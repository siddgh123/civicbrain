import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RULES_FILE = (
    PROJECT_ROOT
    / "data"
    / "priority"
    / "severity_scoring_rules.csv"
)


def load_severity_scores():
    if not RULES_FILE.exists():
        raise FileNotFoundError(
            f"Severity rules file not found: {RULES_FILE}"
        )

    scores = {}

    with RULES_FILE.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            level = row["severity_level"].strip().upper()
            score = float(row["severity_score"])

            if not 0 <= score <= 100:
                raise ValueError(
                    f"Invalid severity score for {level}: {score}"
                )

            scores[level] = score

    required_levels = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    if set(scores.keys()) != required_levels:
        raise ValueError(
            "Severity rules must contain exactly "
            "LOW, MEDIUM, HIGH and CRITICAL."
        )

    return scores


def get_severity_score(
    severity_level: str,
    scores: dict
) -> float:

    level = severity_level.strip().upper()

    if level not in scores:
        raise ValueError(
            f"Unknown severity level: {severity_level}"
        )

    return scores[level]


def main():

    scores = load_severity_scores()

    print("=" * 50)
    print("CIVICBRAIN SEVERITY MAPPER TEST")
    print("=" * 50)

    test_levels = [
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]

    for level in test_levels:
        score = get_severity_score(level, scores)
        print(
            f"{level:<10} -> {score:>6.2f}"
        )

    print("-" * 50)
    print("SEVERITY MAPPING TEST PASSED")
    print("=" * 50)


if __name__ == "__main__":
    main()