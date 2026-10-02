from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# ============================================================================
# CIVICBRAIN STEP 13.1 — FINAL WORK-TYPE MAPPING
#
# Purpose:
#   Create the FINAL Step 13 operational work-type mapping using the
#   approved CivicBrain 4-category scope:
#
#       ROAD
#       WATER
#       GARBAGE
#       ELECTRICITY
#
# Important:
#   - Step 9 YOLO classes remain unchanged.
#   - Step 13 does NOT create 8 operational work types.
#   - "Other" is NOT silently forced into a category.
#   - "Other" remains REVIEW_REQUIRED and therefore cannot become an
#     executable Step 13 job.
#   - This script does not modify PostgreSQL.
#   - Existing Step 8 and Step 10 source datasets are read-only.
#
# Correct project root:
#   C:\Users\Siddhesh\OneDrive\Desktop\CivicBrain
#
# Script location:
#   CivicBrain\scripts\optimization\jobs\
#       build_step13_final_work_type_mapping.py
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

FINAL_MAPPING_FILE = (
    OUTPUT_DIR / "work_type_mapping.csv"
)

VALIDATION_FILE = (
    OUTPUT_DIR / "work_type_mapping_validation.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "work_type_mapping_summary.json"
)

# ============================================================================
# FINAL FROZEN CIVICBRAIN OPERATIONAL SCOPE
#
# These are Step 13 operational categories, not additional YOLO classes.
# ============================================================================

APPROVED_MAPPING = {
    "pothole": {
        "work_type": "ROAD",
        "team_type": "ROAD",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Pothole is handled under ROAD."
        ),
    },
    "road damage": {
        "work_type": "ROAD",
        "team_type": "ROAD",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Road Damage is handled under ROAD."
        ),
    },
    "waterlogging": {
        "work_type": "WATER",
        "team_type": "WATER",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Waterlogging is handled under WATER."
        ),
    },
    "water leakage": {
        "work_type": "WATER",
        "team_type": "WATER",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Water Leakage is handled under WATER."
        ),
    },
    "blocked drain": {
        "work_type": "WATER",
        "team_type": "WATER",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Blocked Drain is grouped under WATER for the four-category "
            "operational scope. This is a project-level normalization rule, "
            "not an official TDMC departmental classification."
        ),
    },
    "garbage accumulation": {
        "work_type": "GARBAGE",
        "team_type": "GARBAGE",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Garbage Accumulation is handled under GARBAGE."
        ),
    },
    "streetlight": {
        "work_type": "ELECTRICITY",
        "team_type": "ELECTRICITY",
        "reason": (
            "CivicBrain Step 13 approved operational grouping: "
            "Streetlight is handled under ELECTRICITY."
        ),
    },
    "other": {
        "work_type": "",
        "team_type": "",
        "reason": (
            "Other cannot be deterministically assigned to one of the four "
            "approved operational work types from the available category "
            "value alone. Keep in REVIEW_REQUIRED and exclude from "
            "executable Step 13 jobs until manually classified."
        ),
    },
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


def unique_nonblank_values(
    df: pd.DataFrame,
    column: str,
) -> list[str]:
    return sorted(
        {
            str(value).strip()
            for value in df[column].dropna()
            if str(value).strip()
        },
        key=lambda x: x.lower(),
    )


def make_mapping_row(
    source_value: str,
    source_type: str,
) -> dict:
    key = normalize(source_value)

    if key not in APPROVED_MAPPING:
        return {
            "source_value": source_value,
            "source_type": source_type,
            "work_type": "",
            "team_type": "",
            "mapping_status": "REVIEW_REQUIRED",
            "reason": (
                "Observed source value is not covered by the approved "
                "four-category CivicBrain mapping."
            ),
        }

    rule = APPROVED_MAPPING[key]

    if key == "other":
        status = "REVIEW_REQUIRED"
    else:
        status = "VALIDATED"

    return {
        "source_value": source_value,
        "source_type": source_type,
        "work_type": rule["work_type"],
        "team_type": rule["team_type"],
        "mapping_status": status,
        "reason": rule["reason"],
    }


def validation_row(
    check_id: str,
    status: str,
    actual_value: object,
    expected_value: object,
    notes: str,
) -> dict:
    return {
        "check_id": check_id,
        "status": status,
        "actual_value": str(actual_value),
        "expected_value": str(expected_value),
        "notes": notes,
    }


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.1 — FINAL WORK-TYPE MAPPING")
    print("=" * 80)

    print()
    print("Project root :", PROJECT_ROOT)
    print("Step 8 file  :", STEP8_FILE)
    print("Step 10 file :", STEP10_FILE)

    step8 = load_csv(STEP8_FILE, "Step 8 complaint dataset")
    step10 = load_csv(STEP10_FILE, "Step 10 resource dataset")

    required_step8 = {"complaint_id", "category"}
    required_step10 = {"complaint_id", "issue_type"}

    missing_step8 = required_step8 - set(step8.columns)
    missing_step10 = required_step10 - set(step10.columns)

    if missing_step8:
        raise ValueError(
            "Step 8 missing columns: "
            + ", ".join(sorted(missing_step8))
        )

    if missing_step10:
        raise ValueError(
            "Step 10 missing columns: "
            + ", ".join(sorted(missing_step10))
        )

    # ------------------------------------------------------------------------
    # Validate the previously inspected fact:
    # Step 8 and Step 10 use the same issue/category values for the same IDs.
    # ------------------------------------------------------------------------

    s8 = (
        step8[["complaint_id", "category"]]
        .copy()
        .assign(
            complaint_id=lambda x: (
                x["complaint_id"].astype(str).str.strip()
            ),
            category=lambda x: (
                x["category"].fillna("").astype(str).str.strip()
            ),
        )
    )

    s10 = (
        step10[["complaint_id", "issue_type"]]
        .copy()
        .assign(
            complaint_id=lambda x: (
                x["complaint_id"].astype(str).str.strip()
            ),
            issue_type=lambda x: (
                x["issue_type"].fillna("").astype(str).str.strip()
            ),
        )
    )

    merged = s8.merge(
        s10,
        on="complaint_id",
        how="outer",
        indicator=True,
    )

    both = merged[merged["_merge"] == "both"].copy()

    mismatches = both[
        both.apply(
            lambda row: normalize(row["category"])
            != normalize(row["issue_type"]),
            axis=1,
        )
    ]

    only_step8 = int((merged["_merge"] == "left_only").sum())
    only_step10 = int((merged["_merge"] == "right_only").sum())

    categories = unique_nonblank_values(step8, "category")
    issue_types = unique_nonblank_values(step10, "issue_type")

    all_source_pairs: list[tuple[str, str]] = []

    for value in categories:
        all_source_pairs.append((value, "step8_category"))

    for value in issue_types:
        all_source_pairs.append((value, "step10_issue_type"))

    mapping_rows = [
        make_mapping_row(value, source_type)
        for value, source_type in all_source_pairs
    ]

    mapping_df = (
        pd.DataFrame(
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

    # ------------------------------------------------------------------------
    # Expected 4 operational work types.
    # ------------------------------------------------------------------------

    actual_work_types = set(
        mapping_df.loc[
            mapping_df["mapping_status"] == "VALIDATED",
            "work_type",
        ]
        .dropna()
        .astype(str)
        .str.strip()
    )

    expected_work_types = {
        "ROAD",
        "WATER",
        "GARBAGE",
        "ELECTRICITY",
    }

    review_values = set(
        mapping_df.loc[
            mapping_df["mapping_status"] == "REVIEW_REQUIRED",
            "source_value",
        ]
    )

    validations: list[dict] = []

    validations.append(
        validation_row(
            "SOURCE_STEP8_ROW_COUNT",
            "PASS" if len(step8) == 500 else "FAIL",
            len(step8),
            500,
            "Step 8 must contain 500 complaint records.",
        )
    )

    validations.append(
        validation_row(
            "SOURCE_STEP10_ROW_COUNT",
            "PASS" if len(step10) == 500 else "FAIL",
            len(step10),
            500,
            "Step 10 must contain 500 resource records.",
        )
    )

    validations.append(
        validation_row(
            "COMMON_COMPLAINT_IDS",
            "PASS"
            if len(both) == 500 and only_step8 == 0 and only_step10 == 0
            else "FAIL",
            f"common={len(both)}, step8_only={only_step8}, step10_only={only_step10}",
            "common=500, step8_only=0, step10_only=0",
            "Step 8 and Step 10 must join one-to-one for all complaint IDs.",
        )
    )

    validations.append(
        validation_row(
            "CATEGORY_ISSUE_TYPE_MATCH",
            "PASS" if len(mismatches) == 0 else "FAIL",
            len(mismatches),
            0,
            "Step 8 category and Step 10 issue_type must agree after normalization.",
        )
    )

    validations.append(
        validation_row(
            "FOUR_OPERATIONAL_WORK_TYPES",
            "PASS"
            if actual_work_types == expected_work_types
            else "FAIL",
            sorted(actual_work_types),
            sorted(expected_work_types),
            "Step 13 must use exactly the approved four operational work types.",
        )
    )

    validations.append(
        validation_row(
            "OTHER_REVIEW_REQUIRED",
            "PASS"
            if "Other" in review_values
            else "FAIL",
            sorted(review_values),
            "Other",
            "Other must not be automatically assigned to an operational work type.",
        )
    )

    validated_count = int(
        (mapping_df["mapping_status"] == "VALIDATED").sum()
    )
    review_count = int(
        (mapping_df["mapping_status"] == "REVIEW_REQUIRED").sum()
    )

    validations.append(
        validation_row(
            "EXPECTED_VALIDATED_MAPPING_ROWS",
            "PASS" if validated_count == 14 else "FAIL",
            validated_count,
            14,
            (
                "There are 7 non-Other source values and each appears in "
                "both Step 8 and Step 10, giving 14 validated source/type rows."
            ),
        )
    )

    validations.append(
        validation_row(
            "EXPECTED_REVIEW_MAPPING_ROWS",
            "PASS" if review_count == 2 else "FAIL",
            review_count,
            2,
            "Other appears once in Step 8 and once in Step 10.",
        )
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mapping_df.to_csv(
        FINAL_MAPPING_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_df = pd.DataFrame(
        validations,
        columns=[
            "check_id",
            "status",
            "actual_value",
            "expected_value",
            "notes",
        ],
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "step": "13.1_final_work_type_mapping",
        "read_only_sources": True,
        "project_root": str(PROJECT_ROOT),
        "step8_file": str(STEP8_FILE),
        "step10_file": str(STEP10_FILE),
        "approved_step13_operational_scope": [
            "ROAD",
            "WATER",
            "GARBAGE",
            "ELECTRICITY",
        ],
        "step9_yolo_classes_unchanged": [
            "Pothole",
            "Garbage Accumulation",
            "Waterlogging",
            "Road Damage",
        ],
        "source_categories": categories,
        "source_issue_types": issue_types,
        "source_join": {
            "step8_rows": int(len(step8)),
            "step10_rows": int(len(step10)),
            "common_complaint_ids": int(len(both)),
            "step8_only": only_step8,
            "step10_only": only_step10,
            "category_issue_type_mismatches": int(len(mismatches)),
        },
        "mapping_rows": {
            "validated": validated_count,
            "review_required": review_count,
            "total": int(len(mapping_df)),
        },
        "other_policy": (
            "Other remains REVIEW_REQUIRED and is excluded from executable "
            "Step 13 jobs until manually classified."
        ),
        "outputs": {
            "final_mapping": str(FINAL_MAPPING_FILE),
            "validation": str(VALIDATION_FILE),
        },
        "gate": {
            "status": (
                "PASS"
                if all(row["status"] == "PASS" for row in validations)
                else "FAIL"
            ),
            "next_step": (
                "Build eligible_jobs.csv only after this mapping validation passes."
            ),
        },
    }

    SUMMARY_FILE.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("-" * 80)
    print("FINAL APPROVED OPERATIONAL SCOPE")
    print("-" * 80)
    print("ROAD")
    print("WATER")
    print("GARBAGE")
    print("ELECTRICITY")

    print()
    print("-" * 80)
    print("OBSERVED SOURCE VALUES")
    print("-" * 80)
    for value in categories:
        key = normalize(value)
        rule = APPROVED_MAPPING.get(key)
        if rule is None:
            print(f"{value:25} -> REVIEW_REQUIRED")
        elif key == "other":
            print(f"{value:25} -> REVIEW_REQUIRED")
        else:
            print(f"{value:25} -> {rule['work_type']}")

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validations:
        print(
            f"{row['check_id']:35} : {row['status']:4} | "
            f"actual={row['actual_value']}"
        )

    overall = summary["gate"]["status"]

    print()
    print("=" * 80)
    print(f"STEP 13.1 FINAL WORK-TYPE MAPPING GATE: {overall}")
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(f"Final mapping : {FINAL_MAPPING_FILE}")
    print(f"Validation    : {VALIDATION_FILE}")
    print(f"Summary       : {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
