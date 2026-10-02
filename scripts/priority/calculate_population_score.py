import csv
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

POPULATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "official_ward_population.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "ward_population_scores.csv"
)


# ============================================================
# LOAD OFFICIAL WARD POPULATION
# ============================================================

def load_population_data():
    if not POPULATION_FILE.exists():
        raise FileNotFoundError(
            f"Population file not found: {POPULATION_FILE}"
        )

    data = []

    with POPULATION_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "ward_number",
            "ward_population",
            "source",
            "source_year",
        }

        if not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "official_ward_population.csv is missing required columns."
            )

        for row in reader:
            ward_number = int(row["ward_number"])
            ward_population = int(row["ward_population"])

            if ward_population < 0:
                raise ValueError(
                    f"Invalid population for Ward {ward_number}"
                )

            data.append({
                "ward_number": ward_number,
                "ward_population": ward_population,
                "source": row["source"].strip(),
                "source_year": int(row["source_year"]),
            })

    if len(data) != 23:
        raise ValueError(
            f"Expected 23 wards, found {len(data)}"
        )

    return data


# ============================================================
# CALCULATE POPULATION SCORES
# ============================================================

def calculate_scores(data):
    max_population = max(
        row["ward_population"]
        for row in data
    )

    if max_population <= 0:
        raise ValueError(
            "Maximum ward population must be greater than zero."
        )

    results = []

    for row in data:
        score = (
            row["ward_population"]
            / max_population
        ) * 100

        results.append({
            "ward_number": row["ward_number"],
            "ward_population": row["ward_population"],
            "population_score": round(score, 2),
            "population_source": row["source"],
            "population_source_year": row["source_year"],
        })

    return results, max_population


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(results):
    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [
            "ward_number",
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
    data = load_population_data()

    results, max_population = calculate_scores(data)

    save_results(results)

    print("=" * 60)
    print("CIVICBRAIN POPULATION IMPACT SCORE")
    print("=" * 60)

    print(f"Total wards           : {len(data)}")
    print(f"Maximum ward population: {max_population}")

    print("-" * 60)

    for row in results:
        print(
            f"Ward {row['ward_number']:>2} | "
            f"Population: {row['ward_population']:>4} | "
            f"Score: {row['population_score']:>6.2f}"
        )

    print("-" * 60)
    print(f"Output: {OUTPUT_FILE}")
    print("POPULATION SCORE CALCULATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()