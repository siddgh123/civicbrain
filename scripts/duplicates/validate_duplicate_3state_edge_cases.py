from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


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
    / "duplicate_edge_case_validation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_edge_case_summary.csv"
)

CONFIG_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "duplicates"
    / "duplicate_3state_config.json"
)

# Experimentally supported configuration from the previous validation.
TIME_WINDOW_DAYS = 7
TEXT_WEIGHT = 0.70
DISTANCE_WEIGHT = 0.20
RECENCY_WEIGHT = 0.10
DUPLICATE_THRESHOLD = 0.59

# Conservative review band around the validated threshold.
# This is a proposed safety band and is NOT yet frozen.
UNCERTAIN_LOWER_BOUND = 0.55


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

    return df.reset_index(drop=True)


def calculate_score(
    text_similarity: float,
    distance_score: float,
    recency_score: float,
) -> float:
    return float(
        np.clip(
            TEXT_WEIGHT * text_similarity
            + DISTANCE_WEIGHT * distance_score
            + RECENCY_WEIGHT * recency_score,
            0.0,
            1.0,
        )
    )


def classify_score(score: float) -> str:
    if score >= DUPLICATE_THRESHOLD:
        return "DUPLICATE"

    if score >= UNCERTAIN_LOWER_BOUND:
        return "UNCERTAIN"

    return "NOT_DUPLICATE"


def classify_input_case(
    *,
    score: float | None,
    distance_meters: float | None,
    has_text: bool,
    has_gps: bool,
    has_timestamp: bool,
) -> str:
    # Missing critical fields must never be auto-merged.
    if not has_text or not has_gps or not has_timestamp:
        return "UNCERTAIN"

    # Candidate generation rule: outside the configured spatial
    # candidate radius is not a duplicate candidate.
    if distance_meters is not None and distance_meters > 300:
        return "NOT_DUPLICATE"

    if score is None:
        return "UNCERTAIN"

    return classify_score(score)


def score_from_row(row: pd.Series) -> float:
    return calculate_score(
        float(row["text_similarity"]),
        float(row["distance_score"]),
        float(row["recency_score_7d"]),
    )


def add_case(
    rows: list[dict],
    case_id: str,
    category: str,
    expected_decision: str,
    actual_decision: str,
    score: float | None,
    *,
    has_text: bool = True,
    has_gps: bool = True,
    has_timestamp: bool = True,
    distance_meters: float | None = None,
    note: str = "",
) -> None:
    rows.append(
        {
            "case_id": case_id,
            "category": category,
            "expected_decision": expected_decision,
            "actual_decision": actual_decision,
            "score": score,
            "has_text": has_text,
            "has_gps": has_gps,
            "has_timestamp": has_timestamp,
            "distance_meters": distance_meters,
            "pass": expected_decision == actual_decision,
            "note": note,
        }
    )


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 12 — 3-STATE + EDGE-CASE VALIDATION")
    print("=" * 80)

    df = load_data()

    print()
    print("EXPERIMENTAL 3-STATE LOGIC")
    print("-" * 80)
    print(
        f"NOT_DUPLICATE : score < {UNCERTAIN_LOWER_BOUND:.2f}"
    )
    print(
        f"UNCERTAIN     : {UNCERTAIN_LOWER_BOUND:.2f} <= "
        f"score < {DUPLICATE_THRESHOLD:.2f}"
    )
    print(
        f"DUPLICATE     : score >= {DUPLICATE_THRESHOLD:.2f}"
    )
    print()
    print("Safety rules:")
    print("1. Missing text/GPS/timestamp -> UNCERTAIN")
    print("2. Distance > 300 m -> NOT_DUPLICATE candidate")
    print("3. No automatic merge for UNCERTAIN cases")

    cases: list[dict] = []

    # ------------------------------------------------------------
    # A. Exact decision-boundary tests
    # ------------------------------------------------------------
    for score, expected, label in [
        (0.40, "NOT_DUPLICATE", "low score"),
        (0.54, "NOT_DUPLICATE", "just below uncertain band"),
        (0.55, "UNCERTAIN", "uncertain lower boundary"),
        (0.57, "UNCERTAIN", "middle uncertain score"),
        (0.58, "UNCERTAIN", "just below duplicate threshold"),
        (0.59, "DUPLICATE", "exact duplicate threshold"),
        (0.60, "DUPLICATE", "just above duplicate threshold"),
        (0.80, "DUPLICATE", "high score"),
    ]:
        actual = classify_input_case(
            score=score,
            distance_meters=100,
            has_text=True,
            has_gps=True,
            has_timestamp=True,
        )
        add_case(
            cases,
            f"BOUNDARY_{str(score).replace('.', '_')}",
            "decision_boundary",
            expected,
            actual,
            score,
            distance_meters=100,
            note=label,
        )

    # ------------------------------------------------------------
    # B. Missing-input safety tests
    # ------------------------------------------------------------
    missing_cases = [
        ("MISSING_TEXT", False, True, True, "Missing complaint text"),
        ("MISSING_GPS", True, False, True, "Missing GPS"),
        (
            "MISSING_TIMESTAMP",
            True,
            True,
            False,
            "Missing complaint timestamp",
        ),
        (
            "MISSING_TEXT_GPS",
            False,
            False,
            True,
            "Missing text and GPS",
        ),
        (
            "MISSING_ALL_REQUIRED",
            False,
            False,
            False,
            "Missing text, GPS and timestamp",
        ),
    ]

    for case_id, has_text, has_gps, has_timestamp, note in missing_cases:
        actual = classify_input_case(
            score=0.95,
            distance_meters=10,
            has_text=has_text,
            has_gps=has_gps,
            has_timestamp=has_timestamp,
        )
        add_case(
            cases,
            case_id,
            "missing_required_input",
            "UNCERTAIN",
            actual,
            0.95,
            has_text=has_text,
            has_gps=has_gps,
            has_timestamp=has_timestamp,
            distance_meters=10,
            note=note,
        )

    # ------------------------------------------------------------
    # C. Spatial candidate boundary tests
    # ------------------------------------------------------------
    for distance, expected, label in [
        (3.0, "DUPLICATE", "very close candidate with high score"),
        (299.9, "DUPLICATE", "inside 300 m candidate radius"),
        (300.0, "DUPLICATE", "exact 300 m candidate boundary"),
        (300.1, "NOT_DUPLICATE", "outside 300 m candidate radius"),
        (500.0, "NOT_DUPLICATE", "far pair"),
    ]:
        actual = classify_input_case(
            score=0.85,
            distance_meters=distance,
            has_text=True,
            has_gps=True,
            has_timestamp=True,
        )
        add_case(
            cases,
            f"SPATIAL_{str(distance).replace('.', '_')}",
            "spatial_candidate_boundary",
            expected,
            actual,
            0.85,
            distance_meters=distance,
            note=label,
        )

    # ------------------------------------------------------------
    # D. Constructed semantic/spatial/recency combinations
    # ------------------------------------------------------------
    constructed_cases = [
        {
            "case_id": "SEMANTIC_HIGH_NEAR_RECENT",
            "expected": "DUPLICATE",
            "text": 0.90,
            "distance": 0.90,
            "recency": 0.90,
            "distance_m": 20,
            "note": "High semantic similarity + near location + recent report",
        },
        {
            "case_id": "SEMANTIC_MEDIUM_BORDERLINE",
            "expected": "UNCERTAIN",
            "text": 0.68,
            "distance": 0.35,
            "recency": 0.35,
            "distance_m": 140,
            "note": (
                "Designed to land inside the declared UNCERTAIN score band"
            ),
        },
        {
            "case_id": "SEMANTIC_LOW_FAR_OLD",
            "expected": "NOT_DUPLICATE",
            "text": 0.35,
            "distance": 0.20,
            "recency": 0.20,
            "distance_m": 280,
            "note": "Weak combined evidence",
        },
        {
            "case_id": "HIGH_TEXT_WEAK_GEOMETRY",
            "expected": "DUPLICATE",
            "text": 0.90,
            "distance": 0.10,
            "recency": 0.20,
            "distance_m": 260,
            "note": (
                "High text similarity but weak spatial/recency evidence; "
                "tests whether the declared 70% text weighting dominates "
                "the combined score as configured"
            ),
        },
        {
            "case_id": "LOW_TEXT_STRONG_GEOMETRY",
            "expected": "UNCERTAIN",
            "text": 0.40,
            "distance": 0.95,
            "recency": 0.95,
            "distance_m": 15,
            "note": "Very close/recent but weak textual similarity",
        },
    ]

    for item in constructed_cases:
        score = calculate_score(
            item["text"],
            item["distance"],
            item["recency"],
        )

        # Specification sanity check:
        # The expected label for a constructed score-based test must
        # agree with the declared 3-state score bands. This prevents
        # the test itself from being internally inconsistent.
        score_decision = classify_score(score)

        if score_decision != item["expected"]:
            raise ValueError(
                f"Constructed test specification error: "
                f"{item['case_id']} expects {item['expected']} "
                f"but score={score:.4f} maps to {score_decision} "
                f"under the declared score bands."
            )

        actual = classify_input_case(
            score=score,
            distance_meters=item["distance_m"],
            has_text=True,
            has_gps=True,
            has_timestamp=True,
        )

        add_case(
            cases,
            item["case_id"],
            "constructed_evidence_pattern",
            item["expected"],
            actual,
            score,
            distance_meters=item["distance_m"],
            note=(
                f"{item['note']}; calculated score={score:.4f}"
            ),
        )

    # ------------------------------------------------------------
    # E. Representative real benchmark rows for logic inspection
    # These do NOT create official ground truth.
    # ------------------------------------------------------------
    representative = (
        df.copy()
        .assign(calculated_score=df.apply(score_from_row, axis=1))
        .sort_values("calculated_score")
    )

    selections = {
        "LOWEST_SCORE": representative.iloc[0],
        "HIGHEST_SCORE": representative.iloc[-1],
    }

    uncertain_candidates = representative[
        (
            representative["calculated_score"]
            >= UNCERTAIN_LOWER_BOUND
        )
        & (
            representative["calculated_score"]
            < DUPLICATE_THRESHOLD
        )
    ]

    if not uncertain_candidates.empty:
        selections["BORDERLINE_SCORE"] = (
            uncertain_candidates.iloc[
                (
                    uncertain_candidates["calculated_score"]
                    - (
                        (
                            UNCERTAIN_LOWER_BOUND
                            + DUPLICATE_THRESHOLD
                        )
                        / 2
                    )
                )
                .abs()
                .argmin()
            ]
        )

    nearest = df.nsmallest(
        1,
        "time_difference_hours",
    )
    if not nearest.empty:
        selections["MOST_RECENT_PAIR"] = nearest.iloc[0]

    near_spatial = (
        df.assign(calculated_score=df.apply(score_from_row, axis=1))
        .sort_values("distance_meters" if "distance_meters" in df.columns else "distance_score")
    )

    # The feature file may store normalized distance rather than meters.
    # For representative evidence, use the existing score fields only.
    for name, row in selections.items():
        score = score_from_row(row)
        actual = classify_input_case(
            score=score,
            distance_meters=None,
            has_text=True,
            has_gps=True,
            has_timestamp=True,
        )

        add_case(
            cases,
            f"DATA_{name}",
            "representative_benchmark_row",
            actual,
            actual,
            score,
            note=(
                "Representative synthetic benchmark row used to inspect "
                "deterministic 3-state classification; not official TDMC ground truth."
            ),
        )

    results_df = pd.DataFrame(cases)

    summary_df = (
        results_df
        .groupby("category", as_index=False)
        .agg(
            total_cases=("case_id", "count"),
            passed=("pass", "sum"),
            failed=("pass", lambda s: int((~s).sum())),
        )
    )

    total_cases = len(results_df)
    total_passed = int(results_df["pass"].sum())
    total_failed = int((~results_df["pass"]).sum())

    print()
    print("=" * 80)
    print("EDGE-CASE VALIDATION SUMMARY")
    print("=" * 80)
    print(summary_df.to_string(index=False))

    print()
    print(f"Total cases                 : {total_cases}")
    print(f"Passed                      : {total_passed}")
    print(f"Failed                      : {total_failed}")

    if total_failed:
        print()
        print("FAILED CASES")
        print("-" * 80)
        print(
            results_df.loc[
                ~results_df["pass"],
                [
                    "case_id",
                    "category",
                    "expected_decision",
                    "actual_decision",
                    "score",
                    "note",
                ],
            ].to_string(index=False)
        )

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
        "time_window_days": TIME_WINDOW_DAYS,
        "text_weight": TEXT_WEIGHT,
        "distance_weight": DISTANCE_WEIGHT,
        "recency_weight": RECENCY_WEIGHT,
        "duplicate_threshold": DUPLICATE_THRESHOLD,
        "uncertain_lower_bound": UNCERTAIN_LOWER_BOUND,
        "decision_rules": {
            "duplicate": (
                f"score >= {DUPLICATE_THRESHOLD:.2f}"
            ),
            "uncertain": (
                f"{UNCERTAIN_LOWER_BOUND:.2f} <= score < "
                f"{DUPLICATE_THRESHOLD:.2f}"
            ),
            "not_duplicate": (
                f"score < {UNCERTAIN_LOWER_BOUND:.2f}"
            ),
            "missing_required_input": (
                "UNCERTAIN"
            ),
            "outside_candidate_radius": (
                "NOT_DUPLICATE candidate decision"
            ),
        },
        "validation_cases": total_cases,
        "passed_cases": total_passed,
        "failed_cases": total_failed,
        "note": (
            "The 0.55 uncertain lower bound is a proposed safety "
            "band based on the previously tested threshold range. "
            "It is not an official TDMC rule and is not frozen. "
            "Benchmark data are synthetic-by-construction."
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
    print("OUTPUT FILES")
    print("=" * 80)
    print(f"Case results                 : {OUTPUT_FILE}")
    print(f"Category summary             : {SUMMARY_FILE}")
    print(f"3-state config               : {CONFIG_OUTPUT_FILE}")

    print()
    if total_failed == 0:
        print("ALL 3-STATE / EDGE-CASE VALIDATION TESTS PASSED")
    else:
        print("EDGE-CASE VALIDATION FOUND FAILURES — DO NOT FREEZE")

    print()
    print("IMPORTANT")
    print("-" * 80)
    print(
        "These tests validate decision logic and safety handling, "
        "not real TDMC duplicate-detection accuracy."
    )
    print(
        "UNCERTAIN cases must remain manual-review cases and must not "
        "be auto-merged."
    )
    print(
        "The 0.55-0.59 review band is experimental and must not be "
        "called official TDMC policy."
    )

    print()
    print("=" * 80)
    print("3-STATE + EDGE-CASE VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
