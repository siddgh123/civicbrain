from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_text_similarity.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_feature_analysis.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_feature_summary.csv"
)

SPATIAL_RADIUS_M = 300

RECENT_WINDOWS_DAYS = [7, 14, 30, 60, 90]


def main() -> None:
    print("=" * 78)
    print("CIVICBRAIN STEP 12 — DUPLICATE FEATURE ANALYSIS")
    print("=" * 78)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = [
        "pair_id",
        "actual_duplicate",
        "text_similarity",
        "distance_meters",
        "time_difference_hours",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {column}" for column in missing)
        )

    for column in [
        "actual_duplicate",
        "text_similarity",
        "distance_meters",
        "time_difference_hours",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[required].isna().any().any():
        bad_rows = df[required].isna().any(axis=1).sum()
        raise ValueError(
            f"{bad_rows} rows contain missing required numeric values."
        )

    # ------------------------------------------------------------
    # Distance closeness
    #
    # 1.0 = same point
    # 0.0 = exactly 300 m or farther
    #
    # This is a feature representation, not a final weighting.
    # ------------------------------------------------------------

    df["distance_score"] = (
        1.0
        - (
            df["distance_meters"]
            / SPATIAL_RADIUS_M
        )
    ).clip(0.0, 1.0)

    # ------------------------------------------------------------
    # Time representation
    # ------------------------------------------------------------

    df["time_difference_days"] = (
        df["time_difference_hours"] / 24.0
    )

    # Recency closeness for multiple candidate windows.
    # No window is selected as final yet.
    for window_days in RECENT_WINDOWS_DAYS:
        window_hours = window_days * 24

        df[f"within_{window_days}d"] = (
            df["time_difference_hours"] <= window_hours
        )

        df[f"recency_score_{window_days}d"] = (
            1.0
            - (
                df["time_difference_hours"]
                / window_hours
            )
        ).clip(0.0, 1.0)

    # ------------------------------------------------------------
    # Pair group label
    # ------------------------------------------------------------

    df["label_group"] = df["actual_duplicate"].map(
        {
            1: "DUPLICATE",
            0: "NON_DUPLICATE",
        }
    )

    output_columns = [
        "pair_id",
        "pair_type",
        "complaint_id_1",
        "complaint_id_2",
        "category_1",
        "category_2",
        "category_match",
        "description_1",
        "description_2",
        "actual_duplicate",
        "label_group",
        "text_similarity",
        "distance_meters",
        "distance_score",
        "time_difference_hours",
        "time_difference_days",
    ]

    for window_days in RECENT_WINDOWS_DAYS:
        output_columns.extend(
            [
                f"within_{window_days}d",
                f"recency_score_{window_days}d",
            ]
        )

    output_columns.extend(
        [
            "model_name",
            "similarity_metric",
            "label_source",
        ]
    )

    output = df[
        [column for column in output_columns if column in df.columns]
    ].copy()

    # Round numeric values for stable CSV inspection.
    for column in [
        "text_similarity",
        "distance_meters",
        "distance_score",
        "time_difference_hours",
        "time_difference_days",
    ]:
        if column in output.columns:
            output[column] = output[column].round(6)

    for window_days in RECENT_WINDOWS_DAYS:
        column = f"recency_score_{window_days}d"
        output[column] = output[column].round(6)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Summary by label group
    # ------------------------------------------------------------

    summary_rows = []

    for label_group, group in output.groupby(
        "label_group",
        sort=True,
    ):
        row = {
            "label_group": label_group,
            "pair_count": len(group),
            "mean_text_similarity": round(
                group["text_similarity"].mean(),
                6,
            ),
            "median_text_similarity": round(
                group["text_similarity"].median(),
                6,
            ),
            "mean_distance_m": round(
                group["distance_meters"].mean(),
                3,
            ),
            "median_distance_m": round(
                group["distance_meters"].median(),
                3,
            ),
            "mean_distance_score": round(
                group["distance_score"].mean(),
                6,
            ),
            "mean_time_difference_days": round(
                group["time_difference_days"].mean(),
                3,
            ),
            "median_time_difference_days": round(
                group["time_difference_days"].median(),
                3,
            ),
        }

        for window_days in RECENT_WINDOWS_DAYS:
            within_column = f"within_{window_days}d"
            recency_column = f"recency_score_{window_days}d"

            row[
                f"within_{window_days}d_count"
            ] = int(group[within_column].sum())

            row[
                f"within_{window_days}d_percent"
            ] = round(
                group[within_column].mean() * 100,
                2,
            )

            row[
                f"mean_recency_score_{window_days}d"
            ] = round(
                group[recency_column].mean(),
                6,
            )

        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Window-level descriptive analysis
    # ------------------------------------------------------------

    print()
    print("1. INPUT")
    print("-" * 78)
    print(f"Pairs loaded                 : {len(output)}")
    print(
        f"Missing required values     : "
        f"{output[required].isna().any(axis=1).sum()}"
    )

    print()
    print("2. TEXT / DISTANCE / RECENCY SUMMARY")
    print("-" * 78)

    for label_group in ["DUPLICATE", "NON_DUPLICATE"]:
        group = output[
            output["label_group"] == label_group
        ]

        if group.empty:
            continue

        print(f"\n{label_group}")
        print(f"  Pairs                    : {len(group)}")
        print(
            f"  Mean text similarity    : "
            f"{group['text_similarity'].mean():.6f}"
        )
        print(
            f"  Median text similarity  : "
            f"{group['text_similarity'].median():.6f}"
        )
        print(
            f"  Mean distance           : "
            f"{group['distance_meters'].mean():.3f} m"
        )
        print(
            f"  Median distance         : "
            f"{group['distance_meters'].median():.3f} m"
        )
        print(
            f"  Mean distance score     : "
            f"{group['distance_score'].mean():.6f}"
        )
        print(
            f"  Mean time difference    : "
            f"{group['time_difference_days'].mean():.3f} days"
        )
        print(
            f"  Median time difference  : "
            f"{group['time_difference_days'].median():.3f} days"
        )

    print()
    print("3. RECENT-WINDOW ELIGIBILITY")
    print("-" * 78)

    print(
        f"{'Window':>12} | "
        f"{'Duplicate':>12} | "
        f"{'Non-duplicate':>15} | "
        f"{'All':>8}"
    )
    print("-" * 78)

    for window_days in RECENT_WINDOWS_DAYS:
        column = f"within_{window_days}d"

        duplicate_count = int(
            output.loc[
                output["label_group"] == "DUPLICATE",
                column,
            ].sum()
        )

        non_duplicate_count = int(
            output.loc[
                output["label_group"] == "NON_DUPLICATE",
                column,
            ].sum()
        )

        total_count = int(output[column].sum())

        print(
            f"{window_days:>9} days | "
            f"{duplicate_count:>12} | "
            f"{non_duplicate_count:>15} | "
            f"{total_count:>8}"
        )

    print()
    print("4. RECENCY SCORE SUMMARY")
    print("-" * 78)

    for window_days in RECENT_WINDOWS_DAYS:
        column = f"recency_score_{window_days}d"

        print(
            f"{window_days:>3} days -> "
            f"min={output[column].min():.6f}, "
            f"median={output[column].median():.6f}, "
            f"mean={output[column].mean():.6f}, "
            f"max={output[column].max():.6f}"
        )

    print()
    print("5. FEATURE SANITY CHECKS")
    print("-" * 78)

    print(
        f"Text similarity outside [0,1] : "
        f"{int(((output['text_similarity'] < 0) | (output['text_similarity'] > 1)).sum())}"
    )

    print(
        f"Distance outside [0,300]      : "
        f"{int(((output['distance_meters'] < 0) | (output['distance_meters'] > 300)).sum())}"
    )

    print(
        f"Distance score outside [0,1]  : "
        f"{int(((output['distance_score'] < 0) | (output['distance_score'] > 1)).sum())}"
    )

    for window_days in RECENT_WINDOWS_DAYS:
        column = f"recency_score_{window_days}d"
        print(
            f"Recency {window_days:>3}d outside [0,1]    : "
            f"{int(((output[column] < 0) | (output[column] > 1)).sum())}"
        )

    print()
    print("6. OUTPUT FILES")
    print("-" * 78)
    print(f"Feature dataset              : {OUTPUT_FILE}")
    print(f"Feature summary              : {SUMMARY_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 78)
    print(
        "No duplicate threshold is selected here."
    )
    print(
        "No final text/distance/recency weights are selected here."
    )
    print(
        "The 7/14/30/60/90-day recency windows are descriptive "
        "candidates only; the final window must be validated."
    )
    print(
        "The next modeling step can test combinations of text "
        "similarity, distance and recency without treating any "
        "single feature as sufficient evidence."
    )

    print()
    print("=" * 78)
    print("DUPLICATE FEATURE ANALYSIS COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
