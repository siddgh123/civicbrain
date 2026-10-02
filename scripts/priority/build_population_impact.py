import csv
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMPLAINT_WARD_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "complaint_ward_mapping.csv"
)

WARD_SCORE_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "ward_population_scores.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "population_impact.csv"
)


# ============================================================
# LOAD WARD POPULATION SCORES
# ============================================================

def load_ward_scores():
    if not WARD_SCORE_FILE.exists():
        raise FileNotFoundError(
            f"Ward score file not found: {WARD_SCORE_FILE}"
        )

    ward_scores = {}

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

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "ward_population_scores.csv is missing required columns."
            )

        for row in reader:
            ward_number = int(row["ward_number"])

            ward_scores[ward_number] = {
                "ward_population": int(row["ward_population"]),
                "population_score": float(row["population_score"]),
                "population_source": row["population_source"].strip(),
                "population_source_year": int(
                    row["population_source_year"]
                ),
            }

    if len(ward_scores) != 23:
        raise ValueError(
            f"Expected 23 wards, found {len(ward_scores)}"
        )

    return ward_scores


# ============================================================
# BUILD COMPLAINT POPULATION IMPACT
# ============================================================

def build_population_impact(ward_scores):
    if not COMPLAINT_WARD_FILE.exists():
        raise FileNotFoundError(
            f"Complaint ward mapping file not found: "
            f"{COMPLAINT_WARD_FILE}"
        )

    results = []
    seen_complaints = set()

    with COMPLAINT_WARD_FILE.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "complaint_id",
            "ward_number",
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "complaint_ward_mapping.csv is missing required columns."
            )

        for row in reader:
            complaint_id = int(row["complaint_id"])
            ward_number = int(row["ward_number"])

            if complaint_id in seen_complaints:
                raise ValueError(
                    f"Duplicate complaint_id found: {complaint_id}"
                )

            seen_complaints.add(complaint_id)

            if ward_number not in ward_scores:
                raise ValueError(
                    f"Ward {ward_number} not found "
                    f"in ward population scores."
                )

            ward_data = ward_scores[ward_number]

            results.append({
                "complaint_id": complaint_id,
                "ward_id": ward_number,
                "ward_population": ward_data["ward_population"],
                "population_score": ward_data["population_score"],
                "population_source": ward_data["population_source"],
                "population_source_year": (
                    ward_data["population_source_year"]
                ),
            })

    if len(results) != 500:
        raise ValueError(
            f"Expected 500 complaints, found {len(results)}"
        )

    return results


# ============================================================
# SAVE OUTPUT
# ============================================================

def save_results(results):
    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [
            "complaint_id",
            "ward_id",
            "ward_population",
            "population_score",
            "population_source",
            "population_source_year",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)


# ============================================================
# MAIN
# ============================================================

def main():
    ward_scores = load_ward_scores()

    results = build_population_impact(ward_scores)

    save_results(results)

    print("=" * 60)
    print("CIVICBRAIN POPULATION IMPACT DATASET")
    print("=" * 60)
    print(f"Complaints processed : {len(results)}")
    print(f"Unique wards used    : {len(ward_scores)}")
    print(f"Output               : {OUTPUT_FILE}")
    print("POPULATION IMPACT DATASET CREATED")
    print("=" * 60)


if __name__ == "__main__":
    main()