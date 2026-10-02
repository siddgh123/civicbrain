from __future__ import annotations

from pathlib import Path
import csv
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "duplicates" / "duplicate_label_review.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "duplicates" / "duplicate_label_review_labeled.csv"

REQUIRED_COLUMNS = [
    "review_order",
    "pair_id",
    "complaint_id_1",
    "complaint_id_2",
    "category_1",
    "category_2",
    "description_1",
    "description_2",
    "distance_meters",
    "distance_bucket",
    "time_difference_hours",
    "time_bucket",
    "category_match",
    "actual_duplicate",
    "label_notes",
]


def load_review_file() -> pd.DataFrame:
    if OUTPUT_FILE.exists():
        df = pd.read_csv(OUTPUT_FILE, dtype=str)
        source = OUTPUT_FILE
    elif INPUT_FILE.exists():
        df = pd.read_csv(INPUT_FILE, dtype=str)
        source = INPUT_FILE
    else:
        raise FileNotFoundError(
            "Neither review file exists.\n"
            f"Expected input:\n{INPUT_FILE}\n"
            f"Expected labeled output:\n{OUTPUT_FILE}"
        )

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {c}" for c in missing)
        )

    # Ensure workflow columns exist.
    if "review_status" not in df.columns:
        df["review_status"] = ""

    if "reviewer_notes" not in df.columns:
        df["reviewer_notes"] = ""

    return df, source


def save(df: pd.DataFrame) -> None:
    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
        quoting=csv.QUOTE_MINIMAL,
    )


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def main() -> None:
    print("=" * 78)
    print("CIVICBRAIN STEP 12 — DUPLICATE PAIR REVIEW WORKFLOW")
    print("=" * 78)

    df, source = load_review_file()

    print(f"Review file loaded : {source}")
    print(f"Total review pairs : {len(df)}")

    # Convert blank values consistently.
    for column in [
        "actual_duplicate",
        "label_notes",
        "review_status",
        "reviewer_notes",
    ]:
        df[column] = df[column].fillna("").astype(str)

    # Find first unreviewed row.
    reviewed_statuses = {
        "DUPLICATE",
        "NON_DUPLICATE",
        "UNCERTAIN",
    }

    unreviewed_indices = [
        idx
        for idx, row in df.iterrows()
        if clean(row["review_status"]).upper() not in reviewed_statuses
    ]

    if not unreviewed_indices:
        print()
        print("All review pairs are already reviewed.")
        print(f"Output : {OUTPUT_FILE}")
        print("=" * 78)
        return

    print(f"Unreviewed pairs remaining : {len(unreviewed_indices)}")
    print()
    print("LABEL RULES")
    print("-" * 78)
    print("DUPLICATE (1)    = both complaints refer to the same real-world civic issue.")
    print("NON_DUPLICATE (0)= complaints refer to different real-world issues.")
    print(
        "UNCERTAIN        = available evidence is insufficient to decide safely; "
        "do not force 0 or 1."
    )
    print()
    print("COMMANDS")
    print("1 = DUPLICATE")
    print("0 = NON_DUPLICATE")
    print("U = UNCERTAIN")
    print("S = SKIP this pair for now")
    print("Q = SAVE and quit")
    print("=" * 78)

    for idx in unreviewed_indices:
        row = df.loc[idx]

        print()
        print("-" * 78)
        print(
            f"Review order      : {clean(row['review_order'])}"
        )
        print(
            f"Pair ID           : {clean(row['pair_id'])}"
        )
        print(
            f"Complaint IDs     : "
            f"{clean(row['complaint_id_1'])}  vs  "
            f"{clean(row['complaint_id_2'])}"
        )
        print(
            f"Category          : "
            f"{clean(row['category_1'])}  vs  "
            f"{clean(row['category_2'])}"
        )
        print(
            f"Category match    : {clean(row['category_match'])}"
        )
        print(
            f"Distance          : "
            f"{clean(row['distance_meters'])} m "
            f"({clean(row['distance_bucket'])})"
        )
        print(
            f"Time difference   : "
            f"{clean(row['time_difference_hours'])} hours "
            f"({clean(row['time_bucket'])})"
        )

        print()
        print("COMPLAINT 1")
        print(clean(row["description_1"]))

        print()
        print("COMPLAINT 2")
        print(clean(row["description_2"]))

        while True:
            decision = input(
                "\nDecision [1/0/U/S/Q]: "
            ).strip().upper()

            if decision == "Q":
                save(df)
                print()
                print("Progress saved.")
                print(f"Output : {OUTPUT_FILE}")
                return

            if decision == "S":
                print("Pair skipped.")
                break

            if decision not in {"1", "0", "U"}:
                print("Please enter 1, 0, U, S, or Q.")
                continue

            if decision == "1":
                status = "DUPLICATE"
                actual = "1"
            elif decision == "0":
                status = "NON_DUPLICATE"
                actual = "0"
            else:
                status = "UNCERTAIN"
                actual = ""

            print()
            note = input(
                "Evidence/reason note "
                "(brief but specific): "
            ).strip()

            if status == "UNCERTAIN" and not note:
                note = "Insufficient evidence to determine whether the pair refers to the same real-world issue."

            df.at[idx, "review_status"] = status
            df.at[idx, "actual_duplicate"] = actual
            df.at[idx, "reviewer_notes"] = note

            # Keep label_notes synchronized for compatibility with the
            # original review file.
            df.at[idx, "label_notes"] = note

            save(df)

            print(
                f"Saved: {status} | "
                f"pair={clean(row['pair_id'])}"
            )
            break

    save(df)

    reviewed = (
        df["review_status"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    print()
    print("=" * 78)
    print("REVIEW SESSION COMPLETE")
    print("=" * 78)
    print(
        f"DUPLICATE     : {(reviewed == 'DUPLICATE').sum()}"
    )
    print(
        f"NON_DUPLICATE : {(reviewed == 'NON_DUPLICATE').sum()}"
    )
    print(
        f"UNCERTAIN     : {(reviewed == 'UNCERTAIN').sum()}"
    )
    print(
        f"UNREVIEWED    : "
        f"{(~reviewed.isin(['DUPLICATE', 'NON_DUPLICATE', 'UNCERTAIN'])).sum()}"
    )
    print(f"Output        : {OUTPUT_FILE}")
    print("=" * 78)


if __name__ == "__main__":
    main()
