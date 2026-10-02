from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "duplicates" / "candidate_pairs.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "duplicates" / "duplicate_label_review.csv"

# Number of pairs to prepare for manual labeling.
# The selection is deterministic so the same input produces the same review set.
TARGET_REVIEW_PAIRS = 300

DISTANCE_BINS = [-0.001, 50, 100, 150, 200, 250, 300]
DISTANCE_LABELS = [
    "0-50m",
    "50-100m",
    "100-150m",
    "150-200m",
    "200-250m",
    "250-300m",
]

TIME_BINS_HOURS = [-0.001, 24, 72, 168, 720, 1440, 2160]
TIME_LABELS = [
    "0-1d",
    "1-3d",
    "3-7d",
    "7-30d",
    "30-60d",
    "60-90d",
]


def main() -> None:
    print("=" * 72)
    print("CIVICBRAIN STEP 12 — STRATIFIED DUPLICATE LABEL REVIEW SET")
    print("=" * 72)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Candidate pair file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = [
        "pair_id",
        "complaint_id_1",
        "complaint_id_2",
        "category_1",
        "category_2",
        "description_1",
        "description_2",
        "distance_meters",
        "time_difference_hours",
        "actual_duplicate",
        "label_notes",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {c}" for c in missing)
        )

    # Numeric cleanup.
    df["distance_meters"] = pd.to_numeric(
        df["distance_meters"], errors="coerce"
    )
    df["time_difference_hours"] = pd.to_numeric(
        df["time_difference_hours"], errors="coerce"
    )

    df = df.dropna(
        subset=["distance_meters", "time_difference_hours"]
    ).copy()

    # Normalize category values for reliable comparison.
    df["category_1_norm"] = (
        df["category_1"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["category_2_norm"] = (
        df["category_2"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["category_match"] = (
        df["category_1_norm"] == df["category_2_norm"]
    )

    # Distance and time strata.
    df["distance_bucket"] = pd.cut(
        df["distance_meters"],
        bins=DISTANCE_BINS,
        labels=DISTANCE_LABELS,
        include_lowest=True,
        right=True,
    )

    df["time_bucket"] = pd.cut(
        df["time_difference_hours"],
        bins=TIME_BINS_HOURS,
        labels=TIME_LABELS,
        include_lowest=True,
        right=True,
    )

    # We intentionally do NOT use actual_duplicate for selection.
    # All pairs are currently unlabeled, and labels must come from human review.
    df["actual_duplicate"] = ""
    df["label_notes"] = ""

    print(f"Input candidate pairs      : {len(df)}")
    print(
        f"Same-category candidates   : "
        f"{int(df['category_match'].sum())}"
    )
    print(
        f"Different-category         : "
        f"{int((~df['category_match']).sum())}"
    )

    # ------------------------------------------------------------
    # Selection strategy
    #
    # 1. Keep all same-category pairs when there are <= 150.
    #    This is important because same-category pairs are the
    #    most plausible duplicates and form only a small portion
    #    of the candidate set.
    #
    # 2. Add different-category pairs using deterministic
    #    stratified sampling across distance x time buckets.
    #
    # 3. Never use duplicate labels to select the sample.
    # ------------------------------------------------------------

    same = df[df["category_match"]].copy()
    different = df[~df["category_match"]].copy()

    same_limit = min(len(same), 150)

    if len(same) > same_limit:
        # Deterministic stratified sample from same-category pairs.
        same_sample = (
            same.groupby(
                ["distance_bucket", "time_bucket"],
                observed=True,
                group_keys=False,
            )
            .apply(
                lambda g: g.sample(
                    n=max(
                        1,
                        round(
                            len(g)
                            / len(same)
                            * same_limit
                        ),
                    )
                    if len(g) > 0
                    else g
                ),
                include_groups=False,
            )
            .reset_index(drop=True)
        )

        # Exact-size correction if proportional rounding produced
        # too many or too few rows.
        if len(same_sample) > same_limit:
            same_sample = same_sample.sample(
                n=same_limit, random_state=42
            )
        elif len(same_sample) < same_limit:
            remaining = same.loc[
                ~same["pair_id"].isin(same_sample["pair_id"])
            ]
            extra = remaining.sample(
                n=min(
                    same_limit - len(same_sample),
                    len(remaining),
                ),
                random_state=42,
            )
            same_sample = pd.concat(
                [same_sample, extra],
                ignore_index=True,
            )
    else:
        same_sample = same.copy()

    remaining_target = max(
        0,
        min(
            TARGET_REVIEW_PAIRS - len(same_sample),
            len(different),
        ),
    )

    if remaining_target > 0:
        different_sample = (
            different.groupby(
                ["distance_bucket", "time_bucket"],
                observed=True,
                group_keys=False,
            )
            .apply(
                lambda g: g.sample(
                    n=max(
                        1,
                        round(
                            len(g)
                            / len(different)
                            * remaining_target
                        ),
                    )
                    if len(g) > 0
                    else g
                ),
                include_groups=False,
            )
            .reset_index(drop=True)
        )

        if len(different_sample) > remaining_target:
            different_sample = different_sample.sample(
                n=remaining_target, random_state=42
            )
        elif len(different_sample) < remaining_target:
            remaining = different.loc[
                ~different["pair_id"].isin(
                    different_sample["pair_id"]
                )
            ]
            extra = remaining.sample(
                n=min(
                    remaining_target - len(different_sample),
                    len(remaining),
                ),
                random_state=42,
            )
            different_sample = pd.concat(
                [different_sample, extra],
                ignore_index=True,
            )
    else:
        different_sample = different.iloc[0:0].copy()

    review = pd.concat(
        [same_sample, different_sample],
        ignore_index=True,
    )

    # Deterministic review order for the human annotator.
    review = review.sort_values(
        [
            "category_match",
            "distance_bucket",
            "time_bucket",
            "pair_id",
        ],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)

    review["review_order"] = range(1, len(review) + 1)

    # Keep only fields needed for manual labeling.
    output_columns = [
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

    review = review[output_columns]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    print()
    print("REVIEW SET SUMMARY")
    print("-" * 72)
    print(f"Review pairs created       : {len(review)}")
    print(
        f"Same-category selected     : "
        f"{int(review['category_match'].sum())}"
    )
    print(
        f"Different-category selected: "
        f"{int((~review['category_match']).sum())}"
    )

    print()
    print("Distance strata:")
    print(
        review["distance_bucket"]
        .value_counts(sort=False)
        .to_string()
    )

    print()
    print("Time strata:")
    print(
        review["time_bucket"]
        .value_counts(sort=False)
        .to_string()
    )

    print()
    print("Category-match distribution:")
    print(
        review["category_match"]
        .map({True: "same", False: "different"})
        .value_counts()
        .to_string()
    )

    print()
    print("IMPORTANT:")
    print(
        "actual_duplicate is intentionally blank."
    )
    print(
        "Do not auto-label pairs from category, distance, "
        "or wording alone."
    )
    print(
        "A pair should be labeled 1 only when both complaints "
        "refer to the same real-world civic issue."
    )
    print(
        "A pair should be labeled 0 when the complaints refer "
        "to different real-world issues."
    )
    print(
        "Use label_notes to record the evidence/reasoning "
        "for every reviewed pair."
    )
    print(
        "Use an uncertain/manual-review note when the available "
        "evidence is insufficient to determine the relationship."
    )

    print()
    print(f"Output file                : {OUTPUT_FILE}")
    print("=" * 72)
    print("STRATIFIED LABEL REVIEW SET CREATED")
    print("=" * 72)


if __name__ == "__main__":
    main()
