from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE = PROJECT_ROOT / "data" / "duplicates" / "candidate_pairs.csv"

# Recent-window values to inspect.
ANALYSIS_WINDOWS_DAYS = [7, 14, 30, 60, 90]


def load_data() -> pd.DataFrame:
    """Load and validate candidate_pairs.csv."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Candidate-pair file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "pair_id",
        "complaint_id_1",
        "complaint_id_2",
        "category_1",
        "category_2",
        "description_1",
        "description_2",
        "latitude_1",
        "longitude_1",
        "latitude_2",
        "longitude_2",
        "submitted_time_1",
        "submitted_time_2",
        "distance_meters",
        "time_difference_hours",
        "actual_duplicate",
        "label_notes",
    ]

    missing = [column for column in required_columns if column not in df.columns]

    if missing:
        raise ValueError(
            "candidate_pairs.csv is missing required columns:\n"
            + "\n".join(f" - {column}" for column in missing)
        )

    numeric_columns = [
        "complaint_id_1",
        "complaint_id_2",
        "latitude_1",
        "longitude_1",
        "latitude_2",
        "longitude_2",
        "distance_meters",
        "time_difference_hours",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["submitted_time_1"] = pd.to_datetime(
        df["submitted_time_1"],
        errors="coerce",
        utc=True,
    )

    df["submitted_time_2"] = pd.to_datetime(
        df["submitted_time_2"],
        errors="coerce",
        utc=True,
    )

    return df


def print_section(title: str) -> None:
    print()
    print(title)
    print("-" * 72)


def print_numeric_distribution(
    series: pd.Series,
    label: str,
    unit: str = "",
) -> None:
    """Print descriptive statistics and useful project buckets."""
    clean = pd.to_numeric(series, errors="coerce").dropna()

    print(f"\n{label}")

    if clean.empty:
        print("  No valid values available.")
        return

    suffix = f" {unit}" if unit else ""

    print(f"  Count       : {len(clean)}")
    print(f"  Minimum     : {clean.min():.3f}{suffix}")
    print(f"  Q1 (25%)    : {clean.quantile(0.25):.3f}{suffix}")
    print(f"  Median      : {clean.median():.3f}{suffix}")
    print(f"  Mean        : {clean.mean():.3f}{suffix}")
    print(f"  Q3 (75%)    : {clean.quantile(0.75):.3f}{suffix}")
    print(f"  Maximum     : {clean.max():.3f}{suffix}")

    if label == "Distance distribution":
        bins = [-0.001, 50, 100, 150, 200, 250, 300]
        names = [
            "0–50 m",
            "50–100 m",
            "100–150 m",
            "150–200 m",
            "200–250 m",
            "250–300 m",
        ]

    elif label == "Time-difference distribution":
        bins = [-0.001, 6, 12, 24, 48, 72, 168, float("inf")]
        names = [
            "0–6 h",
            "6–12 h",
            "12–24 h",
            "1–2 days",
            "2–3 days",
            "3–7 days",
            ">7 days",
        ]

    else:
        return

    bucketed = pd.cut(
        clean,
        bins=bins,
        labels=names,
        include_lowest=True,
        right=True,
    )

    counts = bucketed.value_counts(sort=False)

    print("  Buckets:")
    for bucket, count in counts.items():
        print(f"    {str(bucket):>10} : {int(count)}")


def main() -> None:
    print("=" * 72)
    print("CIVICBRAIN STEP 12 — CANDIDATE PAIR ANALYSIS")
    print("=" * 72)

    df = load_data()

    print(f"Input file               : {INPUT_FILE}")
    print(f"Candidate pairs loaded   : {len(df)}")

    invalid_distance = int(df["distance_meters"].isna().sum())
    invalid_time = int(df["time_difference_hours"].isna().sum())

    print(f"Invalid distance values  : {invalid_distance}")
    print(f"Invalid time values      : {invalid_time}")

    usable = df.dropna(
        subset=["distance_meters", "time_difference_hours"]
    ).copy()

    print(f"Usable candidate pairs   : {len(usable)}")

    if usable.empty:
        raise ValueError("No usable candidate pairs available.")

    # ------------------------------------------------------------
    # 1. RECENT-WINDOW ANALYSIS
    # ------------------------------------------------------------
    print_section("1. RECENT-WINDOW ANALYSIS")

    print(
        f"{'Window':>12} | {'All pairs':>10} | "
        f"{'Same category':>14} | {'Different category':>18}"
    )
    print("-" * 72)

    usable["category_1_norm"] = (
        usable["category_1"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    usable["category_2_norm"] = (
        usable["category_2"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    usable["category_match"] = (
        usable["category_1_norm"] == usable["category_2_norm"]
    )

    for window_days in ANALYSIS_WINDOWS_DAYS:
        threshold_hours = window_days * 24

        window_df = usable[
            usable["time_difference_hours"] <= threshold_hours
        ]

        total = len(window_df)
        same_category = int(window_df["category_match"].sum())
        different_category = total - same_category

        print(
            f"{window_days:>9} days | "
            f"{total:>10} | "
            f"{same_category:>14} | "
            f"{different_category:>18}"
        )

    # ------------------------------------------------------------
    # 2. CATEGORY MATCH ANALYSIS
    # ------------------------------------------------------------
    print_section("2. CATEGORY MATCH ANALYSIS")

    category_match_count = int(usable["category_match"].sum())
    category_mismatch_count = len(usable) - category_match_count

    print(f"Same category             : {category_match_count}")
    print(f"Different category        : {category_mismatch_count}")
    print(
        f"Same-category percentage  : "
        f"{category_match_count / len(usable) * 100:.2f}%"
    )
    print(
        f"Different-category %      : "
        f"{category_mismatch_count / len(usable) * 100:.2f}%"
    )

    print("\nCategory-pair matrix:")

    category_matrix = pd.crosstab(
        usable["category_1_norm"].replace("", "(blank)"),
        usable["category_2_norm"].replace("", "(blank)"),
        margins=True,
    )

    print(category_matrix.to_string())

    # ------------------------------------------------------------
    # 3. SAME-CATEGORY WINDOW ANALYSIS
    # ------------------------------------------------------------
    print_section("3. SAME-CATEGORY PAIRS BY RECENT WINDOW")

    print(
        f"{'Window':>12} | {'Same-category pairs':>20} | "
        f"{'% of all candidates':>20}"
    )
    print("-" * 72)

    for window_days in ANALYSIS_WINDOWS_DAYS:
        threshold_hours = window_days * 24

        window_df = usable[
            usable["time_difference_hours"] <= threshold_hours
        ]

        same_category = int(window_df["category_match"].sum())

        print(
            f"{window_days:>9} days | "
            f"{same_category:>20} | "
            f"{same_category / len(usable) * 100:>19.2f}%"
        )

    # ------------------------------------------------------------
    # 4. DISTANCE DISTRIBUTION
    # ------------------------------------------------------------
    print_section("4. DISTANCE DISTRIBUTION")

    print_numeric_distribution(
        usable["distance_meters"],
        "Distance distribution",
        "m",
    )

    # ------------------------------------------------------------
    # 5. TIME-DIFFERENCE DISTRIBUTION
    # ------------------------------------------------------------
    print_section("5. TIME-DIFFERENCE DISTRIBUTION")

    print_numeric_distribution(
        usable["time_difference_hours"],
        "Time-difference distribution",
        "hours",
    )

    # ------------------------------------------------------------
    # 6. DISTANCE + CATEGORY ANALYSIS
    # ------------------------------------------------------------
    print_section("6. SAME-CATEGORY DISTANCE ANALYSIS")

    same_category_df = usable[
        usable["category_match"]
    ].copy()

    if same_category_df.empty:
        print("No same-category candidate pairs found.")
    else:
        print(
            f"Same-category candidate pairs : "
            f"{len(same_category_df)}"
        )

        print_numeric_distribution(
            same_category_df["distance_meters"],
            "Same-category distance distribution",
            "m",
        )

    # ------------------------------------------------------------
    # 7. SAME-CATEGORY TIME ANALYSIS
    # ------------------------------------------------------------
    print_section("7. SAME-CATEGORY TIME-DIFFERENCE ANALYSIS")

    if same_category_df.empty:
        print("No same-category candidate pairs found.")
    else:
        print_numeric_distribution(
            same_category_df["time_difference_hours"],
            "Same-category time-difference distribution",
            "hours",
        )

    # ------------------------------------------------------------
    # 8. DATA-QUALITY CHECKS
    # ------------------------------------------------------------
    print_section("8. DATA-QUALITY CHECKS")

    duplicate_pair_ids = int(
        usable["pair_id"].duplicated(keep=False).sum()
    )

    self_pairs = int(
        (usable["complaint_id_1"] == usable["complaint_id_2"]).sum()
    )

    outside_spatial_baseline = int(
        (usable["distance_meters"] > 300).sum()
    )

    negative_distance = int(
        (usable["distance_meters"] < 0).sum()
    )

    negative_time = int(
        (usable["time_difference_hours"] < 0).sum()
    )

    print(f"Duplicate pair_id rows   : {duplicate_pair_ids}")
    print(f"Self-pairs                : {self_pairs}")
    print(f"Distance > 300m           : {outside_spatial_baseline}")
    print(f"Negative distance         : {negative_distance}")
    print(f"Negative time difference : {negative_time}")

    # ------------------------------------------------------------
    # 9. LABEL STATUS
    # ------------------------------------------------------------
    print_section("9. LABEL STATUS")

    labels = (
        usable["actual_duplicate"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    labeled = labels.isin(["0", "1"])

    duplicate_labels = int((labels == "1").sum())
    non_duplicate_labels = int((labels == "0").sum())
    unlabeled = int((~labeled).sum())

    print(f"Duplicate labels (1)     : {duplicate_labels}")
    print(f"Non-duplicate labels (0) : {non_duplicate_labels}")
    print(f"Unlabeled pairs          : {unlabeled}")

    # ------------------------------------------------------------
    # 10. OVERALL SUMMARY
    # ------------------------------------------------------------
    print_section("10. COMPLETE SUMMARY")

    print(f"Total candidate pairs     : {len(usable)}")
    print(f"Same-category pairs       : {category_match_count}")
    print(f"Different-category pairs  : {category_mismatch_count}")
    print(
        f"Average distance          : "
        f"{usable['distance_meters'].mean():.3f} m"
    )
    print(
        f"Median distance           : "
        f"{usable['distance_meters'].median():.3f} m"
    )
    print(
        f"Maximum distance          : "
        f"{usable['distance_meters'].max():.3f} m"
    )
    print(
        f"Average time difference   : "
        f"{usable['time_difference_hours'].mean():.3f} hours"
    )
    print(
        f"Median time difference    : "
        f"{usable['time_difference_hours'].median():.3f} hours"
    )
    print(
        f"Maximum time difference   : "
        f"{usable['time_difference_hours'].max():.3f} hours"
    )

    print()
    print("Recent-window counts:")

    for window_days in ANALYSIS_WINDOWS_DAYS:
        threshold_hours = window_days * 24

        count = int(
            (
                usable["time_difference_hours"]
                <= threshold_hours
            ).sum()
        )

        print(f"  {window_days:>3} days : {count}")

    # ------------------------------------------------------------
    # 11. INTERPRETATION / RULES
    # ------------------------------------------------------------
    print_section("11. INTERPRETATION NOTES")

    print(
        "1. The 300 m spatial radius is the current CivicBrain "
        "project baseline."
    )
    print(
        "2. The recent-window value is still under evaluation; "
        "do not freeze it only from pair counts."
    )
    print(
        "3. Category match is a supporting signal, not proof "
        "that two complaints are duplicates."
    )
    print(
        "4. Final duplicate decisions require text similarity "
        "plus location and recency evidence."
    )
    print(
        "5. actual_duplicate must be assigned only after "
        "reviewing the complaint pair."
    )
    print(
        "6. Precision, Recall and F1 must be calculated only "
        "after positive and negative labels are available."
    )

    print()
    print("=" * 72)
    print("CANDIDATE PAIR ANALYSIS COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()