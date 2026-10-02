import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "resources"
    / "processed"
    / "resource_dataset.csv"
)

REQUIRED_COLUMNS = [
    "complaint_id",
    "issue_type",
    "severity",
    "estimated_area",
    "estimated_workers",
    "estimated_duration_hours",
    "labour_cost",
    "material_cost",
    "equipment_cost",
    "transport_cost",
    "total_cost",
    "required_equipment",
]


def main():

    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    print(f"Total rows: {len(rows)}")

    errors = []

    # Row count
    if len(rows) != 500:
        errors.append(f"Expected 500 rows, found {len(rows)}")

    # Required columns
    if rows:
        for column in REQUIRED_COLUMNS:
            if column not in rows[0]:
                errors.append(f"Missing column: {column}")

    # Validate rows
    for index, row in enumerate(rows, start=2):

        # Empty fields
        for column in REQUIRED_COLUMNS:
            if not row.get(column, "").strip():
                errors.append(
                    f"Row {index}: empty {column}"
                )

        # Numeric values
        try:
            labour = float(row["labour_cost"])
            material = float(row["material_cost"])
            equipment = float(row["equipment_cost"])
            transport = float(row["transport_cost"])
            total = float(row["total_cost"])

            calculated_total = (
                labour
                + material
                + equipment
                + transport
            )

            if round(calculated_total, 2) != round(total, 2):
                errors.append(
                    f"Row {index}: total cost mismatch"
                )

        except (ValueError, KeyError):
            errors.append(
                f"Row {index}: invalid cost value"
            )

        # Area
        try:
            area = float(row["estimated_area"])

            if area < 0:
                errors.append(
                    f"Row {index}: negative estimated area"
                )

        except (ValueError, KeyError):
            errors.append(
                f"Row {index}: invalid estimated area"
            )

    if errors:
        print("\nVALIDATION FAILED")
        print(f"Errors found: {len(errors)}")

        for error in errors[:20]:
            print(error)

    else:
        print("\nRESOURCE DATASET VALIDATION PASSED")
        print("500/500 complaints validated")
        print("Required fields: PASS")
        print("Cost calculation: PASS")
        print("Estimated area: PASS")


if __name__ == "__main__":
    main()