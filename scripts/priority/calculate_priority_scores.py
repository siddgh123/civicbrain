import csv
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_factor_dataset.csv"
)

RULES_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_rules.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_scores.csv"
)


# ============================================================
# PRIORITY LEVEL
# ============================================================

def get_priority_level(score):
    if score >= 75:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MEDIUM"
    else:
        return "LOW"


# ============================================================
# LOAD WEIGHTS
# ============================================================

def load_weights():

    weights = {}

    with RULES_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            factor = row["factor"].strip()
            weights[factor] = float(row["weight"])

    if len(weights) != 7:
        raise ValueError(
            f"Expected 7 factors, found {len(weights)}"
        )

    if abs(sum(weights.values()) - 1.0) > 0.000001:
        raise ValueError(
            "Priority weights must total 1.0"
        )

    return weights


# ============================================================
# CALCULATE PRIORITY
# ============================================================

def calculate_priority(row, weights):

    severity = float(row["severity_score"])
    population = float(row["population_score"])
    location = float(row["location_risk_score"])
    frequency = float(row["frequency_score"])
    wait_time = float(row["wait_time_score"])
    infrastructure = float(
        row["infrastructure_importance_score"]
    )
    historical = float(
        row["historical_risk_score"]
    )

    scores = [
        severity,
        population,
        location,
        frequency,
        wait_time,
        infrastructure,
        historical,
    ]

    for score in scores:
        if not 0 <= score <= 100:
            raise ValueError(
                f"Factor score outside 0-100: {score}"
            )

    priority_score = (
        weights["severity"] * severity
        + weights["population_impact"] * population
        + weights["location_risk"] * location
        + weights["frequency"] * frequency
        + weights["wait_time"] * wait_time
        + weights["infrastructure_importance"]
        * infrastructure
        + weights["historical_risk"]
        * historical
    )

    priority_score = max(
        0.0,
        min(100.0, priority_score)
    )

    priority_score = round(priority_score, 2)

    priority_level = get_priority_level(
        priority_score
    )

    reasons = []

    if severity >= 75:
        reasons.append("High/Critical severity")
    elif severity >= 50:
        reasons.append("Medium severity")

    if population >= 75:
        reasons.append("High population impact")
    elif population >= 50:
        reasons.append("Moderate population impact")

    if location >= 75:
        reasons.append("High location risk")
    elif location >= 50:
        reasons.append("Moderate location risk")

    if frequency >= 75:
        reasons.append("Frequent similar complaints")
    elif frequency >= 50:
        reasons.append("Repeated similar complaints")

    if wait_time >= 75:
        reasons.append("Long waiting time")
    elif wait_time >= 50:
        reasons.append("Moderate waiting time")

    if infrastructure >= 75:
        reasons.append(
            "Important/critical infrastructure"
        )
    elif infrastructure >= 50:
        reasons.append("Medium infrastructure importance")

    if historical >= 75:
        reasons.append(
            "Persistent historical recurrence"
        )
    elif historical >= 50:
        reasons.append("Historical recurrence")

    if not reasons:
        reasons.append("Low overall priority factors")

    return {
        "complaint_id": row["complaint_id"],
        "ward_id": row["ward_id"],
        "severity_score": severity,
        "population_score": population,
        "location_risk_score": location,
        "frequency_score": frequency,
        "wait_time_score": wait_time,
        "infrastructure_importance_score":
            infrastructure,
        "historical_risk_score": historical,
        "priority_score": priority_score,
        "priority_level": priority_level,
        "priority_reasons": " | ".join(reasons),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    weights = load_weights()

    results = []

    with INPUT_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            results.append(
                calculate_priority(row, weights)
            )

    if len(results) != 500:
        raise ValueError(
            f"Expected 500 complaints, found {len(results)}"
        )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [
            "complaint_id",
            "ward_id",
            "severity_score",
            "population_score",
            "location_risk_score",
            "frequency_score",
            "wait_time_score",
            "infrastructure_importance_score",
            "historical_risk_score",
            "priority_score",
            "priority_level",
            "priority_reasons",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    print("=" * 70)
    print("CIVICBRAIN FINAL PRIORITY SCORES")
    print("=" * 70)
    print(f"Complaints processed : {len(results)}")
    print(f"Output               : {OUTPUT_FILE}")
    print("FINAL PRIORITY SCORES CREATED")
    print("=" * 70)


if __name__ == "__main__":
    main()