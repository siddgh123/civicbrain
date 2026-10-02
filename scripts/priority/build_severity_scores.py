import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "resources"
    / "processed"
    / "resource_dataset.csv"
)

SEVERITY_RULES_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "severity_scoring_rules.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "severity_scores.csv"
)


def load_severity_rules():
    rules = {}

    with SEVERITY_RULES_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            level = row["severity_level"].strip().upper()
            score = float(row["severity_score"])

            rules[level] = score

    required_levels = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    if set(rules.keys()) != required_levels:
        raise ValueError(
            "Severity rules must contain LOW, MEDIUM, HIGH and CRITICAL."
        )

    return rules


def build_severity_scores(rules):
    results = []
    seen_ids = set()

    with RESOURCE_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "complaint_id",
            "severity",
            "severity_source",
        }

        if not required_columns.issubset(
            set(reader.fieldnames or [])
        ):
            raise ValueError(
                "resource_dataset.csv is missing required columns."
            )

        for row in reader:
            complaint_id = int(row["complaint_id"])

            if complaint_id in seen_ids:
                raise ValueError(
                    f"Duplicate complaint_id: {complaint_id}"
                )

            seen_ids.add(complaint_id)

            severity_level = row["severity"].strip().upper()

            if severity_level not in rules:
                raise ValueError(
                    f"Invalid severity '{severity_level}' "
                    f"for complaint {complaint_id}"
                )

            results.append({
                "complaint_id": complaint_id,
                "severity_level": severity_level,
                "severity_score": rules[severity_level],
                "severity_source": row["severity_source"].strip(),
            })

    if len(results) != 500:
        raise ValueError(
            f"Expected 500 complaints, found {len(results)}"
        )

    return results


def save_results(results):
    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fieldnames = [
            "complaint_id",
            "severity_level",
            "severity_score",
            "severity_source",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)


def main():
    rules = load_severity_rules()
    results = build_severity_scores(rules)
    save_results(results)

    print("=" * 60)
    print("CIVICBRAIN SEVERITY SCORE DATASET")
    print("=" * 60)
    print(f"Complaints processed : {len(results)}")
    print(f"Output               : {OUTPUT_FILE}")
    print("SEVERITY SCORE DATASET CREATED")
    print("=" * 60)


if __name__ == "__main__":
    main()