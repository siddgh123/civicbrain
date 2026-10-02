import csv
from pathlib import Path

CSV_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "complaints"
    / "raw"
    / "complaints_raw.csv"
)
VERIFIED_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "complaints"
    / "verified"
    / "complaints_verified.csv"
)
EXPECTED_COLUMNS = [
    "complaint_id",
    "title",
    "description",
    "category",
    "latitude",
    "longitude",
    "created_at",
    "status",
    "image_path",
    "is_synthetic"
]

VALID_CATEGORIES = {
    "Pothole",
    "Road Damage",
    "Garbage Accumulation",
    "Waterlogging",
    "Water Leakage",
    "Blocked Drain",
    "Streetlight",
    "Other"
}

VALID_STATUSES = {
    "SUBMITTED",
    "VERIFIED",
    "ASSIGNED",
    "SCHEDULED",
    "IN_PROGRESS",
    "COMPLETED",
    "CLOSED",
    "REOPENED"
}


def validate_dataset():

    with open(CSV_FILE, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    errors = []

    # Check columns
    if reader.fieldnames != EXPECTED_COLUMNS:
        errors.append("CSV columns do not match expected columns.")

    # Check record count
    if len(rows) != 500:
        errors.append(f"Expected 500 records, found {len(rows)}.")

    complaint_ids = []

    for row in rows:

        complaint_id = row["complaint_id"]
        complaint_ids.append(complaint_id)

        # Required fields
        for field in EXPECTED_COLUMNS:
            if field != "image_path" and not row[field].strip():
                errors.append(
                    f"Complaint {complaint_id}: {field} is empty."
                )

        # Category
        if row["category"] not in VALID_CATEGORIES:
            errors.append(
                f"Complaint {complaint_id}: invalid category."
            )

        # Status
        if row["status"] not in VALID_STATUSES:
            errors.append(
                f"Complaint {complaint_id}: invalid status."
            )

        # Coordinates
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

            if not (-90 <= latitude <= 90):
                errors.append(
                    f"Complaint {complaint_id}: invalid latitude."
                )

            if not (-180 <= longitude <= 180):
                errors.append(
                    f"Complaint {complaint_id}: invalid longitude."
                )

        except ValueError:
            errors.append(
                f"Complaint {complaint_id}: invalid coordinates."
            )

        # Synthetic flag
        if row["is_synthetic"].lower() != "true":
            errors.append(
                f"Complaint {complaint_id}: is_synthetic is not true."
            )

        # Image path
        if not row["image_path"].strip():
            errors.append(
                f"Complaint {complaint_id}: image_path is empty."
            )

    # Duplicate complaint IDs
    if len(complaint_ids) != len(set(complaint_ids)):
        errors.append("Duplicate complaint_id values found.")

    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print("-", error)
    else:
        VERIFIED_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(CSV_FILE, "r", encoding="utf-8") as source:
            data = source.read()

        with open(VERIFIED_FILE, "w", encoding="utf-8", newline="") as destination:
            destination.write(data)

        print(f"Verified file created: {VERIFIED_FILE}")
        print("VALIDATION PASSED")
        print("Total records: 500")
        print("All required fields: OK")
        print("Categories: OK")
        print("Coordinates: OK")
        print("Status values: OK")
        print("Image paths: OK")
        print("Synthetic flag: OK")
        print("Duplicate complaint IDs: None")


if __name__ == "__main__":
    validate_dataset()