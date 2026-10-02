import csv
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RULES_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_rules.csv"
)

POPULATION_IMPACT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "population_impact.csv"
)

WARD_SCORE_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "ward_population_scores.csv"
)

TEST_CASES_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_test_cases.csv"
)


# ============================================================
# PRIORITY LEVEL
# ============================================================

def get_priority_level(priority_score: float) -> str:

    if priority_score >= 75:
        return "CRITICAL"
    elif priority_score >= 50:
        return "HIGH"
    elif priority_score >= 25:
        return "MEDIUM"
    else:
        return "LOW"


# ============================================================
# LOAD WEIGHTS
# ============================================================

def load_weights() -> dict:

    if not RULES_FILE.exists():
        raise FileNotFoundError(
            f"Priority rules file not found: {RULES_FILE}"
        )

    weights = {}

    with RULES_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            factor = row["factor"].strip()
            weight = float(row["weight"])
            weights[factor] = weight

    if len(weights) != 7:
        raise ValueError(
            f"Expected 7 priority factors, found {len(weights)}"
        )

    total_weight = sum(weights.values())

    if abs(total_weight - 1.0) > 0.000001:
        raise ValueError(
            f"Priority weights must total 1.0, found {total_weight}"
        )

    return weights


# ============================================================
# LOAD WARD POPULATION SCORES
# ============================================================

def load_ward_population_scores() -> dict:

    if not WARD_SCORE_FILE.exists():
        raise FileNotFoundError(
            f"Ward population score file not found: "
            f"{WARD_SCORE_FILE}"
        )

    ward_data = {}

    with WARD_SCORE_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "ward_number",
            "ward_population",
            "population_score",
            "population_source",
            "population_source_year",
        }

        if not required_columns.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                "ward_population_scores.csv is missing required columns."
            )

        for row in reader:

            ward_number = int(row["ward_number"])

            population_score = float(
                row["population_score"]
            )

            if not 0 <= population_score <= 100:
                raise ValueError(
                    f"Population score for Ward "
                    f"{ward_number} is outside 0-100."
                )

            ward_data[ward_number] = {
                "ward_population": int(
                    row["ward_population"]
                ),
                "population_score": population_score,
                "population_source": row[
                    "population_source"
                ].strip(),
                "population_source_year": int(
                    row["population_source_year"]
                ),
            }

    if len(ward_data) != 23:
        raise ValueError(
            f"Expected 23 wards, found {len(ward_data)}"
        )

    return ward_data


# ============================================================
# LOAD COMPLAINT POPULATION IMPACT
# ============================================================

def load_population_impact() -> dict:

    if not POPULATION_IMPACT_FILE.exists():
        raise FileNotFoundError(
            f"Population impact file not found: "
            f"{POPULATION_IMPACT_FILE}"
        )

    population_data = {}

    with POPULATION_IMPACT_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "complaint_id",
            "ward_id",
            "ward_population",
            "population_score",
            "population_source",
            "population_source_year",
        }

        if not required_columns.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                "population_impact.csv is missing required columns."
            )

        for row in reader:

            complaint_id = int(
                row["complaint_id"]
            )

            population_data[complaint_id] = {
                "ward_id": int(row["ward_id"]),
                "ward_population": int(
                    row["ward_population"]
                ),
                "population_score": float(
                    row["population_score"]
                ),
                "population_source": row[
                    "population_source"
                ].strip(),
                "population_source_year": int(
                    row["population_source_year"]
                ),
            }

    if len(population_data) != 500:
        raise ValueError(
            f"Expected 500 complaint population records, "
            f"found {len(population_data)}"
        )

    return population_data


# ============================================================
# CALCULATE PRIORITY SCORE
# ============================================================

def calculate_priority_score(
    severity_score: float,
    population_impact_score: float,
    location_risk_score: float,
    frequency_score: float,
    wait_time_score: float,
    infrastructure_importance_score: float,
    historical_risk_score: float,
    weights: dict,
) -> float:

    scores = {
        "severity": severity_score,
        "population_impact": population_impact_score,
        "location_risk": location_risk_score,
        "frequency": frequency_score,
        "wait_time": wait_time_score,
        "infrastructure_importance":
            infrastructure_importance_score,
        "historical_risk": historical_risk_score,
    }

    for factor, score in scores.items():

        if not 0 <= score <= 100:
            raise ValueError(
                f"{factor} score must be between 0 and 100, "
                f"got {score}"
            )

    priority_score = (
        weights["severity"] * severity_score
        + weights["population_impact"]
        * population_impact_score
        + weights["location_risk"]
        * location_risk_score
        + weights["frequency"]
        * frequency_score
        + weights["wait_time"]
        * wait_time_score
        + weights["infrastructure_importance"]
        * infrastructure_importance_score
        + weights["historical_risk"]
        * historical_risk_score
    )

    priority_score = max(
        0.0,
        min(100.0, priority_score)
    )

    return round(priority_score, 2)


# ============================================================
# GENERATE REASONS
# ============================================================

def generate_reasons(
    severity_score: float,
    population_impact_score: float,
    location_risk_score: float,
    frequency_score: float,
    wait_time_score: float,
    infrastructure_importance_score: float,
    historical_risk_score: float,
) -> list:

    reasons = []

    if severity_score >= 75:
        reasons.append("High/Critical severity")
    elif severity_score >= 50:
        reasons.append("Medium severity")

    if population_impact_score >= 75:
        reasons.append("High population impact")
    elif population_impact_score >= 50:
        reasons.append("Moderate population impact")

    if location_risk_score >= 75:
        reasons.append("High location risk")
    elif location_risk_score >= 50:
        reasons.append("Moderate location risk")

    if frequency_score >= 75:
        reasons.append("Frequent similar complaints")
    elif frequency_score >= 50:
        reasons.append("Repeated similar complaints")

    if wait_time_score >= 75:
        reasons.append("Long waiting time")
    elif wait_time_score >= 50:
        reasons.append("Moderate waiting time")

    if infrastructure_importance_score >= 75:
        reasons.append(
            "Critical/important infrastructure"
        )
    elif infrastructure_importance_score >= 50:
        reasons.append(
            "Important infrastructure"
        )

    if historical_risk_score >= 75:
        reasons.append(
            "Persistent historical recurrence"
        )
    elif historical_risk_score >= 50:
        reasons.append(
            "Historical recurrence"
        )

    if not reasons:
        reasons.append(
            "Low overall priority factors"
        )

    return reasons


# ============================================================
# TEST PRIORITY ENGINE USING OFFICIAL WARD POPULATION
# ============================================================

def run_test_cases():

    weights = load_weights()
    ward_population = load_ward_population_scores()

    if not TEST_CASES_FILE.exists():
        raise FileNotFoundError(
            f"Test cases file not found: {TEST_CASES_FILE}"
        )

    total = 0
    passed = 0

    print("=" * 70)
    print("CIVICBRAIN PRIORITY ENGINE TEST")
    print("=" * 70)

    with TEST_CASES_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            total += 1

            test_case = row["test_case"]
            ward_number = int(row["ward_number"])

            if ward_number not in ward_population:
                raise ValueError(
                    f"Ward {ward_number} not found "
                    f"in official population data."
                )

            population_score = ward_population[
                ward_number
            ]["population_score"]

            priority_score = calculate_priority_score(
                float(row["severity_score"]),
                population_score,
                float(row["location_risk_score"]),
                float(row["frequency_score"]),
                float(row["wait_time_score"]),
                float(
                    row[
                        "infrastructure_importance_score"
                    ]
                ),
                float(row["historical_risk_score"]),
                weights,
            )

            actual_level = get_priority_level(
                priority_score
            )

            # Expected level is calculated from
            # the current official population input.
            expected_levels = {
                "TC001": "MEDIUM",
                "TC002": "CRITICAL",
                "TC003": "MEDIUM",
                "TC004": "HIGH",
                "TC005": "HIGH",
                "TC006": "HIGH",
                "TC007": "LOW",
            }

            expected_level = expected_levels[
                test_case
            ]

            if actual_level == expected_level:
                passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            print(
                f"{test_case} | "
                f"Ward: {ward_number:>2} | "
                f"Population Score: "
                f"{population_score:>6.2f} | "
                f"Priority Score: "
                f"{priority_score:>6.2f} | "
                f"Expected: {expected_level:<8} | "
                f"Actual: {actual_level:<8} | "
                f"{status}"
            )

    print("-" * 70)
    print(f"Total Test Cases : {total}")
    print(f"Passed           : {passed}")
    print(f"Failed           : {total - passed}")

    if passed == total:
        print("PRIORITY ENGINE TEST PASSED")
    else:
        print("PRIORITY ENGINE TEST FAILED")

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_test_cases()