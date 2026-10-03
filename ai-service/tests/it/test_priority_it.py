"""Step 11 priority against civicbrain_test (role civicbrain_ai): factor data from PostGIS, the is_current switch,
the complaint columns and the daily recompute. Fixture rows are inserted as the owner (it_data) and deleted afterwards.
"""

import csv
import datetime as dt
import re

import pytest
from sqlalchemy import text

from app.config import PRIORITY_DATA_DIR, PRIORITY_WEIGHTS, REPO_ROOT_DIR
from app.db import session_scope
from pipeline import priority as pr

pytestmark = pytest.mark.integration

NOW = dt.datetime.now(dt.UTC).replace(microsecond=0)
M_LAT = 0.0000090  # about 1 m of latitude


def _hospital(it) -> tuple[float, float]:
    row = it._sql("SELECT latitude, longitude FROM pois WHERE type = 'hospital' ORDER BY poi_id LIMIT 1")[0]
    return float(row["latitude"]), float(row["longitude"])


def _complaint(it, at, submitted, *, category="Pothole", depth=None, synthetic=False, locate=True) -> int:
    """A complaint stored like the intake API does (ward/road/POI from fn_locate_point unless locate=False)."""
    user_id = it.user_ids[0] if it.user_ids else it.new_user()
    with it.engine.begin() as conn:
        conn.execute(text("SELECT set_config('civicbrain.actor_role', 'CITIZEN', true), set_config('civicbrain.actor_user_id', :u, true)"),
                     {"u": str(user_id)})
        cid = conn.execute(
            text(
                "INSERT INTO complaints (user_id, category_id, title, description, location, location_source, submitted_at, depth_answer, "
                "                        is_synthetic, ward_id, road_id, poi_id) "
                "SELECT :u, (SELECT category_id FROM complaint_categories WHERE category_name = :cat), 'IT priority', 'priority fixture', "
                "       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :src, :sub, :depth, :syn, "
                "       CASE WHEN :locate THEN l.ward_id END, CASE WHEN :locate THEN l.road_id END, CASE WHEN :locate THEN l.poi_id END "
                "  FROM fn_locate_point(:lat, :lon) l RETURNING complaint_id"
            ),
            {"u": user_id, "cat": category, "lat": at[0], "lon": at[1], "src": "SYNTHETIC" if synthetic else "BROWSER_GPS",
             "sub": submitted, "depth": depth, "syn": synthetic, "locate": locate},
        ).scalar_one()
    it.complaint_ids.append(cid)
    return cid


def _set_status(it, complaint_id: int, status: str, role: str) -> None:
    with it.engine.begin() as conn:
        conn.execute(text("SELECT set_config('civicbrain.actor_role', :r, true)"), {"r": role})
        conn.execute(text("UPDATE complaints SET status = :s WHERE complaint_id = :c"), {"s": status, "c": complaint_id})


def test_factor_data_comes_from_postgis_and_the_counts_follow_the_rules(it_data, ai_engine):
    lat, lon = _hospital(it_data)
    near = (lat + 30 * M_LAT, lon)
    cid = _complaint(it_data, (lat, lon), NOW - dt.timedelta(hours=1), depth="DEEP")
    counted_both = _complaint(it_data, near, NOW - dt.timedelta(days=2))  # <= 300 m, 30 d, same ward + category
    counted_historical = _complaint(it_data, near, NOW - dt.timedelta(days=40))  # outside 30 d, inside 180 d
    _complaint(it_data, near, NOW - dt.timedelta(days=2), category="Garbage Accumulation")  # other category
    _complaint(it_data, near, NOW - dt.timedelta(days=200))  # older than 180 d
    _complaint(it_data, near, NOW - dt.timedelta(minutes=30))  # after the complaint
    _complaint(it_data, near, NOW - dt.timedelta(days=1), synthetic=True)  # synthetic never counts for a real complaint
    rejected = _complaint(it_data, near, NOW - dt.timedelta(days=1))
    _set_status(it_data, rejected, "REJECTED", "OFFICER")
    wards = it_data._sql("SELECT DISTINCT ward_id FROM complaints WHERE complaint_id = ANY(:ids)",
                         ids=[cid, counted_both, counted_historical])
    assert len(wards) == 1, "fixture points must lie in one ward"

    rules = pr.get_rules()
    with session_scope(ai_engine) as s:
        inputs = pr.load_inputs(s, cid, rules)
    located = it_data._sql(
        "SELECT w.ward_number, r.road_id, r.road_type FROM fn_locate_point(:lat, :lon) l JOIN wards w ON w.ward_id = l.ward_id "
        "JOIN roads r ON r.road_id = l.road_id", lat=lat, lon=lon)[0]
    assert (inputs.ward_number, inputs.road_id, inputs.road_type) == (located["ward_number"], located["road_id"], located["road_type"])
    assert inputs.pois[0].type == "hospital" and inputs.pois[0].distance_m < 1.0
    assert all(p.distance_m <= 1000 for p in inputs.pois)
    assert (inputs.frequency_count, inputs.historical_count, inputs.depth_answer) == (1, 2, "DEEP")

    result = pr.compute(inputs, rules, as_of=NOW)
    assert result.scores["location_risk"] == 100.0  # hospital at 0 m
    assert result.scores["severity"] == 75.0 and result.scores["frequency"] == 10.0 and result.scores["historical_risk"] == 14.29
    assert result.scores["population_impact"] == rules.wards[located["ward_number"]].score
    assert result.scores["infrastructure_importance"] == rules.roads[located["road_type"]][1]


def test_assessment_is_written_once_current_and_mirrored_on_the_complaint(it_data, ai_engine):
    lat, lon = _hospital(it_data)
    cid = _complaint(it_data, (lat + 200 * M_LAT, lon), NOW - dt.timedelta(hours=3), depth="SHALLOW")
    for _ in range(2):  # the same job twice -> one current row with the same values
        with session_scope(ai_engine) as s:
            result = pr.assess_complaint(s, cid, as_of=NOW)
    rows = it_data._sql(
        "SELECT final_score::float AS f, priority_level, is_current, severity_score::float AS s, urgency_score::float AS u, "
        "       location_score::float AS l, impact_score::float AS i, frequency_score::float AS fr, infrastructure_score::float AS inf, "
        "       historical_risk_score::float AS h, reason, formula_version, weights, explanation "
        "FROM priority_assessments WHERE complaint_id = :c ORDER BY priority_assessment_id", c=cid)
    assert [r["is_current"] for r in rows] == [False, True]
    current = rows[1]
    sc = result.scores
    assert (current["s"], current["i"], current["l"], current["fr"], current["u"], current["inf"], current["h"]) == (
        sc["severity"], sc["population_impact"], sc["location_risk"], sc["frequency"], sc["wait_time"], sc["infrastructure_importance"],
        sc["historical_risk"])
    assert (current["f"], current["priority_level"]) == (result.final_score, result.level)
    assert current["reason"] == " | ".join(result.reasons) and current["formula_version"] == "STEP11_FROZEN_V1"
    assert current["weights"] == PRIORITY_WEIGHTS
    # jsonb keeps no key order: the UI lists the factors in formula order (pr.FACTORS)
    assert current["explanation"]["trigger"] == "ANALYSIS" and set(current["explanation"]["factors"]) == set(pr.FACTORS)
    assert current["explanation"]["factors"]["location_risk"]["input"]["poi"]["type"] == "hospital"  # 200 m -> 75
    c = it_data._sql(
        "SELECT current_priority_score::float AS s, current_priority_level AS l FROM complaints WHERE complaint_id = :c", c=cid)[0]
    assert (c["s"], c["l"]) == (result.final_score, result.level)


def test_ward_and_road_missing_on_the_row_are_looked_up_from_the_location(it_data, ai_engine):
    lat, lon = _hospital(it_data)
    cid = _complaint(it_data, (lat, lon), NOW, locate=False)
    with session_scope(ai_engine) as s:
        inputs = pr.load_inputs(s, cid, pr.get_rules())
    assert inputs.ward_number is not None and inputs.road_type is not None


SEED_SQL = REPO_ROOT_DIR / "db" / "seed" / "seed_synthetic_demo_data.sql"
# One complaints row of the pg_dump seed: (id, user, category|NULL, 'title', 'description', 'STATUS', '<EWKB hex point>', ...
SEED_ROW = re.compile(r"^\s*\((\d+), \d+, (?:\d+|NULL), '(?:[^']|'')*', '(?:[^']|'')*', '[A-Z_]+', '([0-9A-F]{50})'")


def _research_locations() -> dict[int, str]:
    """complaint_id -> location (EWKB hex, SRID 4326) of the 500 research complaints (the seed's complaints block)."""
    lines = SEED_SQL.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("-- Data for Name: complaints;"))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("-- Data for Name:"))
    return {int(m.group(1)): m.group(2) for m in map(SEED_ROW.match, lines[start:end]) if m}


def test_live_location_rule_reproduces_all_500_research_location_scores(it_data, ai_engine, capsys):
    """The 500 Step 11 complaints at their research locations (POIs from V1 as in the research): load_inputs +
    location_risk_score give data/priority/location_risk_scores.csv exactly."""
    with (PRIORITY_DATA_DIR / "location_risk_scores.csv").open(encoding="utf-8-sig", newline="") as f:
        research = {int(r["complaint_id"]): float(r["location_risk_score"]) for r in csv.DictReader(f)}
    locations = _research_locations()
    assert len(research) == 500 and set(locations) == set(research)

    rows = it_data._sql(
        "INSERT INTO complaints (user_id, title, description, location, location_source, is_synthetic) "
        "SELECT :u, 'research location ' || t.rid, 'Step 11 location-risk fixture', CAST(t.hex AS geometry), 'SYNTHETIC', true "
        "  FROM unnest(CAST(:rids AS bigint[]), CAST(:hexes AS text[])) AS t(rid, hex) "
        "RETURNING complaint_id, title",
        u=it_data.new_user(), rids=list(locations), hexes=list(locations.values()),
    )
    fixture = {int(r["title"].rsplit(" ", 1)[1]): int(r["complaint_id"]) for r in rows}
    it_data.complaint_ids.extend(fixture.values())

    rules = pr.get_rules()
    mismatches = []
    with session_scope(ai_engine) as s:
        for research_id, cid in sorted(fixture.items()):
            inputs = pr.load_inputs(s, cid, rules)
            live = pr.location_risk_score([(p.type, p.distance_m) for p in inputs.pois], rules)
            if abs(live - research[research_id]) > 1e-9:
                mismatches.append((research_id, live, research[research_id]))
    with capsys.disabled():
        print(f"\nLOCATION RISK vs research: {len(fixture)} rows checked, {len(mismatches)} mismatches")
    assert len(fixture) == 500
    assert mismatches == []


def test_daily_recompute_takes_open_real_complaints_only(it_data, ai_engine):
    lat, lon = _hospital(it_data)
    at = (lat + 500 * M_LAT, lon)
    verified = _complaint(it_data, at, NOW - dt.timedelta(days=3))
    rejected = _complaint(it_data, at, NOW - dt.timedelta(days=3))
    synthetic = _complaint(it_data, at, NOW - dt.timedelta(days=3), synthetic=True)
    not_analysed = _complaint(it_data, at, NOW - dt.timedelta(days=3))
    for cid in (verified, rejected, synthetic):
        with session_scope(ai_engine) as s:
            pr.assess_complaint(s, cid, as_of=NOW)
    _set_status(it_data, verified, "VERIFIED", "SYSTEM")
    _set_status(it_data, rejected, "REJECTED", "OFFICER")

    with session_scope(ai_engine) as s:
        open_ids = set(pr.open_complaint_ids(s))
    assert verified in open_ids and not open_ids & {rejected, synthetic, not_analysed}

    current_sql = "SELECT urgency_score::float AS u FROM priority_assessments WHERE complaint_id = :c AND is_current"
    before = it_data._sql(current_sql, c=verified)[0]["u"]
    done, failed = pr.recompute_open(ai_engine, NOW + dt.timedelta(days=10))
    assert done >= 1 and failed == 0
    rows = it_data._sql(
        "SELECT urgency_score::float AS u, explanation->>'trigger' AS t FROM priority_assessments WHERE complaint_id = :c AND is_current",
        c=verified)
    assert rows[0]["t"] == "DAILY_RECOMPUTE" and rows[0]["u"] > before
    for other in (rejected, synthetic):
        assert it_data._sql("SELECT count(*) AS n FROM priority_assessments WHERE complaint_id = :c", c=other)[0]["n"] == 1
    with session_scope(ai_engine) as s:
        assert pr.last_daily_recompute(s) is not None
