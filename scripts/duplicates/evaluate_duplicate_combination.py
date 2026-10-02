from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score


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
    / "duplicate_combination_evaluation.csv"
)

CONFIG_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_selected_config.json"
)

RANDOM_SEED = 42
TEST_SIZE = 0.40

RECENT_WINDOWS_DAYS = [7, 14, 30, 60, 90]

# Candidate transparent weighted combinations.
# These are EXPERIMENTAL configurations only.
WEIGHT_CONFIGS = [
    ("equal", 1 / 3, 1 / 3, 1 / 3),
    ("text50_distance30_recency20", 0.50, 0.30, 0.20),
    ("text60_distance25_recency15", 0.60, 0.25, 0.15),
    ("text70_distance20_recency10", 0.70, 0.20, 0.10),
    ("text40_distance40_recency20", 0.40, 0.40, 0.20),
    ("text50_distance20_recency30", 0.50, 0.20, 0.30),
]

# Do not infer a final threshold from this list. It is an experiment grid.
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
        "distance_meters",
        "time_difference_hours",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {c}" for c in missing)
        )

    numeric = [
        "actual_duplicate",
        "text_similarity",
        "distance_score",
        "distance_meters",
        "time_difference_hours",
    ]

    for col in numeric:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    required_recency = [
        f"recency_score_{days}d"
        for days in RECENT_WINDOWS_DAYS
    ]

    for col in required_recency:
        if col not in df.columns:
            raise ValueError(
                f"Missing recency feature column: {col}"
            )

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    if df[numeric + required_recency].isna().any().any():
        raise ValueError(
            "Missing values found in required feature columns."
        )

    if not set(df["actual_duplicate"].unique()).issubset({0, 1}):
        raise ValueError(
            "actual_duplicate must contain only 0 and 1."
        )

    return df.reset_index(drop=True)


def evaluate_predictions(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict[str, float | int]:
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


def make_score(
    df: pd.DataFrame,
    text_weight: float,
    distance_weight: float,
    recency_weight: float,
    window_days: int,
) -> pd.Series:
    recency_column = f"recency_score_{window_days}d"

    return (
        text_weight * df["text_similarity"]
        + distance_weight * df["distance_score"]
        + recency_weight * df[recency_column]
    ).clip(0.0, 1.0)


def eligible_mask(
    df: pd.DataFrame,
    window_days: int,
) -> pd.Series:
    return (
        df["time_difference_hours"]
        <= window_days * 24
    )


def choose_best_calibration_result(
    results: list[dict],
) -> dict:
    """
    Select the best experimental configuration on calibration data.

    Tie-breaking:
      1. F1
      2. Precision
      3. Recall
      4. More recent candidate window (prefer wider window only after
         performance tie)
      5. Higher threshold
    """
    if not results:
        raise ValueError("No calibration results available.")

    ordered = sorted(
        results,
        key=lambda row: (
            row["calibration_f1"],
            row["calibration_precision"],
            row["calibration_recall"],
            row["window_days"],
            row["threshold"],
        ),
        reverse=True,
    )

    return ordered[0]


def main() -> None:
    print("=" * 78)
    print("CIVICBRAIN STEP 12 — DUPLICATE COMBINATION + THRESHOLD EXPERIMENT")
    print("=" * 78)

    df = load_data()

    print(f"Pairs loaded                 : {len(df)}")

    # ------------------------------------------------------------
    # Holdout split
    # ------------------------------------------------------------
    train_df, test_df = train_test_split(
        df,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=df["actual_duplicate"],
    )

    print(f"Calibration rows             : {len(train_df)}")
    print(f"Evaluation rows              : {len(test_df)}")
    print(
        "Calibration duplicate count  : "
        f"{int(train_df['actual_duplicate'].sum())}"
    )
    print(
        "Calibration non-duplicate    : "
        f"{int((train_df['actual_duplicate'] == 0).sum())}"
    )
    print(
        "Evaluation duplicate count   : "
        f"{int(test_df['actual_duplicate'].sum())}"
    )
    print(
        "Evaluation non-duplicate     : "
        f"{int((test_df['actual_duplicate'] == 0).sum())}"
    )

    all_results = []
    calibration_results = []

    for window_days in RECENT_WINDOWS_DAYS:
        for (
            weight_name,
            text_weight,
            distance_weight,
            recency_weight,
        ) in WEIGHT_CONFIGS:

            calibration_score = make_score(
                train_df,
                text_weight,
                distance_weight,
                recency_weight,
                window_days,
            )

            evaluation_score = make_score(
                test_df,
                text_weight,
                distance_weight,
                recency_weight,
                window_days,
            )

            calibration_eligible = eligible_mask(
                train_df,
                window_days,
            )

            evaluation_eligible = eligible_mask(
                test_df,
                window_days,
            )

            for threshold in THRESHOLDS:
                calibration_pred = (
                    calibration_eligible
                    & (calibration_score >= threshold)
                ).astype(int).to_numpy()

                evaluation_pred = (
                    evaluation_eligible
                    & (evaluation_score >= threshold)
                ).astype(int).to_numpy()

                cal_metrics = evaluate_predictions(
                    train_df["actual_duplicate"],
                    calibration_pred,
                )

                test_metrics = evaluate_predictions(
                    test_df["actual_duplicate"],
                    evaluation_pred,
                )

                row = {
                    "window_days": window_days,
                    "weight_config": weight_name,
                    "text_weight": text_weight,
                    "distance_weight": distance_weight,
                    "recency_weight": recency_weight,
                    "threshold": float(threshold),
                    "calibration_eligible_pairs": int(
                        calibration_eligible.sum()
                    ),
                    "evaluation_eligible_pairs": int(
                        evaluation_eligible.sum()
                    ),
                    "calibration_tp": cal_metrics["tp"],
                    "calibration_fp": cal_metrics["fp"],
                    "calibration_tn": cal_metrics["tn"],
                    "calibration_fn": cal_metrics["fn"],
                    "calibration_precision": cal_metrics["precision"],
                    "calibration_recall": cal_metrics["recall"],
                    "calibration_f1": cal_metrics["f1"],
                    "evaluation_tp": test_metrics["tp"],
                    "evaluation_fp": test_metrics["fp"],
                    "evaluation_tn": test_metrics["tn"],
                    "evaluation_fn": test_metrics["fn"],
                    "evaluation_precision": test_metrics["precision"],
                    "evaluation_recall": test_metrics["recall"],
                    "evaluation_f1": test_metrics["f1"],
                }

                all_results.append(row)

                calibration_results.append(
                    {
                        "window_days": window_days,
                        "weight_config": weight_name,
                        "text_weight": text_weight,
                        "distance_weight": distance_weight,
                        "recency_weight": recency_weight,
                        "threshold": float(threshold),
                        "calibration_precision": cal_metrics["precision"],
                        "calibration_recall": cal_metrics["recall"],
                        "calibration_f1": cal_metrics["f1"],
                    }
                )

    results_df = pd.DataFrame(all_results)

    # Highest calibration F1 determines the experimental configuration.
    best = choose_best_calibration_result(
        calibration_results
    )

    selected_mask = (
        (results_df["window_days"] == best["window_days"])
        & (
            results_df["weight_config"]
            == best["weight_config"]
        )
        & (
            results_df["threshold"]
            == best["threshold"]
        )
    )

    selected_result = results_df.loc[
        selected_mask
    ].iloc[0].to_dict()

    # ------------------------------------------------------------
    # Save all experiment results.
    # ------------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    selected_config = {
        "version": "1.0-experimental",
        "status": "SELECTED_FOR_HELD_OUT_EVALUATION",
        "selection_method": (
            "Highest calibration F1; ties broken by calibration "
            "precision, recall, wider recent window, then threshold."
        ),
        "random_seed": RANDOM_SEED,
        "test_size": TEST_SIZE,
        "recent_window_days": int(best["window_days"]),
        "weight_config": best["weight_config"],
        "text_weight": float(best["text_weight"]),
        "distance_weight": float(best["distance_weight"]),
        "recency_weight": float(best["recency_weight"]),
        "threshold": float(best["threshold"]),
        "calibration_precision": float(
            selected_result["calibration_precision"]
        ),
        "calibration_recall": float(
            selected_result["calibration_recall"]
        ),
        "calibration_f1": float(
            selected_result["calibration_f1"]
        ),
        "held_out_evaluation_precision": float(
            selected_result["evaluation_precision"]
        ),
        "held_out_evaluation_recall": float(
            selected_result["evaluation_recall"]
        ),
        "held_out_evaluation_f1": float(
            selected_result["evaluation_f1"]
        ),
        "held_out_confusion_matrix": {
            "tp": int(selected_result["evaluation_tp"]),
            "fp": int(selected_result["evaluation_fp"]),
            "tn": int(selected_result["evaluation_tn"]),
            "fn": int(selected_result["evaluation_fn"]),
        },
        "note": (
            "This configuration is experimentally selected from the "
            "controlled synthetic benchmark. It is NOT an official TDMC "
            "duplicate rule and is not frozen until documented final "
            "validation is complete."
        ),
    }

    CONFIG_FILE.write_text(
        json.dumps(
            selected_config,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------------
    # Print summary.
    # ------------------------------------------------------------

    print()
    print("EXPERIMENT GRID")
    print("-" * 78)
    print(
        f"Recent windows tested       : "
        f"{', '.join(map(str, RECENT_WINDOWS_DAYS))} days"
    )
    print(
        f"Weight configurations tested: "
        f"{len(WEIGHT_CONFIGS)}"
    )
    print(
        f"Thresholds tested           : "
        f"{len(THRESHOLDS)}"
    )
    print(
        f"Total experiments           : "
        f"{len(results_df)}"
    )

    print()
    print("SELECTED ON CALIBRATION SET")
    print("-" * 78)
    print(
        f"Recent window               : "
        f"{best['window_days']} days"
    )
    print(
        f"Weight configuration        : "
        f"{best['weight_config']}"
    )
    print(
        f"Text weight                : "
        f"{best['text_weight']:.2f}"
    )
    print(
        f"Distance weight            : "
        f"{best['distance_weight']:.2f}"
    )
    print(
        f"Recency weight             : "
        f"{best['recency_weight']:.2f}"
    )
    print(
        f"Threshold                  : "
        f"{best['threshold']:.2f}"
    )
    print(
        f"Calibration precision      : "
        f"{selected_result['calibration_precision']:.4f}"
    )
    print(
        f"Calibration recall         : "
        f"{selected_result['calibration_recall']:.4f}"
    )
    print(
        f"Calibration F1             : "
        f"{selected_result['calibration_f1']:.4f}"
    )

    print()
    print("HELD-OUT EVALUATION")
    print("-" * 78)
    print(
        f"Precision                  : "
        f"{selected_result['evaluation_precision']:.4f}"
    )
    print(
        f"Recall                     : "
        f"{selected_result['evaluation_recall']:.4f}"
    )
    print(
        f"F1                         : "
        f"{selected_result['evaluation_f1']:.4f}"
    )
    print(
        "Confusion matrix           : "
        f"TP={selected_result['evaluation_tp']}, "
        f"FP={selected_result['evaluation_fp']}, "
        f"TN={selected_result['evaluation_tn']}, "
        f"FN={selected_result['evaluation_fn']}"
    )

    print()
    print("OUTPUT")
    print("-" * 78)
    print(f"Experiment results         : {OUTPUT_FILE}")
    print(f"Selected config            : {CONFIG_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 78)
    print(
        "This is an experimental selection step, not a final freeze."
    )
    print(
        "The score combines text similarity, distance and recency."
    )
    print(
        "No single feature is used as the duplicate decision."
    )
    print(
        "The benchmark labels are synthetic-by-construction and "
        "must not be described as official TDMC ground truth."
    )

    print()
    print("=" * 78)
    print("DUPLICATE COMBINATION EXPERIMENT COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
