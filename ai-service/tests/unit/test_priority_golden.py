"""Step 11 golden test (FROZEN: docs/06_AI_PIPELINE.md sec. 2.7, docs/09_BUILD_PLAN_7DAY.md sec. 4).

Every row of data/priority/priority_factor_dataset.csv is recomputed with pipeline/priority.py and compared with the
research output data/priority/priority_scores.csv: score within 1e-6, same level, same reasons -> 0 mismatches.
The live factor rules are checked against the research factor files too (input column -> score column, 500 rows each).
"""

import csv

from app.config import PRIORITY_DATA_DIR, PRIORITY_HISTORICAL_MAX_COUNT, PRIORITY_WAIT_MAX_DAYS, PRIORITY_WEIGHTS
from pipeline import priority as pr

# research column -> engine factor name (the order of the Step 11 formula)
SCORE_COLUMNS = {
    "severity": "severity_score",
    "population_impact": "population_score",
    "location_risk": "location_risk_score",
    "frequency": "frequency_score",
    "wait_time": "wait_time_score",
    "infrastructure_importance": "infrastructure_importance_score",
    "historical_risk": "historical_risk_score",
}


def _rows(name: str) -> list[dict]:
    with (PRIORITY_DATA_DIR / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_golden_priority_scores_have_zero_mismatches(capsys):
    rules = pr.load_rules()
    expected = {r["complaint_id"]: r for r in _rows("priority_scores.csv")}
    rows = _rows("priority_factor_dataset.csv")
    mismatches = []
    for row in rows:
        scores = {factor: float(row[column]) for factor, column in SCORE_COLUMNS.items()}
        score = pr.calculate_priority_score(scores, rules.weights)
        level = pr.get_priority_level(score)
        reasons = " | ".join(pr.priority_reasons(scores))
        want = expected[row["complaint_id"]]
        if abs(score - float(want["priority_score"])) > 1e-6 or level != want["priority_level"] or reasons != want["priority_reasons"]:
            mismatches.append((row["complaint_id"], score, level, want["priority_score"], want["priority_level"]))
    with capsys.disabled():
        print(f"\nPRIORITY GOLDEN: {len(rows)} rows checked, {len(mismatches)} mismatches")
    assert len(rows) == 500 and set(expected) == {r["complaint_id"] for r in rows}
    assert mismatches == []


def test_the_factor_columns_of_both_research_files_agree():
    expected = {r["complaint_id"]: r for r in _rows("priority_scores.csv")}
    for row in _rows("priority_factor_dataset.csv"):
        for column in SCORE_COLUMNS.values():
            assert float(row[column]) == float(expected[row["complaint_id"]][column])


def test_the_engines_own_test_cases_pass():
    """scripts/priority/priority_engine.py run_test_cases(): population from the ward, expected levels from the engine."""
    rules = pr.load_rules()
    expected_levels = {"TC001": "MEDIUM", "TC002": "CRITICAL", "TC003": "MEDIUM", "TC004": "HIGH", "TC005": "HIGH",
                       "TC006": "HIGH", "TC007": "LOW"}
    cases = _rows("priority_test_cases.csv")
    assert [c["test_case"] for c in cases] == list(expected_levels)
    for case in cases:
        scores = {factor: float(case[column]) for factor, column in SCORE_COLUMNS.items() if factor != "population_impact"}
        scores["population_impact"] = pr.population_score(int(case["ward_number"]), rules)
        assert pr.get_priority_level(pr.calculate_priority_score(scores, rules.weights)) == expected_levels[case["test_case"]]


def test_weights_in_the_rule_file_are_the_frozen_weights():
    assert pr.load_rules().weights == PRIORITY_WEIGHTS
    assert abs(sum(PRIORITY_WEIGHTS.values()) - 1.0) < 1e-9


# ---- the live factor rules reproduce the research factor files ----

def test_severity_rule_reproduces_severity_scores():
    rules = pr.load_rules()
    rows = _rows("severity_scores.csv")
    assert len(rows) == 500
    assert all(pr.severity_score(r["severity_level"], rules) == float(r["severity_score"]) for r in rows)


def test_population_rule_reproduces_ward_and_complaint_population_scores():
    rules = pr.load_rules()
    official = _rows("official_ward_population.csv")
    largest = max(int(r["ward_population"]) for r in official)
    assert len(official) == 23
    for r in official:  # calculate_population_score.py: population / largest ward x 100, 2 decimals
        assert pr.population_score(int(r["ward_number"]), rules) == round(int(r["ward_population"]) / largest * 100, 2)
    rows = _rows("population_impact.csv")  # research column ward_id holds the WARD NUMBER (docs/INVENTORY.md)
    assert len(rows) == 500
    assert all(pr.population_score(int(r["ward_id"]), rules) == float(r["population_score"]) for r in rows)


def test_frequency_rule_reproduces_frequency_scores():
    rules = pr.load_rules()
    rows = _rows("frequency_scores.csv")
    assert len(rows) == 500
    assert all(pr.frequency_score(int(r["frequency_count"]), rules) == float(r["frequency_score"]) for r in rows)


def test_wait_time_rule_reproduces_wait_time_scores():
    """The file rounds wait_days to 2 decimals, so a score may differ by one in the last digit (the exact submit times
    reproduce all 500 scores exactly - checked on the seeded dev database, docs/PROGRESS.md P09)."""
    rules = pr.load_rules()
    rows = _rows("wait_time_scores.csv")
    assert len(rows) == 500
    assert round(PRIORITY_WAIT_MAX_DAYS, 2) == max(float(r["wait_days"]) for r in rows)
    assert all(abs(pr.wait_time_score(float(r["wait_days"]), rules) - float(r["wait_time_score"])) <= 0.01 + 1e-9 for r in rows)


def test_infrastructure_rule_reproduces_infrastructure_scores():
    rules = pr.load_rules()
    rows = _rows("infrastructure_importance_scores.csv")
    assert len(rows) == 500
    assert all(pr.infrastructure_score(r["road_type"], rules) == float(r["infrastructure_importance_score"]) for r in rows)


def test_historical_rule_reproduces_historical_risk_scores():
    rules = pr.load_rules()
    rows = _rows("historical_risk_scores.csv")
    assert len(rows) == 500
    assert PRIORITY_HISTORICAL_MAX_COUNT == max(int(r["historical_count"]) for r in rows)
    assert all(pr.historical_risk_score(int(r["historical_count"]), rules) == float(r["historical_risk_score"]) for r in rows)
