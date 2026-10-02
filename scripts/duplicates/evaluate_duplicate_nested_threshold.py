from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FEATURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_feature_analysis.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_nested_threshold_evaluation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_nested_threshold_summary.csv"
)

CONFIG_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_nested_threshold_config.json"
)

RANDOM_SEED = 42
OUTER_FOLDS = 5
INNER_FOLDS = 4

# Pre-declared candidate band from the previous threshold sensitivity test.
THRESHOLDS = np.round(
    np.arange(0.55, 0.651, 0.01),
    2,
)

# Fixed configuration from the previous validated experiments.
TIME_WINDOW_DAYS = 7
TEXT_WEIGHT = 0.70
DISTANCE_WEIGHT = 0.20
RECENCY_WEIGHT = 0.10


def load_data() -> pd.DataFrame:
    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            f"Feature file not found:\n{FEATURE_FILE}"
        )

    df = pd.read_csv(FEATURE_FILE)

    required = [
        "pair_id",
        "actual_duplicate",
        "text_similarity",
        "distance_score",
        "recency_score_7d",
    ]

    missing = [
        column for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {column}" for column in missing)
        )

    for column in required[1:]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[required[1:]].isna().any().any():
        raise ValueError(
            "Missing/invalid values found in required columns."
        )

    labels = set(
        df["actual_duplicate"].astype(int).unique()
    )

    if labels != {0, 1}:
        raise ValueError(
            f"Expected labels {{0,1}}, found {labels}"
        )

    if df["pair_id"].duplicated().any():
        raise ValueError(
            "Duplicate pair_id values detected."
        )

    return df.reset_index(drop=True)


def combined_score(df: pd.DataFrame) -> np.ndarray:
    score = (
        TEXT_WEIGHT * df["text_similarity"]
        + DISTANCE_WEIGHT * df["distance_score"]
        + RECENCY_WEIGHT * df["recency_score_7d"]
    )

    return score.clip(0.0, 1.0).to_numpy()


def evaluate(
    y_true: np.ndarray,
    scores: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    predictions = (
        scores >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    ).ravel()

    return {
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
    }


def choose_threshold_inner_cv(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
) -> tuple[float, pd.DataFrame]:
    inner_splitter = StratifiedKFold(
        n_splits=INNER_FOLDS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    rows = []

    for threshold in THRESHOLDS:
        fold_metrics = []

        for inner_fold, (
            inner_train_idx,
            inner_valid_idx,
        ) in enumerate(
            inner_splitter.split(
                np.zeros(len(x_train)),
                y_train,
            ),
            start=1,
        ):
            inner_valid_df = x_train.iloc[
                inner_valid_idx
            ]

            y_valid = y_train[
                inner_valid_idx
            ]

            valid_scores = combined_score(
                inner_valid_df
            )

            result = evaluate(
                y_valid,
                valid_scores,
                float(threshold),
            )

            fold_metrics.append(result)

            rows.append(
                {
                    "threshold": float(threshold),
                    "inner_fold": inner_fold,
                    "precision": result["precision"],
                    "recall": result["recall"],
                    "f1": result["f1"],
                    "tp": result["tp"],
                    "fp": result["fp"],
                    "tn": result["tn"],
                    "fn": result["fn"],
                }
            )

    inner_df = pd.DataFrame(rows)

    aggregate = (
        inner_df
        .groupby("threshold", as_index=False)
        .agg(
            mean_precision=("precision", "mean"),
            mean_recall=("recall", "mean"),
            mean_f1=("f1", "mean"),
        )
    )

    # Predeclared selection rule:
    # 1) mean inner F1
    # 2) mean inner precision
    # 3) mean inner recall
    # 4) threshold closest to the previously observed 0.59
    # This keeps selection entirely inside the outer training data.
    aggregate["distance_from_059"] = (
        aggregate["threshold"] - 0.59
    ).abs()

    selected = aggregate.sort_values(
        [
            "mean_f1",
            "mean_precision",
            "mean_recall",
            "distance_from_059",
        ],
        ascending=[
            False,
            False,
            False,
            True,
        ],
    ).iloc[0]

    return float(selected["threshold"]), aggregate


def main() -> None:
    print("=" * 80)
    print(
        "CIVICBRAIN STEP 12 — NESTED THRESHOLD VALIDATION"
    )
    print("=" * 80)

    print()
    print("FIXED CONFIGURATION")
    print("-" * 80)
    print(f"Time window                 : {TIME_WINDOW_DAYS} days")
    print(f"Text weight                 : {TEXT_WEIGHT:.2f}")
    print(f"Distance weight             : {DISTANCE_WEIGHT:.2f}")
    print(f"Recency weight              : {RECENCY_WEIGHT:.2f}")
    print(
        f"Outer folds / inner folds   : "
        f"{OUTER_FOLDS} / {INNER_FOLDS}"
    )
    print(
        "Threshold band              : "
        "0.55-0.65"
    )
    print()
    print(
        "Purpose: remove threshold-selection leakage by choosing "
        "the threshold only inside each outer training partition, "
        "then evaluating that threshold once on the untouched "
        "outer test partition."
    )

    df = load_data()
    y = df["actual_duplicate"].astype(int).to_numpy()

    scores = combined_score(df)

    outer_splitter = StratifiedKFold(
        n_splits=OUTER_FOLDS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    outer_rows = []
    selected_thresholds = []

    for outer_fold, (
        outer_train_idx,
        outer_test_idx,
    ) in enumerate(
        outer_splitter.split(
            np.zeros(len(df)),
            y,
        ),
        start=1,
    ):
        outer_train_df = df.iloc[
            outer_train_idx
        ].reset_index(drop=True)

        outer_test_df = df.iloc[
            outer_test_idx
        ].reset_index(drop=True)

        y_outer_train = (
            outer_train_df["actual_duplicate"]
            .astype(int)
            .to_numpy()
        )

        y_outer_test = (
            outer_test_df["actual_duplicate"]
            .astype(int)
            .to_numpy()
        )

        selected_threshold, inner_summary = (
            choose_threshold_inner_cv(
                outer_train_df,
                y_outer_train,
            )
        )

        selected_thresholds.append(
            selected_threshold
        )

        outer_test_scores = combined_score(
            outer_test_df
        )

        test_result = evaluate(
            y_outer_test,
            outer_test_scores,
            selected_threshold,
        )

        selected_inner_row = inner_summary[
            np.isclose(
                inner_summary["threshold"],
                selected_threshold,
            )
        ].iloc[0]

        row = {
            "outer_fold": outer_fold,
            "outer_train_pairs": len(
                outer_train_df
            ),
            "outer_test_pairs": len(
                outer_test_df
            ),
            "selected_threshold": selected_threshold,
            "inner_mean_f1": float(
                selected_inner_row[
                    "mean_f1"
                ]
            ),
            "inner_mean_precision": float(
                selected_inner_row[
                    "mean_precision"
                ]
            ),
            "inner_mean_recall": float(
                selected_inner_row[
                    "mean_recall"
                ]
            ),
            "tp": test_result["tp"],
            "fp": test_result["fp"],
            "tn": test_result["tn"],
            "fn": test_result["fn"],
            "test_precision": test_result[
                "precision"
            ],
            "test_recall": test_result[
                "recall"
            ],
            "test_f1": test_result[
                "f1"
            ],
        }

        outer_rows.append(row)

        print()
        print(
            f"Outer Fold {outer_fold}: "
            f"selected threshold={selected_threshold:.2f}"
        )
        print(
            f"  Inner CV  F1={row['inner_mean_f1']:.4f}, "
            f"Precision={row['inner_mean_precision']:.4f}, "
            f"Recall={row['inner_mean_recall']:.4f}"
        )
        print(
            f"  Test CV   F1={row['test_f1']:.4f}, "
            f"Precision={row['test_precision']:.4f}, "
            f"Recall={row['test_recall']:.4f}, "
            f"FP={row['fp']}, FN={row['fn']}"
        )

    outer_df = pd.DataFrame(outer_rows)

    # Aggregate outer-test performance.
    mean_precision = outer_df[
        "test_precision"
    ].mean()

    std_precision = outer_df[
        "test_precision"
    ].std(ddof=1)

    mean_recall = outer_df[
        "test_recall"
    ].mean()

    std_recall = outer_df[
        "test_recall"
    ].std(ddof=1)

    mean_f1 = outer_df[
        "test_f1"
    ].mean()

    std_f1 = outer_df[
        "test_f1"
    ].std(ddof=1)

    threshold_counts = (
        pd.Series(selected_thresholds)
        .value_counts()
        .sort_index()
    )

    modal_threshold = float(
        threshold_counts.idxmax()
    )

    threshold_stability = "; ".join(
        [
            f"{float(threshold):.2f}={int(count)}"
            for threshold, count
            in threshold_counts.items()
        ]
    )

    summary_rows = [
        {
            "metric": "mean_precision",
            "value": mean_precision,
        },
        {
            "metric": "std_precision",
            "value": std_precision,
        },
        {
            "metric": "mean_recall",
            "value": mean_recall,
        },
        {
            "metric": "std_recall",
            "value": std_recall,
        },
        {
            "metric": "mean_f1",
            "value": mean_f1,
        },
        {
            "metric": "std_f1",
            "value": std_f1,
        },
        {
            "metric": "total_tp",
            "value": outer_df["tp"].sum(),
        },
        {
            "metric": "total_fp",
            "value": outer_df["fp"].sum(),
        },
        {
            "metric": "total_tn",
            "value": outer_df["tn"].sum(),
        },
        {
            "metric": "total_fn",
            "value": outer_df["fn"].sum(),
        },
        {
            "metric": "mean_selected_threshold",
            "value": outer_df[
                "selected_threshold"
            ].mean(),
        },
        {
            "metric": "std_selected_threshold",
            "value": outer_df[
                "selected_threshold"
            ].std(ddof=1),
        },
    ]

    summary_df = pd.DataFrame(summary_rows)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    outer_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    config_output = {
        "status": "experimental_nested_validation",
        "method": (
            "5-fold outer CV with 4-fold inner CV. Threshold is "
            "selected only from inner validation data inside each "
            "outer training partition, then evaluated on the untouched "
            "outer test partition."
        ),
        "outer_folds": OUTER_FOLDS,
        "inner_folds": INNER_FOLDS,
        "random_seed": RANDOM_SEED,
        "time_window_days": TIME_WINDOW_DAYS,
        "text_weight": TEXT_WEIGHT,
        "distance_weight": DISTANCE_WEIGHT,
        "recency_weight": RECENCY_WEIGHT,
        "threshold_band": [
            float(x) for x in THRESHOLDS
        ],
        "outer_selected_thresholds": [
            float(x) for x in selected_thresholds
        ],
        "threshold_selection_frequency": threshold_stability,
        "modal_threshold": modal_threshold,
        "mean_precision": float(mean_precision),
        "std_precision": float(std_precision),
        "mean_recall": float(mean_recall),
        "std_recall": float(std_recall),
        "mean_f1": float(mean_f1),
        "std_f1": float(std_f1),
        "note": (
            "Experimental prototype evaluation. Benchmark labels are "
            "synthetic-by-construction. Results do not establish an "
            "official TDMC complaint-processing policy. Final freezing "
            "requires the remaining Step 12 validation and documentation."
        ),
    }

    CONFIG_OUTPUT_FILE.write_text(
        json.dumps(
            config_output,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("NESTED CV SUMMARY")
    print("=" * 80)

    print(
        outer_df[
            [
                "outer_fold",
                "selected_threshold",
                "tp",
                "fp",
                "tn",
                "fn",
                "test_precision",
                "test_recall",
                "test_f1",
            ]
        ].to_string(index=False)
    )

    print()
    print(
        f"Mean Precision              : "
        f"{mean_precision:.4f} ± {std_precision:.4f}"
    )
    print(
        f"Mean Recall                 : "
        f"{mean_recall:.4f} ± {std_recall:.4f}"
    )
    print(
        f"Mean F1                     : "
        f"{mean_f1:.4f} ± {std_f1:.4f}"
    )
    print(
        f"Mean selected threshold     : "
        f"{outer_df['selected_threshold'].mean():.4f}"
    )
    print(
        f"Threshold std               : "
        f"{outer_df['selected_threshold'].std(ddof=1):.4f}"
    )
    print(
        f"Threshold selection counts  : "
        f"{threshold_stability}"
    )
    print(
        f"Modal threshold             : "
        f"{modal_threshold:.2f}"
    )

    print()
    print("OUTPUT FILES")
    print("-" * 80)
    print(f"Outer-fold results           : {OUTPUT_FILE}")
    print(f"Nested CV summary            : {SUMMARY_FILE}")
    print(f"Nested CV config              : {CONFIG_OUTPUT_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 80)
    print(
        "This run is the leakage-controlled threshold validation."
    )
    print(
        "It is still based on synthetic-by-construction benchmark labels."
    )
    print(
        "Do not call the resulting threshold an official TDMC policy."
    )
    print(
        "Do not freeze Step 12 until the remaining validation/documentation "
        "checks are complete."
    )

    print()
    print("=" * 80)
    print("NESTED THRESHOLD VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
