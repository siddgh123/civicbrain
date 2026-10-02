from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


# ============================================================================
# CIVICBRAIN STEP 13.2 — RESOURCE NORMALIZATION
#
# Purpose:
#   Normalize the existing Step 10 resource estimates attached to the
#   canonical Step 13 eligible_jobs.csv dataset.
#
# Inputs:
#   data/optimization/jobs/eligible_jobs.csv
#
# Existing Step 10 source fields already present in eligible_jobs.csv:
#   estimated_workers
#   estimated_duration_hours
#   total_cost
#   required_equipment
#   work_type
#
# Outputs:
#   data/optimization/jobs/normalized_job_resources.csv
#   data/optimization/config/equipment_catalog.csv
#   data/optimization/jobs/resource_normalization_validation.csv
#   data/optimization/jobs/resource_normalization_summary.json
#
# IMPORTANT:
#   - No database writes.
#   - No Step 10 retraining.
#   - No manual per-row edits.
#   - No new operational work types.
#   - Existing four-category Step 13 scope is preserved:
#       ROAD, WATER, GARBAGE, ELECTRICITY
#   - This script normalizes equipment strings reproducibly.
#   - Equipment availability is NOT invented here.
#   - Team master is intentionally NOT created in this step.
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

INPUT_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "eligible_jobs.csv"
)

OUTPUT_JOBS_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "normalized_job_resources.csv"
)

EQUIPMENT_CATALOG_FILE = (
    DATA_DIR
    / "optimization"
    / "config"
    / "equipment_catalog.csv"
)

VALIDATION_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "resource_normalization_validation.csv"
)

SUMMARY_JSON = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "resource_normalization_summary.json"
)

APPROVED_WORK_TYPES = {
    "ROAD",
    "WATER",
    "GARBAGE",
    "ELECTRICITY",
}


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_equipment_token(value: str) -> str:
    value = value.strip().lower()

    value = value.replace("&", " and ")
    value = value.replace("/", " ")
    value = value.replace("-", " ")

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Stable token representation for common separator variants.
    replacements = {
        "road cutter": "road_cutter",
        "plate compactor": "plate_compactor",
        "water pump": "water_pump",
        "dewatering pump": "dewatering_pump",
        "garbage truck": "garbage_truck",
        "waste truck": "garbage_truck",
        "tipper truck": "tipper_truck",
        "ladder": "ladder",
        "tool kit": "tool_kit",
        "hand tools": "hand_tools",
    }

    if value in replacements:
        return replacements[value]

    return value.replace(" ", "_")


def normalize_equipment_string(value: object) -> str:
    raw = clean_text(value)

    if not raw:
        return ""

    # Support common separators produced by Step 10:
    # comma, semicolon, pipe, slash and "and".
    parts = re.split(r"\s*(?:,|;|\||/)\s*|\s+\band\b\s+", raw)

    tokens = []

    for part in parts:
        token = normalize_equipment_token(part)
        if token:
            tokens.append(token)

    # Stable order + duplicate removal.
    tokens = sorted(set(tokens))

    return "|".join(tokens)


def load_input() -> pd.DataFrame:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Required Step 13.1 output not found:\n{INPUT_FILE}"
        )

    try:
        df = pd.read_csv(INPUT_FILE)
    except Exception as exc:
        raise RuntimeError(
            f"Could not read eligible_jobs.csv:\n{exc}"
        ) from exc

    required = {
        "complaint_id",
        "job_id",
        "work_type",
        "workers_required",
        "service_duration_hours",
        "estimated_cost",
        "required_equipment",
        "priority_score",
        "eligibility_status",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "eligible_jobs.csv is missing required columns: "
            + ", ".join(sorted(missing))
        )

    return df


def validation_row(
    check_id: str,
    status: str,
    actual: object,
    expected: object,
    notes: str,
) -> dict:
    return {
        "check_id": check_id,
        "status": status,
        "actual_value": str(actual),
        "expected_value": str(expected),
        "notes": notes,
    }


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.2 — RESOURCE NORMALIZATION")
    print("=" * 80)

    print()
    print("READ-ONLY SOURCE")
    print("-" * 80)
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Input        : {INPUT_FILE}")
    print("Database     : NOT USED")

    df = load_input().copy()

    # Work only on executable canonical jobs.
    non_eligible = int(
        (~df["eligibility_status"].astype(str).str.strip().eq("ELIGIBLE"))
        .sum()
    )

    if non_eligible:
        raise ValueError(
            f"eligible_jobs.csv contains {non_eligible} non-eligible rows. "
            "The canonical Step 13 job file must contain executable jobs only."
        )

    df["work_type"] = (
        df["work_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    invalid_work_types = sorted(
        set(df["work_type"].dropna()) - APPROVED_WORK_TYPES
    )

    if invalid_work_types:
        raise ValueError(
            "Unexpected Step 13 work types found: "
            + ", ".join(invalid_work_types)
        )

    # ----------------------------------------------------------------------
    # Normalize numeric resource fields
    # ----------------------------------------------------------------------

    df["workers_required"] = pd.to_numeric(
        df["workers_required"],
        errors="coerce",
    )

    df["service_duration_hours"] = pd.to_numeric(
        df["service_duration_hours"],
        errors="coerce",
    )

    df["estimated_cost"] = pd.to_numeric(
        df["estimated_cost"],
        errors="coerce",
    )

    # ----------------------------------------------------------------------
    # Normalize equipment representation
    # ----------------------------------------------------------------------

    df["required_equipment_raw"] = (
        df["required_equipment"]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    df["required_equipment"] = (
        df["required_equipment_raw"]
        .map(normalize_equipment_string)
    )

    # ----------------------------------------------------------------------
    # Build equipment catalog from observed Step 10 requirements.
    #
    # Do NOT invent quantities or availability at this stage.
    # ----------------------------------------------------------------------

    equipment_tokens = sorted(
        {
            token
            for value in df["required_equipment"]
            if value
            for token in str(value).split("|")
            if token.strip()
        }
    )

    equipment_rows = []

    for token in equipment_tokens:
        equipment_rows.append(
            {
                "equipment_type": token,
                "description": (
                    "Observed normalized equipment requirement from "
                    "existing Step 10 resource data."
                ),
                "available_quantity": "",
                "status": "TO_BE_CONFIGURED",
                "source": "step10_observed_requirement",
            }
        )

    equipment_catalog = pd.DataFrame(
        equipment_rows,
        columns=[
            "equipment_type",
            "description",
            "available_quantity",
            "status",
            "source",
        ],
    )

    # ----------------------------------------------------------------------
    # Resource validation
    # ----------------------------------------------------------------------

    validations = []

    validations.append(
        validation_row(
            "INPUT_ROW_COUNT",
            "PASS" if len(df) == 441 else "REVIEW",
            len(df),
            441,
            (
                "Expected the current Step 13.1 canonical executable-job "
                "dataset to contain 441 rows."
            ),
        )
    )

    validations.append(
        validation_row(
            "WORK_TYPE_SCOPE",
            "PASS"
            if set(df["work_type"].unique()).issubset(APPROVED_WORK_TYPES)
            else "FAIL",
            sorted(df["work_type"].unique().tolist()),
            sorted(APPROVED_WORK_TYPES),
            "Only the frozen four operational work types may remain.",
        )
    )

    validations.append(
        validation_row(
            "WORKER_VALUES",
            "PASS"
            if bool(df["workers_required"].notna().all())
            and bool(df["workers_required"].gt(0).all())
            else "FAIL",
            int(
                (
                    df["workers_required"].isna()
                    | ~df["workers_required"].gt(0)
                ).sum()
            ),
            0,
            "Every executable job must have a positive worker estimate.",
        )
    )

    validations.append(
        validation_row(
            "DURATION_VALUES",
            "PASS"
            if bool(df["service_duration_hours"].notna().all())
            and bool(df["service_duration_hours"].gt(0).all())
            else "FAIL",
            int(
                (
                    df["service_duration_hours"].isna()
                    | ~df["service_duration_hours"].gt(0)
                ).sum()
            ),
            0,
            "Every executable job must have a positive service duration.",
        )
    )

    validations.append(
        validation_row(
            "COST_VALUES",
            "PASS"
            if bool(df["estimated_cost"].notna().all())
            and bool(df["estimated_cost"].ge(0).all())
            else "FAIL",
            int(
                (
                    df["estimated_cost"].isna()
                    | ~df["estimated_cost"].ge(0)
                ).sum()
            ),
            0,
            "Cost must be numeric and non-negative.",
        )
    )

    validations.append(
        validation_row(
            "EQUIPMENT_VALUES",
            "PASS"
            if bool(df["required_equipment"].str.strip().ne("").all())
            else "FAIL",
            int(
                df["required_equipment"]
                .str.strip()
                .eq("")
                .sum()
            ),
            0,
            "Every executable job must have an equipment representation.",
        )
    )

    validations.append(
        validation_row(
            "JOB_ID_UNIQUENESS",
            "PASS"
            if int(df["job_id"].duplicated().sum()) == 0
            else "FAIL",
            int(df["job_id"].duplicated().sum()),
            0,
            "Canonical jobs must be unique.",
        )
    )

    # Verify normalization is deterministic.
    normalized_twice = (
        df["required_equipment_raw"]
        .map(normalize_equipment_string)
    )

    validations.append(
        validation_row(
            "EQUIPMENT_NORMALIZATION_DETERMINISTIC",
            "PASS"
            if bool(
                normalized_twice.eq(df["required_equipment"]).all()
            )
            else "FAIL",
            int(
                (~normalized_twice.eq(df["required_equipment"])).sum()
            ),
            0,
            "Repeated normalization must produce identical output.",
        )
    )

    validation_df = pd.DataFrame(validations)

    overall_pass = bool(
        validation_df["status"].eq("PASS").all()
    )

    # ----------------------------------------------------------------------
    # Output columns
    # ----------------------------------------------------------------------

    output_columns = [
        "complaint_id",
        "job_id",
        "work_type",
        "priority_score",
        "priority_level",
        "workers_required",
        "service_duration_hours",
        "estimated_cost",
        "required_equipment",
        "required_equipment_raw",
        "latitude",
        "longitude",
        "duplicate_status",
        "is_duplicate_child",
        "status",
        "submitted_at",
    ]

    missing_output_columns = [
        column for column in output_columns
        if column not in df.columns
    ]

    if missing_output_columns:
        raise ValueError(
            "Required output columns are missing from eligible_jobs.csv: "
            + ", ".join(missing_output_columns)
        )

    normalized_jobs = df[output_columns].copy()

    # ----------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------

    work_type_counts = (
        normalized_jobs["work_type"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    equipment_frequency = {}

    for value in normalized_jobs["required_equipment"]:
        for token in str(value).split("|"):
            token = token.strip()
            if token:
                equipment_frequency[token] = (
                    equipment_frequency.get(token, 0) + 1
                )

    equipment_frequency = dict(
        sorted(
            equipment_frequency.items(),
            key=lambda item: item[0],
        )
    )

    summary = {
        "step": "13.2_resource_normalization",
        "project_root": str(PROJECT_ROOT),
        "input": str(INPUT_FILE),
        "read_only": True,
        "database_used": False,
        "approved_work_types": sorted(APPROVED_WORK_TYPES),
        "rows": {
            "input": int(len(df)),
            "normalized": int(len(normalized_jobs)),
        },
        "work_type_counts": {
            key: int(value)
            for key, value in work_type_counts.items()
        },
        "resource_statistics": {
            "workers_min": float(df["workers_required"].min()),
            "workers_max": float(df["workers_required"].max()),
            "duration_min_hours": float(
                df["service_duration_hours"].min()
            ),
            "duration_max_hours": float(
                df["service_duration_hours"].max()
            ),
            "cost_min": float(df["estimated_cost"].min()),
            "cost_max": float(df["estimated_cost"].max()),
        },
        "equipment": {
            "unique_normalized_equipment_types": len(
                equipment_tokens
            ),
            "frequency_by_type": equipment_frequency,
        },
        "equipment_availability_policy": (
            "Availability and quantities are intentionally left "
            "TO_BE_CONFIGURED. No equipment inventory is invented in "
            "resource normalization."
        ),
        "validation": {
            "status": "PASS" if overall_pass else "FAIL",
            "checks_total": int(len(validation_df)),
            "checks_passed": int(
                validation_df["status"].eq("PASS").sum()
            ),
            "checks_review": int(
                validation_df["status"].eq("REVIEW").sum()
            ),
            "checks_failed": int(
                validation_df["status"].eq("FAIL").sum()
            ),
        },
        "outputs": {
            "normalized_job_resources": str(OUTPUT_JOBS_FILE),
            "equipment_catalog": str(EQUIPMENT_CATALOG_FILE),
            "validation": str(VALIDATION_FILE),
        },
        "next_step": (
            "After reviewing this resource normalization, configure the "
            "Step 13 prototype team master and team-equipment capability."
        ),
    }

    OUTPUT_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EQUIPMENT_CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    normalized_jobs.to_csv(
        OUTPUT_JOBS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    equipment_catalog.to_csv(
        EQUIPMENT_CATALOG_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    SUMMARY_JSON.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ----------------------------------------------------------------------
    # Console output
    # ----------------------------------------------------------------------

    print()
    print("-" * 80)
    print("RESOURCE NORMALIZATION SUMMARY")
    print("-" * 80)
    print(f"Input jobs                  : {len(df)}")
    print(f"Normalized jobs             : {len(normalized_jobs)}")
    print(f"Unique equipment types      : {len(equipment_tokens)}")
    print()

    print("Work-type counts:")
    for work_type in sorted(APPROVED_WORK_TYPES):
        print(
            f"  {work_type:15} : "
            f"{work_type_counts.get(work_type, 0)}"
        )

    print()
    print("Equipment types observed:")
    for token in equipment_tokens:
        print(
            f"  {token:30} : "
            f"{equipment_frequency.get(token, 0)} jobs"
        )

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validations:
        print(
            f"{row['check_id']:42} : "
            f"{row['status']:5} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13.2 RESOURCE NORMALIZATION GATE: "
        + ("PASS" if overall_pass else "FAIL")
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(f"Normalized resources : {OUTPUT_JOBS_FILE}")
    print(f"Equipment catalog    : {EQUIPMENT_CATALOG_FILE}")
    print(f"Validation           : {VALIDATION_FILE}")
    print(f"Summary JSON         : {SUMMARY_JSON}")

    if not overall_pass:
        raise RuntimeError(
            "Step 13.2 resource normalization failed. "
            "Review the validation output before continuing."
        )


if __name__ == "__main__":
    main()
