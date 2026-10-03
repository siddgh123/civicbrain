"""Step 11 priority (FROZEN) - engine edges, the live factor rules and the explanation JSON (pure, no database)."""

import datetime as dt
import shutil

import pytest

from app.config import PRIORITY_DATA_DIR, PRIORITY_WAIT_MAX_DAYS
from app.errors import ConfigError, DataError
from pipeline import priority as pr

RULES = pr.load_rules()


@pytest.mark.parametrize(
    ("score", "level"),
    [(0, "LOW"), (24.99, "LOW"), (25, "MEDIUM"), (49.99, "MEDIUM"), (50, "HIGH"), (74.99, "HIGH"), (75, "CRITICAL"), (100, "CRITICAL")],
)
def test_level_edges(score, level):
    assert pr.get_priority_level(score) == level


def _scores(**override) -> dict[str, float]:
    base = dict.fromkeys(pr.FACTORS, 0.0)
    base.update(override)
    return base


def test_weighted_sum_by_hand():
    # TC002 of the engine: ward 6 is the largest ward (population score 100)
    scores = _scores(severity=100, population_impact=100, location_risk=100, frequency=60, wait_time=50,
                     infrastructure_importance=100, historical_risk=40)
    # 0.25*100 + 0.15*100 + 0.15*100 + 0.10*60 + 0.10*50 + 0.15*100 + 0.10*40 = 85
    assert pr.calculate_priority_score(scores, RULES.weights) == 85.0
    assert pr.calculate_priority_score(_scores(severity=33.33), RULES.weights) == 8.33  # 8.3325 -> 2 decimals


@pytest.mark.parametrize("bad", [-0.01, 100.01])
def test_factor_outside_0_100_is_rejected(bad):
    with pytest.raises(ValueError, match="between 0 and 100"):
        pr.calculate_priority_score(_scores(frequency=bad), RULES.weights)


def test_missing_factor_is_rejected():
    scores = _scores()
    del scores["wait_time"]
    with pytest.raises(ValueError, match="wait_time"):
        pr.calculate_priority_score(scores, RULES.weights)


def test_reasons_use_the_research_wording():
    scores = _scores(severity=75, population_impact=97.05, infrastructure_importance=50, historical_risk=42.86)
    assert pr.priority_reasons(scores) == ["High/Critical severity", "High population impact", "Medium infrastructure importance"]
    assert pr.priority_reasons(_scores()) == ["Low overall priority factors"]


# ---- factor rules ----

@pytest.mark.parametrize(
    ("pois", "expected"),
    [
        ([], 0.0),
        ([("hospital", 0.0)], 100.0),
        ([("hospital", 99.99)], 100.0),
        ([("hospital", 100.0)], 75.0),  # bands are [min, max): 100 m starts the 0.75 band
        ([("bus_stop", 250.0)], 45.0),
        ([("school", 300.0)], 40.0),
        ([("government_office", 999.0)], 16.25),
        ([("hospital", 1000.0)], 0.0),
        ([("other", 5.0)], 0.0),  # POI type without a rule
        ([("bus_stop", 20.0), ("hospital", 450.0), ("police_station", 150.0)], 71.25),  # max over all POIs
    ],
)
def test_location_risk_is_the_max_over_pois_of_importance_times_band(pois, expected):
    assert pr.location_risk_score(pois, RULES) == expected


@pytest.mark.parametrize(("count", "expected"), [(0, 0.0), (1, 10.0), (2, 20.0), (10, 100.0), (13, 100.0)])
def test_frequency_score(count, expected):
    assert pr.frequency_score(count, RULES) == expected


@pytest.mark.parametrize(
    ("days", "expected"), [(-0.5, 0.0), (0.0, 0.0), (PRIORITY_WAIT_MAX_DAYS / 2, 50.0), (PRIORITY_WAIT_MAX_DAYS, 100.0), (400.0, 100.0)]
)
def test_wait_time_score_is_clamped(days, expected):
    assert pr.wait_time_score(days, RULES) == expected


@pytest.mark.parametrize(("count", "expected"), [(0, 0.0), (1, 7.14), (7, 50.0), (14, 100.0), (20, 100.0)])
def test_historical_risk_score_is_clamped(count, expected):
    assert pr.historical_risk_score(count, RULES) == expected


def test_infrastructure_score_by_road_type():
    assert pr.infrastructure_score("trunk", RULES) == 100.0
    assert pr.infrastructure_score("tertiary", RULES) == 75.0
    assert pr.infrastructure_score("residential", RULES) == 50.0
    assert pr.infrastructure_score("steps", RULES) == 25.0
    for missing in (None, "motorway"):
        with pytest.raises(DataError, match="road type"):
            pr.infrastructure_score(missing, RULES)


def test_population_score_by_ward_number():
    assert pr.population_score(6, RULES) == 100.0  # 4,244 people = the largest ward
    assert pr.population_score(1, RULES) == 97.05
    for missing in (None, 24):
        with pytest.raises(DataError, match="ward"):
            pr.population_score(missing, RULES)


@pytest.mark.parametrize(
    ("depth", "level", "score"), [("SHALLOW", "LOW", 25.0), ("FINGER", "MEDIUM", 50.0), ("DEEP", "HIGH", 75.0), (None, "MEDIUM", 50.0)]
)
def test_severity_level_from_the_depth_answer(depth, level, score):
    assert pr.severity_level_for(depth) == level
    assert pr.severity_score(level, RULES) == score


# ---- compute + explanation ----

AS_OF = dt.datetime(2026, 10, 3, 12, 0, tzinfo=dt.UTC)


def _inputs(**override) -> pr.PriorityInputs:
    values = dict(
        complaint_id=7, category="Pothole", depth_answer="DEEP", ward_number=6, road_id=11, road_type="trunk",
        pois=(pr.Poi("hospital", "City Hospital", 120.0), pr.Poi("bus_stop", "Stand", 40.0)),
        frequency_count=2, historical_count=7, submitted_at=AS_OF - dt.timedelta(days=PRIORITY_WAIT_MAX_DAYS / 4),
    )
    values.update(override)
    return pr.PriorityInputs(**values)


def test_compute_gives_factors_total_level_and_explanation():
    result = pr.compute(_inputs(), RULES, as_of=AS_OF, trigger="ANALYSIS")
    assert result.scores == {
        "severity": 75.0, "population_impact": 100.0, "location_risk": 75.0, "frequency": 20.0, "wait_time": 25.0,
        "infrastructure_importance": 100.0, "historical_risk": 50.0,
    }
    # 18.75 + 15 + 11.25 + 2 + 2.5 + 15 + 5 = 69.5
    assert (result.final_score, result.level) == (69.5, "HIGH")
    ex = result.explanation
    assert ex["formulaVersion"] == "STEP11_FROZEN_V1" and ex["trigger"] == "ANALYSIS" and ex["asOf"] == "2026-10-03T12:00:00+00:00"
    assert ex["finalScore"] == 69.5 and ex["level"] == "HIGH"
    assert list(ex["factors"]) == list(pr.FACTORS)
    for name, factor in ex["factors"].items():
        assert set(factor) == {"score", "weight", "weighted", "input", "rule"}
        assert factor["score"] == result.scores[name] and factor["weight"] == RULES.weights[name]
    assert round(sum(f["weighted"] for f in ex["factors"].values()), 2) == 69.5
    assert ex["factors"]["location_risk"]["input"]["poi"] == {"type": "hospital", "name": "City Hospital", "distanceM": 120.0}
    assert ex["factors"]["severity"]["input"] == {"depthAnswer": "DEEP", "severityLevel": "HIGH", "assumption": True}
    assert ex["factors"]["frequency"]["input"] == {"count": 2, "radiusM": 300.0, "windowDays": 30.0}
    assert ex["factors"]["historical_risk"]["input"] == {"count": 7, "windowDays": 180.0, "match": "same ward and same category"}
    assert ex["factors"]["infrastructure_importance"]["input"] == {"roadId": 11, "roadType": "trunk", "level": "CRITICAL"}
    assert ex["factors"]["population_impact"]["input"]["wardNumber"] == 6
    assert "severity level from the depth answer" in " ".join(ex["assumptions"])
    assert ex["reasons"] == result.reasons


def test_wait_time_grows_with_the_recompute_time():
    a = pr.compute(_inputs(), RULES, as_of=AS_OF)
    b = pr.compute(_inputs(), RULES, as_of=AS_OF + dt.timedelta(days=30))
    assert b.scores["wait_time"] > a.scores["wait_time"] and b.final_score > a.final_score
    assert b.explanation["trigger"] == "ANALYSIS"


def test_missing_ward_fails_the_step():
    with pytest.raises(DataError, match="ward"):
        pr.compute(_inputs(ward_number=None), RULES, as_of=AS_OF)


# ---- rule files ----

def test_changed_weights_in_the_rule_file_are_refused(tmp_path):
    for f in PRIORITY_DATA_DIR.glob("*.csv"):
        shutil.copy(f, tmp_path / f.name)
    text = (tmp_path / "priority_rules.csv").read_text(encoding="utf-8").replace("severity,0.25", "severity,0.30")
    text = text.replace("population_impact,0.15", "population_impact,0.10")
    (tmp_path / "priority_rules.csv").write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match="FROZEN"):
        pr.load_rules(tmp_path)


def test_missing_rule_file_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="priority_rules.csv"):
        pr.load_rules(tmp_path)
