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

TIME_WINDOW_CONFIG = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_time_window_config.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_threshold_evaluation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_threshold_summary.csv"
)

CONFIG_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_final_threshold_config.json"
)

RANDOM_SEED = 42
N_SPLITS = 5

# Threshold validation band requested after time-window validation.
THRESHOLDS = np.round(
    np.arange(0.55, 0.651, 0.01),
    2,
)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found:\n{path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f" - {c}" for c in missing)
        )

    for c in required[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    if df[required[1:]].isna().any().any():
        raise ValueError("Missing/invalid feature values detected.")

    labels = set(df["actual_duplicate"].astype(int).unique())
    if labels != {0, 1}:
        raise ValueError(f"Expected labels {{0,1}}, found {labels}")

    if df["pair_id"].duplicated().any():
        raise ValueError("Duplicate pair_id values detected.")

    return df.reset_index(drop=True)


def combined_score(
    df: pd.DataFrame,
    text_weight: float,
    distance_weight: float,
    recency_weight: float,
) -> np.ndarray:
    score = (
        text_weight * df["text_similarity"]
        + distance_weight * df["distance_score"]
        + recency_weight * df["recency_score_7d"]
    )
    return score.clip(0.0, 1.0).to_numpy()


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
            precision_score(y_true, y_pred, zero_division=0)
        ),
        "recall": float(
            recall_score(y_true, y_pred, zero_division=0)
        ),
        "f1": float(
            f1_score(y_true, y_pred, zero_division=0)
        ),
    }


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 12 — FINAL THRESHOLD VALIDATION")
    print("=" * 80)

    time_config = load_json(TIME_WINDOW_CONFIG)
    df = load_data()

    selected_window = int(
        time_config["selected_window_days_by_mean_heldout_f1"]
    )

    if selected_window != 7:
        raise ValueError(
            "This validation is intentionally fixed to the experimentally "
            f"selected 7-day window, but config contains {selected_window} days."
        )

    text_weight = float(time_config["text_weight"])
    distance_weight = float(time_config["distance_weight"])
    recency_weight = float(time_config["recency_weight"])

    print()
    print("FIXED CONFIGURATION FOR THRESHOLD TEST")
    print("-" * 80)
    print(f"Time window                 : {selected_window} days")
    print(f"Text weight                 : {text_weight:.2f}")
    print(f"Distance weight             : {distance_weight:.2f}")
    print(f"Recency weight              : {recency_weight:.2f}")
    print()
    print("Thresholds under test:")
    print("0.55 through 0.65 (step 0.01)")
    print()
    print(
        "Thresholds are evaluated on the same 5 held-out folds using "
        "the fixed 7-day / 70-20-10 feature configuration."
    )

    y = df["actual_duplicate"].astype(int).to_numpy()

    splitter = StratifiedKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    folds = list(
        splitter.split(np.zeros(len(df)), y)
    )

    fold_results = []

    for threshold in THRESHOLDS:
        print()
        print("-" * 80)
        print(f"TESTING THRESHOLD {threshold:.2f}")
        print("-" * 80)

        fold_metrics = []

        for fold_number, (train_idx, test_idx) in enumerate(
            folds,
            start=1,
        ):
            # Training data is used only to preserve the fold split.
            # No threshold fitting or selection occurs here because this
            # task is explicitly a direct threshold sensitivity analysis
            # over a pre-declared validation band.
            train_df = df.iloc[train_idx]
            test_df = df.iloc[test_idx]

            y_test = test_df[
                "actual_duplicate"
            ].astype(int).to_numpy()

            test_score = combined_score(
                test_df,
                text_weight,
                distance_weight,
                recency_weight,
            )

            result = evaluate(
                y_test,
                test_score,
                float(threshold),
            )

            row = {
                "threshold": float(threshold),
                "fold": fold_number,
                "test_pairs": len(test_df),
                "tp": result["tp"],
                "fp": result["fp"],
                "tn": result["tn"],
                "fn": result["fn"],
                "precision": result["precision"],
                "recall": result["recall"],
                "f1": result["f1"],
            }

            fold_metrics.append(row)
            fold_results.append(row)

            print(
                f"Fold {fold_number}: "
                f"Precision={result['precision']:.4f}, "
                f"Recall={result['recall']:.4f}, "
                f"F1={result['f1']:.4f}, "
                f"FP={result['fp']}, "
                f"FN={result['fn']}"
            )

    results_df = pd.DataFrame(fold_results)

    summary_df = (
        results_df
        .groupby("threshold", as_index=False)
        .agg(
            mean_precision=("precision", "mean"),
            std_precision=("precision", "std"),
            min_precision=("precision", "min"),
            max_precision=("precision", "max"),
            mean_recall=("recall", "mean"),
            std_recall=("recall", "std"),
            min_recall=("recall", "min"),
            max_recall=("recall", "max"),
            mean_f1=("f1", "mean"),
            std_f1=("f1", "std"),
            min_f1=("f1", "min"),
            max_f1=("f1", "max"),
            total_tp=("tp", "sum"),
            total_fp=("fp", "sum"),
            total_tn=("tn", "sum"),
            total_fn=("fn", "sum"),
        )
    )

    # Primary selection criterion: highest mean held-out F1.
    # Tie-breaker 1: higher mean precision.
    # Tie-breaker 2: higher mean recall.
    # Tie-breaker 3: middle-of-band threshold (0.60) when metrics are
    # numerically tied, to avoid unnecessarily choosing an extreme.
    summary_df["distance_from_midpoint"] = (
        summary_df["threshold"] - 0.60
    ).abs()

    summary_df = summary_df.sort_values(
        [
            "mean_f1",
            "mean_precision",
            "mean_recall",
            "distance_from_midpoint",
        ],
        ascending=[
            False,
            False,
            False,
            True,
        ],
    ).reset_index(drop=True)

    selected = summary_df.iloc[0]

    # Stability band: all thresholds whose mean F1 is within 0.005
    # absolute F1 of the best. This is descriptive, not a second
    # selection criterion.
    best_f1 = float(selected["mean_f1"])
    near_best = summary_df[
        (best_f1 - summary_df["mean_f1"]) <= 0.005
    ].sort_values("threshold")

    stability_band = (
        f"{near_best['threshold'].min():.2f}-"
        f"{near_best['threshold'].max():.2f}"
    )

    selected_threshold = float(selected["threshold"])

    # Check whether the previously observed 0.59 threshold remains
    # close to the selected point.
    old_threshold_row = summary_df[
        np.isclose(
            summary_df["threshold"],
            0.59,
        )
    ]

    if old_threshold_row.empty:
        old_threshold_f1 = None
        old_threshold_precision = None
        old_threshold_recall = None
    else:
        old = old_threshold_row.iloc[0]
        old_threshold_f1 = float(old["mean_f1"])
        old_threshold_precision = float(old["mean_precision"])
        old_threshold_recall = float(old["mean_recall"])

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save unsorted fold results in natural threshold/fold order.
    results_df.sort_values(
        ["threshold", "fold"]
    ).to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # Save the summary in threshold order for easy inspection.
    summary_for_file = summary_df.sort_values(
        "threshold"
    ).copy()

    summary_for_file.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8",
    )

    config_output = {
        "status": "experimental",
        "validation_type": "5-fold threshold sensitivity analysis",
        "folds": N_SPLITS,
        "random_seed": RANDOM_SEED,
        "time_window_days": selected_window,
        "text_weight": text_weight,
        "distance_weight": distance_weight,
        "recency_weight": recency_weight,
        "thresholds_tested": [
            float(x) for x in THRESHOLDS
        ],
        "selected_threshold_by_mean_heldout_f1": selected_threshold,
        "selected_threshold_mean_precision": float(
            selected["mean_precision"]
        ),
        "selected_threshold_std_precision": float(
            selected["std_precision"]
        ),
        "selected_threshold_mean_recall": float(
            selected["mean_recall"]
        ),
        "selected_threshold_std_recall": float(
            selected["std_recall"]
        ),
        "selected_threshold_mean_f1": best_f1,
        "selected_threshold_std_f1": float(
            selected["std_f1"]
        ),
        "near_best_f1_band_within_0.005": stability_band,
        "previous_threshold_0_59_mean_f1": old_threshold_f1,
        "previous_threshold_0_59_mean_precision": old_threshold_precision,
        "previous_threshold_0_59_mean_recall": old_threshold_recall,
        "note": (
            "Experimental only. Threshold does not represent official "
            "TDMC policy. Benchmark labels are synthetic-by-construction. "
            "Final duplicate methodology requires final validation and "
            "documentation before freeze."
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
    print("THRESHOLD SUMMARY")
    print("=" * 80)

    print(
        summary_for_file[
            [
                "threshold",
                "mean_precision",
                "std_precision",
                "mean_recall",
                "std_recall",
                "mean_f1",
                "std_f1",
                "total_fp",
                "total_fn",
            ]
        ].to_string(index=False)
    )

    print()
    print("=" * 80)
    print("EXPERIMENTAL THRESHOLD SELECTED BY MEAN HELD-OUT F1")
    print("=" * 80)
    print(f"Threshold                   : {selected_threshold:.2f}")
    print(
        f"Mean Precision              : "
        f"{selected['mean_precision']:.4f}"
    )
    print(
        f"Mean Recall                 : "
        f"{selected['mean_recall']:.4f}"
    )
    print(
        f"Mean F1                     : "
        f"{selected['mean_f1']:.4f}"
    )
    print(
        f"F1 Std                      : "
        f"{selected['std_f1']:.4f}"
    )
    print(
        f"Near-best F1 band (±0.005)  : "
        f"{stability_band}"
    )

    print()
    print("PREVIOUS 0.59 THRESHOLD")
    print("-" * 80)

    if old_threshold_f1 is None:
        print("0.59 was not found in the evaluation output.")
    else:
        print(
            f"Mean Precision              : "
            f"{old_threshold_precision:.4f}"
        )
        print(
            f"Mean Recall                 : "
            f"{old_threshold_recall:.4f}"
        )
        print(
            f"Mean F1                     : "
            f"{old_threshold_f1:.4f}"
        )

    print()
    print("OUTPUT FILES")
    print("-" * 80)
    print(f"Fold results                : {OUTPUT_FILE}")
    print(f"Threshold summary           : {SUMMARY_FILE}")
    print(f"Selected config             : {CONFIG_OUTPUT_FILE}")

    print()
    print("IMPORTANT")
    print("-" * 80)
    print("This threshold is experimental only.")
    print("Benchmark labels are synthetic-by-construction.")
    print("Do not describe it as official TDMC policy.")
    print(
        "Do not freeze the threshold until the complete Step 12 "
        "validation sequence is finished."
    )

    print()
    print("=" * 80)
    print("FINAL THRESHOLD VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
