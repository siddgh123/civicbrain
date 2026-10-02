from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# ============================================================================
# CIVICBRAIN STEP 13.1 — WORK-TYPE INPUT INSPECTION
#
# Purpose:
#   Inspect the ACTUAL Step 8 complaint categories and Step 10 issue types
#   before creating the final work_type_mapping.csv.
#
# This script is READ-ONLY with respect to project source datasets.
# It does not modify PostgreSQL or any existing CivicBrain source file.
#
# Project root expected:
#   C:\Users\Siddhesh\OneDrive\OneDrive\Desktop\CivicBrain
#
# Correct project root:
#   C:\Users\Siddhesh\OneDrive\Desktop\CivicBrain
#
# Script location:
#   CivicBrain\scripts\optimization\jobs\inspect_step13_work_type_inputs.py
#
# parents[0] = jobs
# parents[1] = optimization
# parents[2] = scripts
# parents[3] = CivicBrain
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

STEP8_FILE = (
    DATA_DIR
    / "complaints"
    / "verified"
    / "complaints_verified.csv"
)

STEP10_FILE = (
    DATA_DIR
    / "resources"
    / "processed"
    / "resource_dataset.csv"
)

OUTPUT_DIR = DATA_DIR / "optimization" / "config"

CANDIDATE_MAPPING_FILE = (
    OUTPUT_DIR / "work_type_mapping_candidate.csv"
)

REPORT_FILE = (
    OUTPUT_DIR / "work_type_input_inspection.json"
)

# Frozen Step 9 classes from the project.
FROZEN_CLASS_TO_WORK_TYPE = {
    "pothole": ("Pothole", "ROAD"),
    "garbage accumulation": ("Garbage Accumulation", "GENERAL"),
    "waterlogging": ("Waterlogging", "WATER"),
    "road damage": ("Road Damage", "ROAD"),
}


def normalize(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())


def load_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found:\n{path}"
        )

    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise RuntimeError(
            f"Could not read {label}:\n{path}\nError: {exc}"
        ) from exc


def counts_table(df: pd.DataFrame, column: str) -> list[dict]:
    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    counts = (
        values.value_counts(dropna=False)
        .rename_axis(column)
        .reset_index(name="count")
    )

    return counts.to_dict(orient="records")


def build_mapping_rows(
    source_values: list[str],
    source_type: str,
) -> list[dict]:
    rows: list[dict] = []

    for raw_value in source_values:
        key = normalize(raw_value)

        if key in FROZEN_CLASS_TO_WORK_TYPE:
            canonical, work_type = FROZEN_CLASS_TO_WORK_TYPE[key]
            rows.append(
                {
                    "source_value": raw_value,
                    "source_type": source_type,
                    "work_type": work_type,
                    "team_type": work_type,
                    "mapping_status": "CANDIDATE_REVIEW",
                    "reason": (
                        f"Exact normalized match to frozen Step 9 class "
                        f"'{canonical}'. Mapping is suggested only; "
                        f"human/project validation is still required."
                    ),
                }
            )
        else:
            rows.append(
                {
                    "source_value": raw_value,
                    "source_type": source_type,
                    "work_type": "",
                    "team_type": "",
                    "mapping_status": "REVIEW_REQUIRED",
                    "reason": (
                        "No exact normalized match to the frozen Step 9 "
                        "classes. Do not assign an operational work type "
                        "automatically."
                    ),
                }
            )

    return rows


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.1 — WORK-TYPE INPUT INSPECTION")
    print("=" * 80)

    print()
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Step 8 file  : {STEP8_FILE}")
    print(f"Step 10 file : {STEP10_FILE}")

    expected_step8 = {
        "complaint_id",
        "category",
    }
    expected_step10 = {
        "complaint_id",
        "issue_type",
        "estimated_workers",
        "estimated_duration_hours",
        "total_cost",
        "required_equipment",
    }

    step8 = load_csv(STEP8_FILE, "Step 8 complaint dataset")
    step10 = load_csv(STEP10_FILE, "Step 10 resource dataset")

    missing_step8 = expected_step8 - set(step8.columns)
    missing_step10 = expected_step10 - set(step10.columns)

    if missing_step8:
        raise ValueError(
            "Step 8 is missing required columns: "
            + ", ".join(sorted(missing_step8))
        )

    if missing_step10:
        raise ValueError(
            "Step 10 is missing required columns: "
            + ", ".join(sorted(missing_step10))
        )

    step8_ids = set(
        step8["complaint_id"]
        .astype(str)
        .str.strip()
    )
    step10_ids = set(
        step10["complaint_id"]
        .astype(str)
        .str.strip()
    )

    categories = (
        step8["category"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    issue_types = (
        step10["issue_type"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    category_values = sorted(
        [v for v in categories.unique().tolist() if v]
    )
    issue_type_values = sorted(
        [v for v in issue_types.unique().tolist() if v]
    )

    print()
    print("-" * 80)
    print("STEP 8 — ACTUAL COMPLAINT CATEGORIES")
    print("-" * 80)

    for row in counts_table(step8, "category"):
        print(f"{row['category']!r:35} : {row['count']}")

    print()
    print("-" * 80)
    print("STEP 10 — ACTUAL RESOURCE ISSUE TYPES")
    print("-" * 80)

    for row in counts_table(step10, "issue_type"):
        print(f"{row['issue_type']!r:35} : {row['count']}")

    print()
    print("-" * 80)
    print("JOIN / COVERAGE CHECK")
    print("-" * 80)

    ids_only_step8 = sorted(step8_ids - step10_ids)
    ids_only_step10 = sorted(step10_ids - step8_ids)
    common_ids = step8_ids & step10_ids

    print(f"Step 8 rows             : {len(step8)}")
    print(f"Step 10 rows            : {len(step10)}")
    print(f"Common complaint IDs    : {len(common_ids)}")
    print(f"Only in Step 8          : {len(ids_only_step8)}")
    print(f"Only in Step 10         : {len(ids_only_step10)}")

    if ids_only_step8:
        print("First Step 8-only IDs   :", ", ".join(ids_only_step8[:10]))

    if ids_only_step10:
        print("First Step 10-only IDs  :", ", ".join(ids_only_step10[:10]))

    merged_types = (
        step8[
            ["complaint_id", "category"]
        ]
        .copy()
        .assign(
            complaint_id=lambda x: x["complaint_id"].astype(str).str.strip()
        )
        .merge(
            step10[
                [
                    "complaint_id",
                    "issue_type",
                    "estimated_workers",
                    "estimated_duration_hours",
                    "total_cost",
                    "required_equipment",
                ]
            ].assign(
                complaint_id=lambda x: (
                    x["complaint_id"].astype(str).str.strip()
                )
            ),
            on="complaint_id",
            how="inner",
        )
    )

    mismatched_category_issue = []
    for _, row in merged_types.iterrows():
        cat = normalize(row["category"])
        issue = normalize(row["issue_type"])

        if cat and issue and cat != issue:
            mismatched_category_issue.append(
                {
                    "complaint_id": str(row["complaint_id"]),
                    "category": str(row["category"]),
                    "issue_type": str(row["issue_type"]),
                }
            )

    print(
        "Category vs issue_type exact-normalized matches : "
        f"{len(merged_types) - len(mismatched_category_issue)}"
    )
    print(
        "Category vs issue_type normalized mismatches    : "
        f"{len(mismatched_category_issue)}"
    )

    print()
    print("-" * 80)
    print("RESOURCE FIELD COMPLETENESS")
    print("-" * 80)

    resource_fields = [
        "estimated_workers",
        "estimated_duration_hours",
        "total_cost",
        "required_equipment",
    ]

    resource_missing = {}
    for column in resource_fields:
        missing = int(
            step10[column].isna().sum()
            + (
                step10[column]
                .astype(str)
                .str.strip()
                .eq("")
            ).sum()
        )
        resource_missing[column] = missing
        print(f"{column:30} : missing/blank = {missing}")

    mapping_rows = []
    mapping_rows.extend(
        build_mapping_rows(
            category_values,
            "step8_category",
        )
    )
    mapping_rows.extend(
        build_mapping_rows(
            issue_type_values,
            "step10_issue_type",
        )
    )

    mapping_df = pd.DataFrame(
        mapping_rows,
        columns=[
            "source_value",
            "source_type",
            "work_type",
            "team_type",
            "mapping_status",
            "reason",
        ],
    )

    # De-duplicate identical source/type rows.
    mapping_df = (
        mapping_df
        .drop_duplicates(
            subset=["source_value", "source_type"],
            keep="first",
        )
        .sort_values(
            ["source_type", "source_value"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping_df.to_csv(
        CANDIDATE_MAPPING_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    report = {
        "step": "13.1_work_type_input_inspection",
        "read_only": True,
        "project_root": str(PROJECT_ROOT),
        "step8_file": str(STEP8_FILE),
        "step10_file": str(STEP10_FILE),
        "step8_row_count": int(len(step8)),
        "step10_row_count": int(len(step10)),
        "step8_category_counts": counts_table(step8, "category"),
        "step10_issue_type_counts": counts_table(step10, "issue_type"),
        "join": {
            "step8_unique_ids": len(step8_ids),
            "step10_unique_ids": len(step10_ids),
            "common_ids": len(common_ids),
            "only_in_step8": len(ids_only_step8),
            "only_in_step10": len(ids_only_step10),
            "category_issue_normalized_mismatches": len(
                mismatched_category_issue
            ),
            "mismatch_examples": mismatched_category_issue[:20],
        },
        "resource_field_missing_counts": resource_missing,
        "frozen_class_mapping_reference": {
            k: {
                "canonical_class": v[0],
                "work_type": v[1],
            }
            for k, v in FROZEN_CLASS_TO_WORK_TYPE.items()
        },
        "candidate_mapping_file": str(CANDIDATE_MAPPING_FILE),
        "final_mapping_status_rule": (
            "Do not change CANDIDATE_REVIEW to VALIDATED until actual "
            "Step 8/Step 10 values are confirmed to represent the same "
            "operational work type. Unmatched values remain REVIEW_REQUIRED."
        ),
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("-" * 80)
    print("OUTPUTS")
    print("-" * 80)
    print(f"Candidate mapping : {CANDIDATE_MAPPING_FILE}")
    print(f"Inspection report : {REPORT_FILE}")

    print()
    print("-" * 80)
    print("GATE")
    print("-" * 80)

    candidate_review = int(
        (mapping_df["mapping_status"] == "CANDIDATE_REVIEW").sum()
    )
    review_required = int(
        (mapping_df["mapping_status"] == "REVIEW_REQUIRED").sum()
    )

    print(f"CANDIDATE_REVIEW  : {candidate_review}")
    print(f"REVIEW_REQUIRED   : {review_required}")

    if review_required:
        print()
        print(
            "STOP: At least one actual category/issue_type is not covered "
            "by the frozen Step 9 class mapping."
        )
        print(
            "Review the candidate mapping before building eligible_jobs.csv."
        )
    else:
        print()
        print(
            "All observed values have a candidate mapping. "
            "Human/project validation is still required before marking "
            "the mappings VALIDATED."
        )

    print()
    print("STEP 13.1 INPUT INSPECTION COMPLETE")


if __name__ == "__main__":
    main()
