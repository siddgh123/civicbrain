from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_feature_analysis.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_stability_evaluation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_stability_summary.csv"
)

RANDOM_SEED = 42
N_SPLITS = 5

RECENT_WINDOWS_DAYS = [7, 14, 30, 60, 90]

WEIGHT_CONFIGS = [
    ("equal", 1 / 3, 1 / 3, 1 / 3),
    ("text50_distance30_recency20", 0.50, 0.30, 0.20),
    ("text60_distance25_recency15", 0.60, 0.25, 0.15),
    ("text70_distance20_recency10", 0.70, 0.20, 0.10),
    ("text40_distance40_recency20", 0.40, 0.40, 0.20),
    ("text50_distance20_recency30", 0.50, 0.20, 0.30),
]

THRESHOLDS = np.round(
    np.arange(0.50, 0.951, 0.01),
    2,
)


def load_data() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Feature dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = [
        "pair_id",
        "actual_duplicate",
        "text_similarity",
        "distance_score",
        "time_difference_hours",
    ]

    missing = [column for column in required if column not in df.columns]

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

    for window_days in RECENT_WINDOWS_DAYS:
        column = f"recency_score_{window_days}d"

        if column not in df.columns:
            raise ValueError(
                f"Missing feature column: {column}"
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[
        [
            "actual_duplicate",
            "text_similarity",
            "distance_score",
            "time_difference_hours",
            *[
                f"recency_score_{d}d"
                for d in RECENT_WINDOWS_DAYS
            ],
        ]
    ].isna().any().any():
        raise ValueError(
            "Missing feature values detected."
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


def evaluate(
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    y_pred = (y_score >= threshold).astype(int)

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


def select_calibration_configuration(
    calibration_rows: list[dict],
) -> dict:
    if not calibration_rows:
        raise ValueError(
            "No calibration results available."
        )

    # Select by mean calibration F1, then mean precision,
    # mean recall, then threshold. No held-out evaluation values
    # are used for selection.
    summary = (
        pd.DataFrame(calibration_rows)
        .groupby(
            [
                "window_days",
                "weight_config",
                "threshold",
            ],
            as_index=False,
        )
        .agg(
            mean_calibration_precision=(
                "calibration_precision",
                "mean",
            ),
            mean_calibration_recall=(
                "calibration_recall",
                "mean",
            ),
            mean_calibration_f1=(
                "calibration_f1",
                "mean",
            ),
        )
    )

    summary = summary.sort_values(
        [
            "mean_calibration_f1",
            "mean_calibration_precision",
            "mean_calibration_recall",
            "window_days",
            "threshold",
        ],
        ascending=[
            False,
            False,
            False,
            False,
            True,
        ],
    )

    row = summary.iloc[0].to_dict()
    return row


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 12 — 5-FOLD DUPLICATE STABILITY EVALUATION")
    print("=" * 80)

    df = load_data()

    y = df["actual_duplicate"].astype(int).to_numpy()

    print(f"Pairs loaded                 : {len(df)}")
    print(f"Folds                        : {N_SPLITS}")
    print(
        f"Pairs per fold (approximately): "
        f"{len(df) // N_SPLITS}"
    )

    skf = StratifiedKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    fold_masks = list(
        skf.split(
            np.zeros(len(df)),
            y,
        )
    )

    all_rows = []
    calibration_rows = []

    for fold_number, (train_indices, test_indices) in enumerate(
        fold_masks,
        start=1,
    ):
        train_df = df.iloc[train_indices].copy()
        test_df = df.iloc[test_indices].copy()

        y_train = train_df["actual_duplicate"].astype(int).to_numpy()
        y_test = test_df["actual_duplicate"].astype(int).to_numpy()

        print()
        print(
            f"Fold {fold_number}: "
            f"train={len(train_df)}, "
            f"test={len(test_df)}"
        )

        for window_days in RECENT_WINDOWS_DAYS:
            for (
                weight_name,
                text_weight,
                distance_weight,
                recency_weight,
            ) in WEIGHT_CONFIGS:

                train_score = combined_score(
                    train_df,
                    text_weight,
                    distance_weight,
                    recency_weight,
                    window_days,
                )

                test_score = combined_score(
                    test_df,
                    text_weight,
                    distance_weight,
                    recency_weight,
                    window_days,
                )

                # Calibration-side threshold selection within this fold.
                for threshold in THRESHOLDS:
                    train_metrics = evaluate(
                        y_train,
                        train_score.to_numpy(),
                        float(threshold),
                    )

                    calibration_rows.append(
                        {
                            "fold": fold_number,
                            "window_days": window_days,
                            "weight_config": weight_name,
                            "threshold": float(threshold),
                            "calibration_precision": train_metrics[
                                "precision"
                            ],
                            "calibration_recall": train_metrics[
                                "recall"
                            ],
                            "calibration_f1": train_metrics[
                                "f1"
                            ],
                        }
                    )

    # Select one configuration using only the aggregate calibration
    # performance across the five folds.
    best = select_calibration_configuration(
        calibration_rows
    )

    selected_window = int(best["window_days"])
    selected_weight_config = str(
        best["weight_config"]
    )
    selected_threshold = float(
        best["threshold"]
    )

    weight_lookup = {
        name: (
            text_weight,
            distance_weight,
            recency_weight,
        )
        for (
            name,
            text_weight,
            distance_weight,
            recency_weight,
        ) in WEIGHT_CONFIGS
    }

    (
        selected_text_weight,
        selected_distance_weight,
        selected_recency_weight,
    ) = weight_lookup[selected_weight_config]

    # Evaluate the selected configuration independently on each
    # fold's held-out test partition.
    heldout_rows = []

    for fold_number, (train_indices, test_indices) in enumerate(
        fold_masks,
        start=1,
    ):
        test_df = df.iloc[test_indices].copy()
        y_test = test_df["actual_duplicate"].astype(int).to_numpy()

        test_score = combined_score(
            test_df,
            selected_text_weight,
            selected_distance_weight,
            selected_recency_weight,
            selected_window,
        )

        metrics = evaluate(
            y_test,
            test_score.to_numpy(),
            selected_threshold,
        )

        heldout_rows.append(
            {
                "fold": fold_number,
                "window_days": selected_window,
                "weight_config": selected_weight_config,
                "text_weight": selected_text_weight,
                "distance_weight": selected_distance_weight,
                "recency_weight": selected_recency_weight,
                "threshold": selected_threshold,
                "test_pairs": len(test_df),
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "tn": metrics["tn"],
                "fn": metrics["fn"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
            }
        )

    heldout_df = pd.DataFrame(heldout_rows)

    # Add fold stability statistics.
    stability = {
        "mean_precision": heldout_df["precision"].mean(),
        "std_precision": heldout_df["precision"].std(ddof=1),
        "mean_recall": heldout_df["recall"].mean(),
        "std_recall": heldout_df["recall"].std(ddof=1),
        "mean_f1": heldout_df["f1"].mean(),
        "std_f1": heldout_df["f1"].std(ddof=1),
    }

    # Save fold-level held-out results.
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    heldout_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # Fold summary.
    summary_df = pd.DataFrame(
        [
            {
                "metric": "precision",
                "mean": stability["mean_precision"],
                "std": stability["std_precision"],
                "min": heldout_df["precision"].min(),
                "max": heldout_df["precision"].max(),
            },
            {
                "metric": "recall",
                "mean": stability["mean_recall"],
                "std": stability["std_recall"],
                "min": heldout_df["recall"].min(),
                "max": heldout_df["recall"].max(),
            },
            {
                "metric": "f1",
                "mean": stability["mean_f1"],
                "std": stability["std_f1"],
                "min": heldout_df["f1"].min(),
                "max": heldout_df["f1"].max(),
            },
        ]
    )

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    selected_config = {
        "status": "experimental",
        "selection_method": (
            "5-fold calibration mean F1, with ties broken by "
            "mean precision, mean recall, wider window, then "
            "lower threshold."
        ),
        "folds": N_SPLITS,
        "random_seed": RANDOM_SEED,
        "recent_window_days": selected_window,
        "weight_config": selected_weight_config,
        "text_weight": selected_text_weight,
        "distance_weight": selected_distance_weight,
        "recency_weight": selected_recency_weight,
        "threshold": selected_threshold,
        "heldout_mean_precision": stability["mean_precision"],
        "heldout_std_precision": stability["std_precision"],
        "heldout_mean_recall": stability["mean_recall"],
        "heldout_std_recall": stability["std_recall"],
        "heldout_mean_f1": stability["mean_f1"],
        "heldout_std_f1": stability["std_f1"],
        "note": (
            "Experimental only. The benchmark is synthetic-by-construction. "
            "This configuration is not official TDMC policy and is not "
            "frozen until final validation/documentation."
        ),
    }

    config_file = (
        PROJECT_ROOT
        / "data"
        / "duplicates"
        / "duplicate_stability_config.json"
    )

    config_file.write_text(
        json.dumps(
            selected_config,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Print complete result.
    # ------------------------------------------------------------

    print()
    print("SELECTED CONFIGURATION FROM 5-FOLD CALIBRATION")
    print("-" * 80)
    print(f"Recent window               : {selected_window} days")
    print(
        f"Weight configuration        : "
        f"{selected_weight_config}"
    )
    print(
        f"Text weight                 : "
        f"{selected_text_weight:.2f}"
    )
    print(
        f"Distance weight             : "
        f"{selected_distance_weight:.2f}"
    )
    print(
        f"Recency weight              : "
        f"{selected_recency_weight:.2f}"
    )
    print(
        f"Threshold                   : "
        f"{selected_threshold:.2f}"
    )

    print()
    print("HELD-OUT FOLD RESULTS")
    print("-" * 80)
    print(
        heldout_df[
            [
                "fold",
                "test_pairs",
                "tp",
                "fp",
                "tn",
                "fn",
                "precision",
                "recall",
                "f1",
            ]
        ].to_string(index=False)
    )

    print()
    print("5-FOLD STABILITY")
    print("-" * 80)
    print(
        f"Precision mean ± std        : "
        f"{stability['mean_precision']:.4f} ± "
        f"{stability['std_precision']:.4f}"
    )
    print(
        f"Recall mean ± std           : "
        f"{stability['mean_recall']:.4f} ± "
        f"{stability['std_recall']:.4f}"
    )
    print(
        f"F1 mean ± std               : "
        f"{stability['mean_f1']:.4f} ± "
        f"{stability['std_f1']:.4f}"
    )

    print()
    print("OUTPUT FILES")
    print("-" * 80)
    print(f"Fold results                : {OUTPUT_FILE}")
    print(f"Stability summary           : {SUMMARY_FILE}")
    print(f"Selected config             : {config_file}")

    print()
    print("IMPORTANT")
    print("-" * 80)
    print(
        "This is a stability experiment only."
    )
    print(
        "The benchmark labels remain synthetic-by-construction."
    )
    print(
        "The selected configuration must not be described as official "
        "TDMC duplicate-detection policy."
    )
    print(
        "Final freezing requires the complete duplicate validation "
        "and documentation sequence."
    )

    print()
    print("=" * 80)
    print("5-FOLD DUPLICATE STABILITY EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
