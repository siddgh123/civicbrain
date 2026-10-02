import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "population": PROJECT_ROOT / "data" / "priority" / "population_impact.csv",
    "severity": PROJECT_ROOT / "data" / "priority" / "severity_scores.csv",
    "location": PROJECT_ROOT / "data" / "priority" / "location_risk_scores.csv",
    "frequency": PROJECT_ROOT / "data" / "priority" / "frequency_scores.csv",
    "wait": PROJECT_ROOT / "data" / "priority" / "wait_time_scores.csv",
    "infrastructure": PROJECT_ROOT / "data" / "priority" / "infrastructure_importance_scores.csv",
    "historical": PROJECT_ROOT / "data" / "priority" / "historical_risk_scores.csv",
}

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "priority_factor_dataset.csv"
)


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def index_by_complaint_id(rows, filename):
    indexed = {}

    for row in rows:
        complaint_id = int(row["complaint_id"])

        if complaint_id in indexed:
            raise ValueError(
                f"Duplicate complaint_id {complaint_id} in {filename}"
            )

        indexed[complaint_id] = row

    if len(indexed) != 500:
        raise ValueError(
            f"{filename}: expected 500 complaints, found {len(indexed)}"
        )

    return indexed


def main():

    population = index_by_complaint_id(
        load_csv(FILES["population"]),
        "population_impact.csv"
    )

    severity = index_by_complaint_id(
        load_csv(FILES["severity"]),
        "severity_scores.csv"
    )

    location = index_by_complaint_id(
        load_csv(FILES["location"]),
        "location_risk_scores.csv"
    )

    frequency = index_by_complaint_id(
        load_csv(FILES["frequency"]),
        "frequency_scores.csv"
    )

    wait = index_by_complaint_id(
        load_csv(FILES["wait"]),
        "wait_time_scores.csv"
    )

    infrastructure = index_by_complaint_id(
        load_csv(FILES["infrastructure"]),
        "infrastructure_importance_scores.csv"
    )

    historical = index_by_complaint_id(
        load_csv(FILES["historical"]),
        "historical_risk_scores.csv"
    )

    complaint_ids = set(population.keys())

    datasets = {
        "severity": severity,
        "location": location,
        "frequency": frequency,
        "wait": wait,
        "infrastructure": infrastructure,
        "historical": historical,
    }

    for name, dataset in datasets.items():
        if set(dataset.keys()) != complaint_ids:
            raise ValueError(
                f"Complaint IDs do not match in {name} dataset."
            )

    results = []

    for complaint_id in sorted(complaint_ids):

        p = population[complaint_id]
        s = severity[complaint_id]
        l = location[complaint_id]
        f = frequency[complaint_id]
        w = wait[complaint_id]
        i = infrastructure[complaint_id]
        h = historical[complaint_id]

        results.append({
            "complaint_id": complaint_id,

            "ward_id": p["ward_id"],
            "ward_population": p["ward_population"],
            "population_score": p["population_score"],
            "population_source": p["population_source"],
            "population_source_year": p["population_source_year"],

            "severity_level": s["severity_level"],
            "severity_score": s["severity_score"],
            "severity_source": s["severity_source"],

            "location_risk_score": l["location_risk_score"],

            "frequency_count": f["frequency_count"],
            "frequency_score": f["frequency_score"],

            "wait_days": w["wait_days"],
            "wait_time_score": w["wait_time_score"],

            "road_id": i["road_id"],
            "road_type": i["road_type"],
            "infrastructure_importance_score":
                i["infrastructure_importance_score"],
            "infrastructure_source":
                i["infrastructure_source"],

            "historical_count": h["historical_count"],
            "historical_risk_score":
                h["historical_risk_score"],
        })

    fieldnames = list(results[0].keys())

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    print("=" * 70)
    print("CIVICBRAIN PRIORITY FACTOR DATASET")
    print("=" * 70)
    print(f"Complaints merged : {len(results)}")
    print(f"Factors merged    : 7")
    print(f"Output            : {OUTPUT_FILE}")
    print("PRIORITY FACTOR DATASET CREATED")
    print("=" * 70)


if __name__ == "__main__":
    main()