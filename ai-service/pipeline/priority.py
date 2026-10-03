"""Priority - ANALYZE_COMPLAINT step 8 and the daily recompute (FROZEN Step 11: docs/06_AI_PIPELINE.md sec. 1, 2.7, FR-25).

Port of scripts/priority/priority_engine.py, unchanged in behaviour:
- the rule tables are read from data/priority/*.csv (as the engine does), with the engine's checks (7 factors,
  weights total 1.0, 23 wards, scores 0-100) plus one more: the weights must be the FROZEN ones in app/config.py;
- P = 0.25 S + 0.15 Ipop + 0.15 Rloc + 0.10 F + 0.10 Twait + 0.15 Iinfra + 0.10 H (every factor 0-100, summed in the
  engine's order), clamped 0-100, rounded to 2 decimals; LOW < 25 <= MEDIUM < 50 <= HIGH < 75 <= CRITICAL;
- reasons in the wording of scripts/priority/calculate_priority_scores.py (the script that wrote priority_scores.csv).
Golden test: tests/unit/test_priority_golden.py (500 rows, 0 mismatches).

The 7 factors of a live complaint follow the research rule files; each rule reproduces its research factor file
(tests/unit/test_priority_golden.py, docs/PROGRESS.md P09):
  S      severity_scoring_rules.csv: LOW 25, MEDIUM 50, HIGH 75, CRITICAL 100; level from the depth answer (ASSUMPTION)
  Ipop   ward population / largest ward population x 100 (ward_population_scores.csv, by ward NUMBER)
  Rloc   max over POIs of importance (location_risk_rules.csv) x distance band (location_risk_distance_rules.csv)
  F      same-category complaints <= 300 m in the 30 days before submission; 10 -> 100 (frequency_rules.csv)
  Twait  days since submission / 179.27 d (longest wait of the research data) x 100, max 100 (wait_time_rules.csv)
  Iinfra road type of the complaint's road (road_infrastructure_rules.csv)
  H      same-ward same-category complaints in the 180 days before submission / 14 x 100, max 100 (historical_risk_rules.csv)
Each factor is rounded to 2 decimals like the research files. Counts only use complaints of the same kind
(real or synthetic) and never REJECTED ones. Missing factor data (no ward, unknown road type) -> DataError: the job
fails (docs/06 sec. 2 step 8).
"""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.config import (
    IST,
    PRIORITY_DATA_DIR,
    PRIORITY_FORMULA_VERSION,
    PRIORITY_HISTORICAL_MAX_COUNT,
    PRIORITY_OPEN_STATUSES,
    PRIORITY_RECOMPUTE_HOUR_IST,
    PRIORITY_SEVERITY_DEFAULT,
    PRIORITY_SEVERITY_FROM_DEPTH,
    PRIORITY_WAIT_MAX_DAYS,
    PRIORITY_WEIGHTS,
)
from app.db import session_scope
from app.errors import ConfigError, DataError

log = logging.getLogger("pipeline.priority")

# The 7 factors in the order of the Step 11 formula (= the engine's summation order)
FACTORS: tuple[str, ...] = (
    "severity", "population_impact", "location_risk", "frequency", "wait_time", "infrastructure_importance", "historical_risk",
)
TRIGGER_ANALYSIS = "ANALYSIS"
TRIGGER_DAILY = "DAILY_RECOMPUTE"


# ---------------------------------------------------------------------------------------------------------------
# Rule files
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class WardPopulation:
    population: int
    score: float
    source: str
    year: int


@dataclass(frozen=True)
class PriorityRules:
    weights: dict[str, float]
    severity_scores: dict[str, float]
    wards: dict[int, WardPopulation]  # by ward NUMBER
    poi_importance: dict[str, float]
    distance_bands: tuple[tuple[float, float, float], ...]  # (min m, max m, multiplier); a band is [min, max)
    frequency_radius_m: float
    frequency_window_days: float
    frequency_max_count: int
    roads: dict[str, tuple[str, float]]  # road type -> (level, score)
    historical_window_days: float
    wait_max_days: float = PRIORITY_WAIT_MAX_DAYS
    historical_max_count: int = PRIORITY_HISTORICAL_MAX_COUNT

    @property
    def poi_search_m(self) -> float:
        """Beyond the last band with a multiplier > 0 no POI adds risk (1,000 m)."""
        return max((hi for _, hi, m in self.distance_bands if m > 0), default=0.0)


def _read(data_dir: Path, name: str) -> list[dict[str, str]]:
    path = data_dir / name
    if not path.is_file():
        raise ConfigError(f"priority rule file missing: {name} (data/priority)")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _named_values(rows: list[dict[str, str]], name: str) -> dict[str, str]:
    values = {r["rule_name"].strip(): r["value"].strip() for r in rows}
    if not values:
        raise ConfigError(f"{name} has no rules")
    return values


def _score(value: str, what: str) -> float:
    score = float(value)
    if not 0 <= score <= 100:
        raise ConfigError(f"{what} is outside 0-100")
    return score


def load_rules(data_dir: Path = PRIORITY_DATA_DIR) -> PriorityRules:
    """Read and check the Step 11 rule files. ConfigError on a missing or changed file."""
    try:
        return _load_rules(data_dir)
    except (KeyError, ValueError) as exc:
        raise ConfigError(f"priority rule files cannot be read ({type(exc).__name__}: {exc})") from None


def _load_rules(data_dir: Path) -> PriorityRules:
    weights = {r["factor"].strip(): float(r["weight"]) for r in _read(data_dir, "priority_rules.csv")}
    if len(weights) != 7 or abs(sum(weights.values()) - 1.0) > 0.000001:  # the engine's own checks
        raise ConfigError(f"priority_rules.csv: expected 7 factors totalling 1.0, found {len(weights)} totalling {sum(weights.values())}")
    if weights != PRIORITY_WEIGHTS:
        raise ConfigError("priority_rules.csv: weights differ from the FROZEN Step 11 weights (.agents/rules/02-frozen-rules.md)")

    severity = {
        r["severity_level"].strip().upper(): _score(r["severity_score"], "severity score")
        for r in _read(data_dir, "severity_scoring_rules.csv")
    }
    if set(severity) != {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ConfigError("severity_scoring_rules.csv must contain exactly LOW, MEDIUM, HIGH and CRITICAL")

    wards = {
        int(r["ward_number"]): WardPopulation(
            int(r["ward_population"]), _score(r["population_score"], "population score"), r["population_source"].strip(),
            int(r["population_source_year"]),
        )
        for r in _read(data_dir, "ward_population_scores.csv")
    }
    if len(wards) != 23:
        raise ConfigError(f"ward_population_scores.csv: expected 23 wards, found {len(wards)}")

    poi = {r["location_type"].strip(): _score(r["importance_score"], "POI importance") for r in _read(data_dir, "location_risk_rules.csv")}
    bands = tuple(
        sorted((float(r["distance_min_m"]), float(r["distance_max_m"]), float(r["risk_multiplier"]))
               for r in _read(data_dir, "location_risk_distance_rules.csv"))
    )
    if not bands or bands[0][0] != 0 or any(a[1] != b[0] for a, b in zip(bands, bands[1:], strict=False)):
        raise ConfigError("location_risk_distance_rules.csv: bands must start at 0 m and have no gaps")

    freq = _named_values(_read(data_dir, "frequency_rules.csv"), "frequency_rules.csv")
    roads = {
        r["road_type"].strip(): (r["infrastructure_level"].strip(), _score(r["importance_score"], "road importance"))
        for r in _read(data_dir, "road_infrastructure_rules.csv")
    }
    hist = _named_values(_read(data_dir, "historical_risk_rules.csv"), "historical_risk_rules.csv")
    method = (hist.get("matching_category"), hist.get("matching_area"), hist.get("score_method"))
    if method != ("exact", "same_ward", "max_count_normalization"):
        raise ConfigError("historical_risk_rules.csv: rule changed (exact category, same ward, max_count_normalization expected)")
    wait = _named_values(_read(data_dir, "wait_time_rules.csv"), "wait_time_rules.csv")
    if wait.get("maximum_wait_for_100") != "dataset_max_wait_days":
        raise ConfigError("wait_time_rules.csv: rule changed (dataset_max_wait_days expected)")

    return PriorityRules(
        weights=weights,
        severity_scores=severity,
        wards=wards,
        poi_importance=poi,
        distance_bands=bands,
        frequency_radius_m=float(freq["nearby_distance"]),
        frequency_window_days=float(freq["recent_window"]),
        frequency_max_count=int(freq["maximum_count_for_100"]),
        roads=roads,
        historical_window_days=float(hist["historical_window"]),
    )


@lru_cache(maxsize=1)
def get_rules() -> PriorityRules:
    """The rules of this process (read once)."""
    return load_rules()


# ---------------------------------------------------------------------------------------------------------------
# Engine port (scripts/priority/priority_engine.py + calculate_priority_scores.py)
# ---------------------------------------------------------------------------------------------------------------
def get_priority_level(priority_score: float) -> str:
    if priority_score >= 75:
        return "CRITICAL"
    elif priority_score >= 50:
        return "HIGH"
    elif priority_score >= 25:
        return "MEDIUM"
    else:
        return "LOW"


def calculate_priority_score(scores: Mapping[str, float], weights: Mapping[str, float]) -> float:
    for factor in FACTORS:
        if factor not in scores:
            raise ValueError(f"{factor} score is missing")
        if not 0 <= scores[factor] <= 100:
            raise ValueError(f"{factor} score must be between 0 and 100, got {scores[factor]}")
    priority_score = (
        weights["severity"] * scores["severity"]
        + weights["population_impact"] * scores["population_impact"]
        + weights["location_risk"] * scores["location_risk"]
        + weights["frequency"] * scores["frequency"]
        + weights["wait_time"] * scores["wait_time"]
        + weights["infrastructure_importance"] * scores["infrastructure_importance"]
        + weights["historical_risk"] * scores["historical_risk"]
    )
    priority_score = max(0.0, min(100.0, priority_score))
    return round(priority_score, 2)


# (factor, >= 75 text, >= 50 text) - wording of calculate_priority_scores.py, which produced priority_scores.csv
_REASONS = (
    ("severity", "High/Critical severity", "Medium severity"),
    ("population_impact", "High population impact", "Moderate population impact"),
    ("location_risk", "High location risk", "Moderate location risk"),
    ("frequency", "Frequent similar complaints", "Repeated similar complaints"),
    ("wait_time", "Long waiting time", "Moderate waiting time"),
    ("infrastructure_importance", "Important/critical infrastructure", "Medium infrastructure importance"),
    ("historical_risk", "Persistent historical recurrence", "Historical recurrence"),
)


def priority_reasons(scores: Mapping[str, float]) -> list[str]:
    reasons = []
    for factor, high, medium in _REASONS:
        if scores[factor] >= 75:
            reasons.append(high)
        elif scores[factor] >= 50:
            reasons.append(medium)
    return reasons or ["Low overall priority factors"]


# ---------------------------------------------------------------------------------------------------------------
# Factor rules for a live complaint
# ---------------------------------------------------------------------------------------------------------------
def severity_level_for(depth_answer: str | None) -> str:
    """ASSUMPTION (app/config.py): SHALLOW -> LOW, FINGER -> MEDIUM, DEEP -> HIGH, anything else -> MEDIUM."""
    return PRIORITY_SEVERITY_FROM_DEPTH.get(depth_answer or "", PRIORITY_SEVERITY_DEFAULT)


def severity_score(level: str, rules: PriorityRules) -> float:
    key = level.strip().upper()
    if key not in rules.severity_scores:
        raise DataError(f"unknown severity level {level!r}")
    return rules.severity_scores[key]


def population_score(ward_number: int | None, rules: PriorityRules) -> float:
    if ward_number is None or ward_number not in rules.wards:
        raise DataError(f"no population data for ward number {ward_number}")
    return rules.wards[ward_number].score


def _band_multiplier(distance_m: float, rules: PriorityRules) -> float:
    for lo, hi, multiplier in rules.distance_bands:
        if lo <= distance_m < hi:
            return multiplier
    return 0.0


def _poi_risk(poi_type: str, distance_m: float, rules: PriorityRules) -> float:
    return rules.poi_importance.get(poi_type, 0.0) * _band_multiplier(distance_m, rules)


def location_risk_score(pois: Sequence[tuple[str, float]], rules: PriorityRules) -> float:
    """max over (type, distance m) of importance x distance multiplier; POI types without a rule count 0."""
    return round(max((_poi_risk(t, d, rules) for t, d in pois), default=0.0), 2)


def frequency_score(count: int, rules: PriorityRules) -> float:
    return round(min(count, rules.frequency_max_count) / rules.frequency_max_count * 100, 2)


def wait_time_score(wait_days: float, rules: PriorityRules) -> float:
    return round(max(0.0, min(100.0, wait_days / rules.wait_max_days * 100)), 2)


def infrastructure_score(road_type: str | None, rules: PriorityRules) -> float:
    if road_type is None or road_type not in rules.roads:
        raise DataError(f"no infrastructure rule for road type {road_type!r}")
    return rules.roads[road_type][1]


def historical_risk_score(count: int, rules: PriorityRules) -> float:
    return round(min(100.0, count / rules.historical_max_count * 100), 2)


# ---------------------------------------------------------------------------------------------------------------
# One complaint: inputs -> result with explanation
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Poi:
    type: str
    name: str | None
    distance_m: float


@dataclass(frozen=True)
class PriorityInputs:
    complaint_id: int
    category: str | None
    depth_answer: str | None
    ward_number: int | None
    road_id: int | None
    road_type: str | None
    pois: tuple[Poi, ...]
    frequency_count: int
    historical_count: int
    submitted_at: datetime


@dataclass(frozen=True)
class PriorityResult:
    scores: dict[str, float]
    final_score: float
    level: str
    reasons: list[str]
    explanation: dict


def _bands_text(rules: PriorityRules) -> str:
    return ", ".join(f"{lo:g}-{hi:g} m x{m:.2f}" for lo, hi, m in rules.distance_bands if m > 0)


def compute(inputs: PriorityInputs, rules: PriorityRules, *, as_of: datetime, trigger: str = TRIGGER_ANALYSIS) -> PriorityResult:
    """The 7 factors, P, level, reasons and the explanation JSON (each factor's input and rule)."""
    level = severity_level_for(inputs.depth_answer)
    wait_days = (as_of - inputs.submitted_at).total_seconds() / 86400
    best_poi = max(inputs.pois, key=lambda p: (_poi_risk(p.type, p.distance_m, rules), -p.distance_m), default=None)
    ward = rules.wards.get(inputs.ward_number) if inputs.ward_number is not None else None
    largest = max(w.population for w in rules.wards.values())

    scores = {
        "severity": severity_score(level, rules),
        "population_impact": population_score(inputs.ward_number, rules),
        "location_risk": location_risk_score([(p.type, p.distance_m) for p in inputs.pois], rules),
        "frequency": frequency_score(inputs.frequency_count, rules),
        "wait_time": wait_time_score(wait_days, rules),
        "infrastructure_importance": infrastructure_score(inputs.road_type, rules),
        "historical_risk": historical_risk_score(inputs.historical_count, rules),
    }
    final = calculate_priority_score(scores, rules.weights)
    final_level = get_priority_level(final)
    reasons = priority_reasons(scores)

    poi_input = None
    if best_poi is not None and scores["location_risk"] > 0:
        poi_input = {"type": best_poi.type, "name": best_poi.name, "distanceM": round(best_poi.distance_m, 1)}
    factor_inputs: dict[str, tuple[dict, str]] = {
        "severity": (
            {"depthAnswer": inputs.depth_answer, "severityLevel": level, "assumption": True},
            "severity level LOW 25, MEDIUM 50, HIGH 75, CRITICAL 100; level from the depth answer "
            "(SHALLOW LOW, FINGER MEDIUM, DEEP HIGH, otherwise MEDIUM)",
        ),
        "population_impact": (
            {"wardNumber": inputs.ward_number, "wardPopulation": ward.population if ward else None,
             "source": f"{ward.source} {ward.year}" if ward else None},
            f"ward population / largest ward population ({largest:,}) x 100",
        ),
        "location_risk": (
            {"poi": poi_input, "poisWithinM": rules.poi_search_m, "poisFound": len(inputs.pois)},
            f"highest POI importance (hospital/fire station 100 ... bus stop 60) x distance factor ({_bands_text(rules)})",
        ),
        "frequency": (
            {"count": inputs.frequency_count, "radiusM": rules.frequency_radius_m, "windowDays": rules.frequency_window_days},
            f"same-category complaints within {rules.frequency_radius_m:g} m in the {rules.frequency_window_days:g} days "
            f"before submission; {rules.frequency_max_count} or more = 100",
        ),
        "wait_time": (
            {"waitDays": round(wait_days, 2)},
            f"days since submission / {rules.wait_max_days:.2f} days (longest wait in the Step 11 data) x 100, max 100",
        ),
        "infrastructure_importance": (
            {"roadId": inputs.road_id, "roadType": inputs.road_type, "level": rules.roads[inputs.road_type][0]},
            "road type of the nearest road: trunk 100, secondary/tertiary 75, residential/service 50, path/track 25",
        ),
        "historical_risk": (
            {"count": inputs.historical_count, "windowDays": rules.historical_window_days, "match": "same ward and same category"},
            f"same-ward same-category complaints in the {rules.historical_window_days:g} days before submission / "
            f"{rules.historical_max_count} (largest count in the Step 11 data) x 100, max 100",
        ),
    }
    factors = {
        name: {
            "score": scores[name],
            "weight": rules.weights[name],
            "weighted": round(rules.weights[name] * scores[name], 4),
            "input": factor_inputs[name][0],
            "rule": factor_inputs[name][1],
        }
        for name in FACTORS
    }
    explanation = {
        "formulaVersion": PRIORITY_FORMULA_VERSION,
        "trigger": trigger,
        "asOf": as_of.isoformat(),
        "finalScore": final,
        "level": final_level,
        "factors": factors,
        "reasons": reasons,
        "assumptions": [
            "severity level from the depth answer (SHALLOW LOW, FINGER MEDIUM, DEEP HIGH; no answer or other "
            "categories MEDIUM) - the Step 11 levels were synthetic",
        ],
    }
    return PriorityResult(scores, final, final_level, reasons, explanation)


# ---------------------------------------------------------------------------------------------------------------
# Database (role civicbrain_ai; the caller owns the transaction)
# ---------------------------------------------------------------------------------------------------------------
# Ward and road: the values stored at submit (fn_locate_point); for an older row without them the same lookup now.
COMPLAINT_SQL = text(
    """
    SELECT c.complaint_id, c.category_id, cc.category_name, c.depth_answer, c.submitted_at, c.is_synthetic,
           COALESCE(c.ward_id, l.ward_id) AS ward_id, w.ward_number, COALESCE(c.road_id, l.road_id) AS road_id, r.road_type
      FROM complaints c
      LEFT JOIN complaint_categories cc ON cc.category_id = c.category_id
      LEFT JOIN LATERAL fn_locate_point(ST_Y(c.location), ST_X(c.location)) l ON c.ward_id IS NULL OR c.road_id IS NULL
      LEFT JOIN wards w ON w.ward_id = COALESCE(c.ward_id, l.ward_id)
      LEFT JOIN roads r ON r.road_id = COALESCE(c.road_id, l.road_id)
     WHERE c.complaint_id = :cid
    """
)
POIS_SQL = text(
    """
    SELECT p.type, p.name, ST_Distance(c.location::geography, p.geometry::geography) AS distance_m
      FROM complaints c
      JOIN pois p ON ST_DWithin(c.location::geography, p.geometry::geography, :radius)
     WHERE c.complaint_id = :cid
     ORDER BY distance_m, p.poi_id
    """
)
FREQUENCY_SQL = text(
    """
    SELECT count(*)
      FROM complaints c
      JOIN complaints o
        ON o.complaint_id <> c.complaint_id
       AND o.category_id = c.category_id
       AND o.is_synthetic = c.is_synthetic
       AND o.status <> 'REJECTED'
       AND o.submitted_at >= c.submitted_at - make_interval(days => :days)
       AND o.submitted_at < c.submitted_at
       AND ST_DWithin(c.location::geography, o.location::geography, :radius)
     WHERE c.complaint_id = :cid
    """
)
HISTORICAL_SQL = text(
    """
    SELECT count(*)
      FROM complaints c
      JOIN complaints o
        ON o.complaint_id <> c.complaint_id
       AND o.ward_id = :ward_id
       AND o.category_id = c.category_id
       AND o.is_synthetic = c.is_synthetic
       AND o.status <> 'REJECTED'
       AND o.submitted_at >= c.submitted_at - make_interval(days => :days)
       AND o.submitted_at < c.submitted_at
     WHERE c.complaint_id = :cid
    """
)


def load_inputs(session: Session, complaint_id: int, rules: PriorityRules) -> PriorityInputs:
    row = session.execute(COMPLAINT_SQL, {"cid": complaint_id}).mappings().one_or_none()
    if row is None:
        raise DataError(f"complaint {complaint_id} not found")
    pois = session.execute(POIS_SQL, {"cid": complaint_id, "radius": rules.poi_search_m}).all()
    frequency = session.execute(
        FREQUENCY_SQL, {"cid": complaint_id, "days": int(rules.frequency_window_days), "radius": rules.frequency_radius_m}
    ).scalar_one()
    historical = 0
    if row["ward_id"] is not None:
        historical = session.execute(
            HISTORICAL_SQL, {"cid": complaint_id, "ward_id": row["ward_id"], "days": int(rules.historical_window_days)}
        ).scalar_one()
    return PriorityInputs(
        complaint_id=complaint_id,
        category=row["category_name"],
        depth_answer=row["depth_answer"],
        ward_number=row["ward_number"],
        road_id=row["road_id"],
        road_type=row["road_type"],
        pois=tuple(Poi(t, n, float(d)) for t, n, d in pois),
        frequency_count=int(frequency),
        historical_count=int(historical),
        submitted_at=row["submitted_at"],
    )


RETIRE_SQL = text("UPDATE priority_assessments SET is_current = false WHERE complaint_id = :cid AND is_current")
INSERT_SQL = text(
    """
    INSERT INTO priority_assessments (complaint_id, severity_score, urgency_score, location_score, impact_score, final_score,
                                      priority_level, reason, frequency_score, infrastructure_score, historical_risk_score,
                                      formula_version, weights, explanation, is_current)
    VALUES (:cid, :severity, :wait, :location, :population, :final, :level, :reason, :frequency, :infrastructure, :historical,
            :version, CAST(:weights AS jsonb), CAST(:explanation AS jsonb), true)
    RETURNING priority_assessment_id
    """
)
COMPLAINT_UPDATE_SQL = text(
    "UPDATE complaints SET current_priority_score = :final, current_priority_level = :level WHERE complaint_id = :cid"
)


def write_priority(session: Session, complaint_id: int, result: PriorityResult, weights: Mapping[str, float]) -> int:
    """The new assessment becomes the only current one (is_current switch); returns its id."""
    s = result.scores
    session.execute(RETIRE_SQL, {"cid": complaint_id})
    assessment_id = session.execute(
        INSERT_SQL,
        {
            "cid": complaint_id, "severity": s["severity"], "wait": s["wait_time"], "location": s["location_risk"],
            "population": s["population_impact"], "final": result.final_score, "level": result.level,
            "reason": " | ".join(result.reasons), "frequency": s["frequency"], "infrastructure": s["infrastructure_importance"],
            "historical": s["historical_risk"], "version": PRIORITY_FORMULA_VERSION, "weights": json.dumps(dict(weights)),
            "explanation": json.dumps(result.explanation),
        },
    ).scalar_one()
    session.execute(COMPLAINT_UPDATE_SQL, {"cid": complaint_id, "final": result.final_score, "level": result.level})
    return int(assessment_id)


def assess_complaint(
    session: Session, complaint_id: int, *, as_of: datetime | None = None, trigger: str = TRIGGER_ANALYSIS,
    rules: PriorityRules | None = None,
) -> PriorityResult:
    """Step 8: load the factor data, compute, store. DataError when factor data is missing (the job fails)."""
    rules = rules or get_rules()
    as_of = as_of or datetime.now(UTC)
    result = compute(load_inputs(session, complaint_id, rules), rules, as_of=as_of, trigger=trigger)
    write_priority(session, complaint_id, result, rules.weights)
    return result


# ---------------------------------------------------------------------------------------------------------------
# Daily recompute at 02:00 IST (06 sec. 1): the wait-time factor grows every day
# ---------------------------------------------------------------------------------------------------------------
OPEN_SQL = text(
    """
    SELECT c.complaint_id
      FROM complaints c
     WHERE NOT c.is_synthetic
       AND c.status = ANY(CAST(:statuses AS varchar[]))
       AND EXISTS (SELECT 1 FROM priority_assessments p WHERE p.complaint_id = c.complaint_id AND p.is_current)
     ORDER BY c.complaint_id
    """
)
LAST_DAILY_SQL = text(f"SELECT max(calculated_at) FROM priority_assessments WHERE explanation->>'trigger' = '{TRIGGER_DAILY}'")


def latest_recompute_time(now: datetime) -> datetime:
    """The most recent 02:00 IST at or before `now` (an aware datetime), as UTC."""
    local = now.astimezone(IST)
    due = local.replace(hour=PRIORITY_RECOMPUTE_HOUR_IST, minute=0, second=0, microsecond=0)
    if due > local:
        due -= timedelta(days=1)
    return due.astimezone(UTC)


def open_complaint_ids(session: Session) -> list[int]:
    """Open, non-synthetic complaints that already have a priority (the analysis gives the first one)."""
    return [int(r[0]) for r in session.execute(OPEN_SQL, {"statuses": list(PRIORITY_OPEN_STATUSES)}).all()]


def last_daily_recompute(session: Session) -> datetime | None:
    return session.execute(LAST_DAILY_SQL).scalar_one()


def recompute_open(engine: Engine, as_of: datetime) -> tuple[int, int]:
    """New current assessment for every open complaint, one transaction each. Returns (done, failed)."""
    rules = get_rules()
    with session_scope(engine) as s:
        ids = open_complaint_ids(s)
    done = failed = 0
    for complaint_id in ids:
        try:
            with session_scope(engine) as s:
                assess_complaint(s, complaint_id, as_of=as_of, trigger=TRIGGER_DAILY, rules=rules)
            done += 1
        except (DataError, ValueError) as exc:  # one complaint's missing data never stops the others
            failed += 1
            log.warning("daily priority recompute skipped a complaint: %s", exc, extra={"complaint_id": complaint_id, "step": "priority"})
    return done, failed
