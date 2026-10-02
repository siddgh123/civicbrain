from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FEATURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_feature_analysis.csv"
)

STABILITY_CONFIG_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_stability_config.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_time_window_evaluation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_time_window_summary.csv"
)

CONFIG_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_time_window_config.json"
)

RANDOM_SEED = 42
N_SPLITS = 5

# These are the time windows already investigated during candidate analysis.
TIME_WINDOWS_DAYS = [7, 14, 30, 60, 90]

# Threshold search used only on each training fold.
THRESHOLDS = np.round(
    np.arange(0.50, 0.951, 0.01),
    2,
)


def load_config() -> dict:
    if not STABILITY_CONFIG_FILE.exists():
        raise FileNotFoundError(
            "Stability configuration not found:\n"
            f"{STABILITY_CONFIG_FILE}"
        )

    with STABILITY_CONFIG_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    required = [
        "text_weight",
        "distance_weight",
        "recency_weight",
    ]

    missing = [
        key for key in required
        if key not in config
    ]

    if missing:
        raise ValueError(
            "Missing weights in stability config: "
            + ", ".join(missing)
        )

    return config


def load_data() -> pd.DataFrame:
    if not FEATURE_FILE.exists():
        raise FileNotFoundError(
            "Feature analysis file not found:\n"
            f"{FEATURE_FILE}"
        )

    df = pd.read_csv(FEATURE_FILE)

    required = [
        "pair_id",
        "actual_duplicate",
        "text_similarity",
        "distance_score",
        "time_difference_hours",
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

    for days in TIME_WINDOWS_DAYS:
        column = f"recency_score_{days}d"

        if column not in df.columns:
            raise ValueError(
                f"Missing required recency feature: {column}"
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    feature_columns = [
        "actual_duplicate",
        "text_similarity",
        "distance_score",
        "time_difference_hours",
        *[
            f"recency_score_{days}d"
            for days in TIME_WINDOWS_DAYS
        ],
    ]

    if df[feature_columns].isna().any().any():
        raise ValueError(
            "Missing/invalid values detected in required features."
        )

    labels = set(
        df["actual_duplicate"].astype(int).unique()
    )

    if labels != {0, 1}:
        raise ValueError(
            f"Expected labels {{0,1}}, found {labels}"
        )

    return df.reset_index(drop=True)


def combined_score(
    df: pd.DataFrame,
    text_weight: float,
    distance_weight: float,
    recency_weight: float,
    window_days: int,
) -> pd.Series:
    return (
        text_weight * df["text_similarity"]
        + distance_weight * df["distance_score"]
        + recency_weight * df[
            f"recency_score_{window_days}d"
        ]
    ).clip(0.0, 1.0)


def metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    y_pred = (
        y_score >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
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
                y_pred,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                y_pred,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                y_pred,
                zero_division=0,
            )
        ),
    }


def select_threshold_from_training(
    y_train: np.ndarray,
    train_score: np.ndarray,
) -> tuple[float, dict]:
    candidates = []

    for threshold in THRESHOLDS:
        result = metrics(
            y_train,
            train_score,
            float(threshold),
        )

        candidates.append(
            {
                "threshold": float(threshold),
                **result,
            }
        )

    # Training-fold-only threshold selection.
    # Primary criterion: F1.
    # Tie-breakers: precision, recall, then lower threshold.
    candidates.sort(
        key=lambda row: (
            row["f1"],
            row["precision"],
            row["recall"],
            -row["threshold"],
        ),
        reverse=True,
    )

    selected = candidates[0]
    return selected["threshold"], selected


def main() -> None:
    print("=" * 80)
    print(
        "CIVICBRAIN STEP 12 — FINAL TIME-WINDOW VALIDATION"
    )
    print("=" * 80)

    config = load_config()
    df = load_data()

    text_weight = float(config["text_weight"])
    distance_weight = float(config["distance_weight"])
    recency_weight = float(config["recency_weight"])

    print()
    print("Weights taken from the previous stability experiment:")
    print(f"Text weight                 : {text_weight:.2f}")
    print(f"Distance weight             : {distance_weight:.2f}")
    print(f"Recency weight              : {recency_weight:.2f}")
    print()
    print("Time windows under test:")
    print("7, 14, 30, 60, 90 days")
    print()
    print("Threshold selection:")
    print(
        "Training fold only; held-out fold is never used "
        "to select its threshold."
    )

    y = df["actual_duplicate"].astype(int).to_numpy()

    splitter = StratifiedKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    all_rows = []

    for window_days in TIME_WINDOWS_DAYS:
        print()
        print("-" * 80)
        print(
            f"TESTING {window_days}-DAY WINDOW"
        )
        print("-" * 80)

        for fold_number, (train_idx, test_idx) in enumerate(
            splitter.split(
                np.zeros(len(df)),
                y,
            ),
            start=1,
        ):
            train_df = df.iloc[train_idx]
            test_df = df.iloc[test_idx]

            y_train = train_df[
                "actual_duplicate"
            ].astype(int).to_numpy()

            y_test = test_df[
                "actual_duplicate"
            ].astype(int).to_numpy()

            train_score = combined_score(
                train_df,
                text_weight,
                distance_weight,
                recency_weight,
                window_days,
            ).to_numpy()

            test_score = combined_score(
                test_df,
                text_weight,
                distance_weight,
                recency_weight,
                window_days,
            ).to_numpy()

            selected_threshold, train_metrics = (
                select_threshold_from_training(
                    y_train,
                    train_score,
                )
            )

            test_metrics = metrics(
                y_test,
                test_score,
                selected_threshold,
            )

            row = {
                "window_days": window_days,
                "fold": fold_number,
                "train_pairs": len(train_df),
                "test_pairs": len(test_df),
                "text_weight": text_weight,
                "distance_weight": distance_weight,
                "recency_weight": recency_weight,
                "selected_threshold": selected_threshold,
                "train_precision": train_metrics["precision"],
                "train_recall": train_metrics["recall"],
                "train_f1": train_metrics["f1"],
                "tp": test_metrics["tp"],
                "fp": test_metrics["fp"],
                "tn": test_metrics["tn"],
                "fn": test_metrics["fn"],
                "test_precision": test_metrics["precision"],
                "test_recall": test_metrics["recall"],
                "test_f1": test_metrics["f1"],
            }

            all_rows.append(row)

            print(
                f"Fold {fold_number}: "
                f"threshold={selected_threshold:.2f}, "
                f"Precision={test_metrics['precision']:.4f}, "
                f"Recall={test_metrics['recall']:.4f}, "
                f"F1={test_metrics['f1']:.4f}"
            )

    results_df = pd.DataFrame(all_rows)

    # Aggregate held-out results by time window.
    summary_df = (
        results_df
        .groupby("window_days", as_index=False)
        .agg(
            mean_precision=(
                "test_precision",
                "mean",
            ),
            std_precision=(
                "test_precision",
                "std",
            ),
            min_precision=(
                "test_precision",
                "min",
            ),
            max_precision=(
                "test_precision",
                "max",
            ),
            mean_recall=(
                "test_recall",
                "mean",
            ),
            std_recall=(
                "test_recall",
                "std",
            ),
            min_recall=(
                "test_recall",
                "min",
            ),
            max_recall=(
                "test_recall",
                "max",
            ),
            mean_f1=(
                "test_f1",
                "mean",
            ),
            std_f1=(
                "test_f1",
                "std",
            ),
            min_f1=(
                "test_f1",
                "min",
            ),
            max_f1=(
                "test_f1",
                "max",
            ),
            mean_selected_threshold=(
                "selected_threshold",
                "mean",
            ),
            std_selected_threshold=(
                "selected_threshold",
                "std",
            ),
            total_tp=(
                "tp",
                "sum",
            ),
            total_fp=(
                "fp",
                "sum",
            ),
            total_tn=(
                "tn",
                "sum",
            ),
            total_fn=(
                "fn",
                "sum",
            ),
        )
    )

    # Rank only for analytical convenience; do not interpret this
    # as a political/electoral ranking. This is a technical metric
    # comparison.
    summary_df = summary_df.sort_values(
        [
            "mean_f1",
            "mean_precision",
            "mean_recall",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)

    selected_window = int(
        summary_df.iloc[0]["window_days"]
    )

    selected_window_row = summary_df.iloc[0]

    # Ensure output directory exists.
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_df.to_csv(
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
        "status": "experimental",
        "selection_method": (
            "Compare 5-fold held-out mean F1 across time windows "
            "using fixed weights from the previous stability experiment. "
            "Within each fold, threshold is selected from training data only."
        ),
        "folds": N_SPLITS,
        "random_seed": RANDOM_SEED,
        "tested_windows_days": TIME_WINDOWS_DAYS,
        "text_weight": text_weight,
        "distance_weight": distance_weight,
        "recency_weight": recency_weight,
        "selected_window_days_by_mean_heldout_f1": selected_window,
        "selected_window_mean_precision": float(
            selected_window_row["mean_precision"]
        ),
        "selected_window_std_precision": float(
            selected_window_row["std_precision"]
        ),
        "selected_window_mean_recall": float(
            selected_window_row["mean_recall"]
        ),
        "selected_window_std_recall": float(
            selected_window_row["std_recall"]
        ),
        "selected_window_mean_f1": float(
            selected_window_row["mean_f1"]
        ),
        "selected_window_std_f1": float(
            selected_window_row["std_f1"]
        ),
        "selected_window_mean_threshold": float(
            selected_window_row["mean_selected_threshold"]
        ),
        "important_note": (
            "This does not establish an official TDMC time window. "
            "Benchmark labels are synthetic-by-construction and the "
            "time strata were intentionally balanced. The selected "
            "window is an experimental result only and must not be "
            "frozen until final validation/documentation."
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
    print("TIME-WINDOW SUMMARY")
    print("=" * 80)

    print(
        summary_df[
            [
                "window_days",
                "mean_precision",
                "std_precision",
                "mean_recall",
                "std_recall",
                "mean_f1",
                "std_f1",
                "mean_selected_threshold",
                "total_fp",
                "total_fn",
            ]
        ].to_string(index=False)
    )

    print()
    print("=" * 80)
    print("EXPERIMENTAL WINDOW SELECTED BY HELD-OUT MEAN F1")
    print("=" * 80)
    print(
        f"Window                      : {selected_window} days"
    )
    print(
        f"Mean Precision              : "
        f"{selected_window_row['mean_precision']:.4f}"
    )
    print(
        f"Mean Recall                 : "
        f"{selected_window_row['mean_recall']:.4f}"
    )
    print(
        f"Mean F1                     : "
        f"{selected_window_row['mean_f1']:.4f}"
    )
    print(
        f"F1 Std                      : "
        f"{selected_window_row['std_f1']:.4f}"
    )
    print(
        f"Mean selected threshold     : "
        f"{selected_window_row['mean_selected_threshold']:.4f}"
    )

    print()
    print("OUTPUT FILES")
    print("-" * 80)
    print(f"Fold results                : {OUTPUT_FILE}")
    print(f"Window summary              : {SUMMARY_FILE}")
    print(f"Selected config             : {CONFIG_OUTPUT_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 80)
    print(
        "The selected window is experimental only."
    )
    print(
        "Benchmark labels are synthetic-by-construction."
    )
    print(
        "Do not describe this as an official TDMC complaint policy."
    )
    print(
        "Final threshold and full duplicate methodology still "
        "require final validation before freezing."
    )

    print()
    print("=" * 80)
    print("FINAL TIME-WINDOW VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
