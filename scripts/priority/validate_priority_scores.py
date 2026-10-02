import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_factor_dataset.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_scores.csv"
)


WEIGHTS = {
    "severity_score": 0.25,
    "population_score": 0.15,
    "location_risk_score": 0.15,
    "frequency_score": 0.10,
    "wait_time_score": 0.10,
    "infrastructure_importance_score": 0.15,
    "historical_risk_score": 0.10,
}


def get_level(score):
    if score >= 75:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MEDIUM"
    else:
        return "LOW"


def main():

    with INPUT_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        factor_rows = list(csv.DictReader(file))

    with OUTPUT_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        result_rows = list(csv.DictReader(file))

    if len(factor_rows) != 500:
        raise ValueError(
            f"Expected 500 factor rows, found {len(factor_rows)}"
        )

    if len(result_rows) != 500:
        raise ValueError(
            f"Expected 500 result rows, found {len(result_rows)}"
        )

    mismatches = 0

    for factor_row, result_row in zip(
        factor_rows,
        result_rows
    ):

        complaint_id = int(
            factor_row["complaint_id"]
        )

        calculated_score = (
            WEIGHTS["severity_score"]
            * float(factor_row["severity_score"])
            + WEIGHTS["population_score"]
            * float(factor_row["population_score"])
            + WEIGHTS["location_risk_score"]
            * float(factor_row["location_risk_score"])
            + WEIGHTS["frequency_score"]
            * float(factor_row["frequency_score"])
            + WEIGHTS["wait_time_score"]
            * float(factor_row["wait_time_score"])
            + WEIGHTS["infrastructure_importance_score"]
            * float(
                factor_row[
                    "infrastructure_importance_score"
                ]
            )
            + WEIGHTS["historical_risk_score"]
            * float(
                factor_row[
                    "historical_risk_score"
                ]
            )
        )

        calculated_score = round(
            max(0.0, min(100.0, calculated_score)),
            2
        )

        stored_score = round(
            float(result_row["priority_score"]),
            2
        )

        expected_level = get_level(
            calculated_score
        )

        stored_level = (
            result_row["priority_level"].strip()
        )

        if (
            calculated_score != stored_score
            or expected_level != stored_level
            or int(result_row["complaint_id"])
            != complaint_id
        ):
            mismatches += 1

            if mismatches <= 10:
                print(
                    f"Mismatch complaint {complaint_id}: "
                    f"calculated={calculated_score}, "
                    f"stored={stored_score}, "
                    f"expected_level={expected_level}, "
                    f"stored_level={stored_level}"
                )

    print("=" * 70)
    print("CIVICBRAIN INDEPENDENT PRIORITY VALIDATION")
    print("=" * 70)
    print(f"Factor rows checked : {len(factor_rows)}")
    print(f"Score rows checked  : {len(result_rows)}")
    print(f"Mismatches          : {mismatches}")

    if mismatches == 0:
        print("INDEPENDENT PRIORITY VALIDATION PASSED")
    else:
        print("INDEPENDENT PRIORITY VALIDATION FAILED")

    print("=" * 70)


if __name__ == "__main__":
    main()