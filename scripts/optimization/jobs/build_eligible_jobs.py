from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2


# ============================================================================
# CIVICBRAIN STEP 13.1 — BUILD ELIGIBLE CANONICAL JOBS
#
# Purpose:
#   Build the single source-of-truth Step 13 job dataset by combining:
#     Step 8 complaint data
#     Step 10 resource estimates
#     Step 11 frozen priority scores
#     Step 12 duplicate/master state from PostgreSQL
#     Step 13.1 final 4-category work-type mapping
#
# IMPORTANT:
#   - Do NOT rebuild or modify Step 11.
#   - Do NOT rebuild or modify Step 12.
#   - Do NOT create Step 13 database tables.
#   - Do NOT use raw 500 complaints directly in clustering.
#   - Duplicate children are NOT separate jobs.
#   - UNCERTAIN/review complaints are NOT executable jobs.
#   - "Other" remains REVIEW_REQUIRED and is excluded.
#   - Step 9 YOLO classes are preserved as evidence context only.
#   - This script reads PostgreSQL only; it performs no INSERT/UPDATE/DELETE.
#
# Correct project root:
#   C:\Users\Siddhesh\OneDrive\Desktop\CivicBrain
#
# Script location:
#   CivicBrain\scripts\optimization\jobs\build_eligible_jobs.py
#
# parents[0] = jobs
# parents[1] = optimization
# parents[2] = scripts
# parents[3] = CivicBrain
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

# --------------------------------------------------------------------------
# Existing project source files
# --------------------------------------------------------------------------

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

STEP11_FILE = (
    DATA_DIR
    / "priority"
    / "priority_scores.csv"
)

MAPPING_FILE = (
    DATA_DIR
    / "optimization"
    / "config"
    / "work_type_mapping.csv"
)

OUTPUT_DIR = DATA_DIR / "optimization" / "jobs"

ELIGIBLE_FILE = OUTPUT_DIR / "eligible_jobs.csv"
SUMMARY_FILE = OUTPUT_DIR / "eligible_jobs_summary.csv"
VALIDATION_FILE = OUTPUT_DIR / "eligible_jobs_validation.csv"
SUMMARY_JSON = OUTPUT_DIR / "eligible_jobs_summary.json"


# --------------------------------------------------------------------------
# Approved Step 13 operational scope
# --------------------------------------------------------------------------

APPROVED_WORK_TYPES = {
    "ROAD",
    "WATER",
    "GARBAGE",
    "ELECTRICITY",
}

# Frozen Step 9 classes. These are evidence/defect classes, not extra
# operational work types.
STEP9_CLASSES = {
    "Pothole",
    "Garbage Accumulation",
    "Waterlogging",
    "Road Damage",
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

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


def to_numeric_series(
    df: pd.DataFrame,
    column: str,
) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def connect_db():
    host = os.getenv("CIVICBRAIN_DB_HOST", "localhost")
    port = int(os.getenv("CIVICBRAIN_DB_PORT", "5432"))
    dbname = os.getenv("CIVICBRAIN_DB_NAME", "civicbrain")
    user = os.getenv("CIVICBRAIN_DB_USER", "postgres")
    password = os.getenv("CIVICBRAIN_DB_PASSWORD")

    if password is None:
        password = getpass.getpass(
            f"PostgreSQL password for {user}@{host}: "
        )

    try:
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        )
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL connection failed. Check PostgreSQL service "
            "and credentials."
        ) from exc


def database_complaints() -> pd.DataFrame:
    conn = connect_db()

    sql = """
        SELECT
            c.complaint_id::text AS complaint_id,
            c.status AS db_status,
            c.master_complaint_id::text AS master_complaint_id,
            c.duplicate_status,
            c.duplicate_review_required,
            c.closed_at,
            c.submitted_at,
            ST_Y(c.location) AS db_latitude,
            ST_X(c.location) AS db_longitude,
            ST_SRID(c.location) AS db_srid
        FROM public.complaints c
        ORDER BY c.complaint_id
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [description[0] for description in cur.description]

        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()


def canonical_step13_work_type(
    source_value: object,
) -> str:
    key = normalize(source_value)

    if key == "pothole":
        return "ROAD"

    if key == "road damage":
        return "ROAD"

    if key == "waterlogging":
        return "WATER"

    if key == "water leakage":
        return "WATER"

    if key == "blocked drain":
        return "WATER"

    if key == "garbage accumulation":
        return "GARBAGE"

    if key == "streetlight":
        return "ELECTRICITY"

    # "Other" and any unexpected future values stay unmapped.
    return ""


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.1 — BUILD ELIGIBLE CANONICAL JOBS")
    print("=" * 80)

    print()
    print("READ-ONLY DATABASE ACCESS")
    print("-" * 80)
    print("No INSERT / UPDATE / DELETE will be executed.")

    print()
    print("Project root :", PROJECT_ROOT)
    print("Step 8       :", STEP8_FILE)
    print("Step 10      :", STEP10_FILE)
    print("Step 11      :", STEP11_FILE)
    print("Mapping      :", MAPPING_FILE)

    # ----------------------------------------------------------------------
    # Load files
    # ----------------------------------------------------------------------

    step8 = load_csv(
        STEP8_FILE,
        "Step 8 complaint dataset",
    )

    step10 = load_csv(
        STEP10_FILE,
        "Step 10 resource dataset",
    )

    step11 = load_csv(
        STEP11_FILE,
        "Step 11 priority score dataset",
    )

    mapping = load_csv(
        MAPPING_FILE,
        "Final Step 13 work-type mapping",
    )

    # Required headers
    required_step8 = {
        "complaint_id",
        "title",
        "description",
        "category",
        "latitude",
        "longitude",
        "created_at",
        "status",
        "image_path",
        "is_synthetic",
    }

    required_step10 = {
        "complaint_id",
        "issue_type",
        "estimated_workers",
        "estimated_duration_hours",
        "total_cost",
        "required_equipment",
    }

    required_step11 = {
        "complaint_id",
        "priority_score",
        "priority_level",
    }

    required_mapping = {
        "source_value",
        "source_type",
        "work_type",
        "team_type",
        "mapping_status",
    }

    for label, df, required in [
        ("Step 8", step8, required_step8),
        ("Step 10", step10, required_step10),
        ("Step 11", step11, required_step11),
        ("work_type_mapping", mapping, required_mapping),
    ]:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"{label} missing required columns: "
                + ", ".join(sorted(missing))
            )

    # ----------------------------------------------------------------------
    # Validate final mapping itself before using it
    # ----------------------------------------------------------------------

    validated_mapping = mapping[
        mapping["mapping_status"].astype(str).str.strip().eq("VALIDATED")
    ].copy()

    invalid_mapping_work_types = set(
        validated_mapping["work_type"]
        .dropna()
        .astype(str)
        .str.strip()
    ) - APPROVED_WORK_TYPES

    if invalid_mapping_work_types:
        raise ValueError(
            "Final mapping contains invalid operational work types: "
            + ", ".join(sorted(invalid_mapping_work_types))
        )

    # Build one lookup keyed by normalized source value.
    source_lookup = {}

    for _, row in mapping.iterrows():
        source = clean_text(row["source_value"])
        key = normalize(source)

        if not key:
            continue

        # Only a validated row is allowed to create an executable mapping.
        if str(row["mapping_status"]).strip() == "VALIDATED":
            source_lookup[key] = str(row["work_type"]).strip()

    # ----------------------------------------------------------------------
    # Load current database state
    # ----------------------------------------------------------------------

    db = database_complaints()

    # DB ID cleanup
    db["complaint_id"] = (
        db["complaint_id"].astype(str).str.strip()
    )

    # ----------------------------------------------------------------------
    # Normalize source IDs
    # ----------------------------------------------------------------------

    for df in (step8, step10, step11):
        df["complaint_id"] = (
            df["complaint_id"].astype(str).str.strip()
        )

    # ----------------------------------------------------------------------
    # Source uniqueness checks
    # ----------------------------------------------------------------------

    duplicate_step8_ids = int(
        step8["complaint_id"].duplicated().sum()
    )
    duplicate_step10_ids = int(
        step10["complaint_id"].duplicated().sum()
    )
    duplicate_step11_ids = int(
        step11["complaint_id"].duplicated().sum()
    )
    duplicate_db_ids = int(
        db["complaint_id"].duplicated().sum()
    )

    if any(
        value != 0
        for value in [
            duplicate_step8_ids,
            duplicate_step10_ids,
            duplicate_step11_ids,
            duplicate_db_ids,
        ]
    ):
        raise ValueError(
            "Duplicate complaint IDs detected in one or more inputs. "
            "Step 13 requires one row per complaint."
        )

    # ----------------------------------------------------------------------
    # Merge:
    # Step 8 + Step 10 + Step 11 + DB state
    # ----------------------------------------------------------------------

    jobs = (
        step8[
            [
                "complaint_id",
                "title",
                "description",
                "category",
                "latitude",
                "longitude",
                "created_at",
                "status",
                "image_path",
                "is_synthetic",
            ]
        ]
        .copy()
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
            ],
            on="complaint_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            step11[
                [
                    "complaint_id",
                    "priority_score",
                    "priority_level",
                ]
            ],
            on="complaint_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            db,
            on="complaint_id",
            how="left",
            validate="one_to_one",
        )
    )

    # ----------------------------------------------------------------------
    # Coverage checks
    # ----------------------------------------------------------------------

    missing_step10_join = int(jobs["issue_type"].isna().sum())
    missing_step11_join = int(jobs["priority_score"].isna().sum())
    missing_db_join = int(jobs["db_status"].isna().sum())

    if missing_step10_join:
        raise ValueError(
            f"{missing_step10_join} complaints have no Step 10 resource row."
        )

    if missing_step11_join:
        raise ValueError(
            f"{missing_step11_join} complaints have no Step 11 priority row."
        )

    if missing_db_join:
        raise ValueError(
            f"{missing_db_join} complaints have no current PostgreSQL row."
        )

    # ----------------------------------------------------------------------
    # Normalize fields
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------

    jobs["title"] = jobs["title"].map(clean_text)
    jobs["description"] = jobs["description"].map(clean_text)
    jobs["category"] = jobs["category"].map(clean_text)
    jobs["issue_type"] = jobs["issue_type"].map(clean_text)
    jobs["status"] = jobs["db_status"].map(clean_text)
    jobs["source_status"] = jobs["status"].copy()

    jobs["work_type"] = jobs["category"].map(
        lambda value: source_lookup.get(
            normalize(value),
            "",
        )
    )

    # Require Step 8 and Step 10 issue category agreement.
    category_issue_mismatch = (
        jobs.apply(
            lambda row: normalize(row["category"])
            != normalize(row["issue_type"]),
            axis=1,
        )
    )

    # Resource normalization
    jobs["workers_required"] = to_numeric_series(
        jobs,
        "estimated_workers",
    )

    jobs["service_duration_hours"] = to_numeric_series(
        jobs,
        "estimated_duration_hours",
    )

    jobs["estimated_cost"] = to_numeric_series(
        jobs,
        "total_cost",
    )

    jobs["required_equipment"] = (
        jobs["required_equipment"]
        .fillna("")
        .astype(str)
        .map(clean_text)
    )

    jobs["priority_score"] = to_numeric_series(
        jobs,
        "priority_score",
    )

    jobs["latitude_db"] = pd.to_numeric(
        jobs["db_latitude"],
        errors="coerce",
    )
    jobs["longitude_db"] = pd.to_numeric(
        jobs["db_longitude"],
        errors="coerce",
    )

    jobs["srid_valid"] = (
        pd.to_numeric(jobs["db_srid"], errors="coerce").eq(4326)
    )

    # Prefer the verified PostGIS coordinates for operational use.
    jobs["latitude"] = jobs["latitude_db"]
    jobs["longitude"] = jobs["longitude_db"]

    jobs["location_valid"] = (
        jobs["latitude"].notna()
        & jobs["longitude"].notna()
        & jobs["latitude"].between(-90, 90, inclusive="both")
        & jobs["longitude"].between(-180, 180, inclusive="both")
        & jobs["srid_valid"]
    )

    # ----------------------------------------------------------------------
    # Step 12 duplicate/master interpretation
    # ----------------------------------------------------------------------

    jobs["master_complaint_id"] = (
        jobs["master_complaint_id"]
        .where(jobs["master_complaint_id"].notna(), "")
        .astype(str)
        .str.strip()
    )

    # pandas may represent NaN-as-string after astype(str); normalize it.
    jobs["master_complaint_id"] = jobs["master_complaint_id"].replace(
        {"nan": "", "None": "", "<NA>": ""},
    )

    jobs["is_duplicate_child"] = (
        jobs["master_complaint_id"].str.strip().ne("")
    )

    jobs["duplicate_status"] = (
        jobs["duplicate_status"]
        .fillna("NOT_EVALUATED")
        .astype(str)
        .str.strip()
    )

    jobs["duplicate_review_required"] = (
        jobs["duplicate_review_required"]
        .fillna(False)
        .astype(bool)
    )

    # Defensive DB-state sanity check.
    if jobs["db_status"].isna().any():
        raise RuntimeError(
            "Current PostgreSQL status is missing after the complaint join."
        )

    # Canonical job identity:
    # a root complaint represents the executable physical issue.
    jobs["job_id"] = jobs["complaint_id"]

    # ----------------------------------------------------------------------
    # Eligibility rules
    # ----------------------------------------------------------------------

    jobs["closed_completed"] = (
        jobs["closed_at"].notna()
        | jobs["status"]
        .str.upper()
        .isin({"COMPLETED", "CLOSED"})
    )

    jobs["uncertain_review"] = (
        jobs["duplicate_status"].str.upper().eq("UNCERTAIN")
        | jobs["duplicate_review_required"].eq(True)
    )

    jobs["work_type_known"] = (
        jobs["work_type"].isin(APPROVED_WORK_TYPES)
    )

    jobs["resource_fields_valid"] = (
        jobs["workers_required"].notna()
        & jobs["workers_required"].gt(0)
        & jobs["service_duration_hours"].notna()
        & jobs["service_duration_hours"].gt(0)
        & jobs["estimated_cost"].notna()
        & jobs["estimated_cost"].ge(0)
        & jobs["required_equipment"].str.strip().ne("")
    )

    jobs["priority_valid"] = (
        jobs["priority_score"].notna()
        & jobs["priority_score"].between(
            0,
            100,
            inclusive="both",
        )
        & jobs["priority_level"].notna()
        & jobs["priority_level"].astype(str).str.strip().ne("")
    )

    jobs["active_status"] = ~jobs["closed_completed"]

    # Final eligibility:
    eligible_mask = (
        jobs["location_valid"]
        & jobs["active_status"]
        & ~jobs["uncertain_review"]
        & ~jobs["is_duplicate_child"]
        & jobs["work_type_known"]
        & jobs["resource_fields_valid"]
        & jobs["priority_valid"]
        & ~category_issue_mismatch
    )

    # ----------------------------------------------------------------------
    # Assign one deterministic eligibility status/reason to every complaint
    # ----------------------------------------------------------------------

    def eligibility_reason(row) -> tuple[str, str]:
        if not bool(row["location_valid"]):
            return "EXCLUDED", "INVALID_GPS_OR_SRID"

        if bool(row["closed_completed"]):
            return "EXCLUDED", "CLOSED_OR_COMPLETED"

        if bool(row["is_duplicate_child"]):
            return "EXCLUDED", "DUPLICATE_CHILD"

        if bool(row["uncertain_review"]):
            return "EXCLUDED", "UNCERTAIN_OR_REVIEW_REQUIRED"

        if not bool(row["work_type_known"]):
            return "EXCLUDED", "UNMAPPED_WORK_TYPE"

        if not bool(row["resource_fields_valid"]):
            return "EXCLUDED", "MISSING_OR_INVALID_RESOURCE_FIELDS"

        if not bool(row["priority_valid"]):
            return "EXCLUDED", "MISSING_OR_INVALID_PRIORITY"

        if bool(category_issue_mismatch.loc[row.name]):
            return "EXCLUDED", "CATEGORY_ISSUE_TYPE_MISMATCH"

        return "ELIGIBLE", "READY_FOR_STEP13_PLANNING"

    statuses = []
    reasons = []

    for idx, row in jobs.iterrows():
        status_value, reason_value = eligibility_reason(row)
        statuses.append(status_value)
        reasons.append(reason_value)

    jobs["eligibility_status"] = statuses
    jobs["eligibility_reason"] = reasons

    # Defensive assertion: status agrees with computed mask.
    expected_status = eligible_mask.map(
        {True: "ELIGIBLE", False: "EXCLUDED"}
    )

    status_mismatch = int(
        (jobs["eligibility_status"] != expected_status).sum()
    )

    if status_mismatch:
        raise RuntimeError(
            "Internal eligibility-status mismatch detected."
        )

    # ----------------------------------------------------------------------
    # Canonical output fields
    # ----------------------------------------------------------------------

    jobs["submitted_at"] = jobs["submitted_at"].astype(str)
    jobs["closed_at"] = jobs["closed_at"].astype(str)

    jobs["review_required"] = jobs["uncertain_review"]

    jobs["is_synthetic"] = (
        jobs["is_synthetic"]
        .fillna(False)
        .astype(bool)
    )

    output_columns = [
        "complaint_id",
        "master_complaint_id",
        "job_id",
        "title",
        "description",
        "category",
        "issue_type",
        "work_type",
        "priority_score",
        "priority_level",
        "latitude",
        "longitude",
        "location_valid",
        "srid_valid",
        "is_duplicate_child",
        "duplicate_status",
        "review_required",
        "workers_required",
        "service_duration_hours",
        "estimated_cost",
        "required_equipment",
        "status",
        "source_status",
        "closed_at",
        "submitted_at",
        "image_path",
        "is_synthetic",
        "eligibility_status",
        "eligibility_reason",
    ]

    all_jobs_output = jobs[output_columns].copy()

    eligible_jobs = (
        all_jobs_output[
            all_jobs_output["eligibility_status"].eq("ELIGIBLE")
        ]
        .copy()
        .sort_values(
            ["priority_score", "complaint_id"],
            ascending=[False, True],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------------------
    # Final validation on eligible jobs
    # ----------------------------------------------------------------------

    validation_rows = []

    def add_validation(
        check_id: str,
        status: str,
        actual: object,
        expected: object,
        notes: str,
    ):
        validation_rows.append(
            {
                "check_id": check_id,
                "status": status,
                "actual_value": str(actual),
                "expected_value": str(expected),
                "notes": notes,
            }
        )

    add_validation(
        "TOTAL_COMPLAINTS",
        "PASS" if len(jobs) == 500 else "FAIL",
        len(jobs),
        500,
        "Step 13 joins the 500 complaint records.",
    )

    add_validation(
        "ELIGIBLE_JOB_ID_UNIQUENESS",
        "PASS"
        if eligible_jobs["job_id"].duplicated().sum() == 0
        else "FAIL",
        int(eligible_jobs["job_id"].duplicated().sum()),
        0,
        "Each executable job must appear exactly once.",
    )

    add_validation(
        "ELIGIBLE_WORK_TYPES",
        "PASS"
        if set(eligible_jobs["work_type"].unique()).issubset(
            APPROVED_WORK_TYPES
        )
        else "FAIL",
        sorted(eligible_jobs["work_type"].dropna().unique().tolist()),
        sorted(APPROVED_WORK_TYPES),
        "No operational type outside the four-category scope may enter.",
    )

    add_validation(
        "ELIGIBLE_DUPLICATE_CHILDREN",
        "PASS"
        if int(eligible_jobs["is_duplicate_child"].sum()) == 0
        else "FAIL",
        int(eligible_jobs["is_duplicate_child"].sum()),
        0,
        "Duplicate children are not executable jobs.",
    )

    add_validation(
        "ELIGIBLE_REVIEW_REQUIRED",
        "PASS"
        if int(eligible_jobs["review_required"].sum()) == 0
        else "FAIL",
        int(eligible_jobs["review_required"].sum()),
        0,
        "UNCERTAIN/review rows must not be scheduled.",
    )

    add_validation(
        "ELIGIBLE_LOCATION_VALID",
        "PASS"
        if bool(eligible_jobs["location_valid"].all())
        else "FAIL",
        int((~eligible_jobs["location_valid"]).sum()),
        0,
        "All eligible jobs require valid PostGIS WGS84 coordinates.",
    )

    add_validation(
        "ELIGIBLE_RESOURCE_FIELDS",
        "PASS"
        if bool(
            jobs.loc[
                jobs["eligibility_status"].eq("ELIGIBLE"),
                "resource_fields_valid",
            ].all()
        )
        else "FAIL",
        int(
            (
                ~jobs.loc[
                    jobs["eligibility_status"].eq("ELIGIBLE"),
                    "resource_fields_valid",
                ]
            ).sum()
        ),
        0,
        "Workers, duration, cost and equipment must be available.",
    )

    add_validation(
        "ELIGIBLE_PRIORITY_FIELDS",
        "PASS"
        if bool(
            jobs.loc[
                jobs["eligibility_status"].eq("ELIGIBLE"),
                "priority_valid",
            ].all()
        )
        else "FAIL",
        int(
            (
                ~jobs.loc[
                    jobs["eligibility_status"].eq("ELIGIBLE"),
                    "priority_valid",
                ]
            ).sum()
        ),
        0,
        "Frozen Step 11 priority must be present and within 0–100.",
    )

    add_validation(
        "CATEGORY_ISSUE_TYPE_MISMATCHES",
        "PASS" if int(category_issue_mismatch.sum()) == 0 else "FAIL",
        int(category_issue_mismatch.sum()),
        0,
        "Step 8 category and Step 10 issue_type must agree.",
    )

    # ----------------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------------

    exclusion_counts = (
        all_jobs_output[
            all_jobs_output["eligibility_status"].eq("EXCLUDED")
        ]["eligibility_reason"]
        .value_counts()
        .to_dict()
    )

    category_counts = (
        all_jobs_output[
            all_jobs_output["eligibility_status"].eq("ELIGIBLE")
        ]["work_type"]
        .value_counts()
        .to_dict()
    )

    priority_counts = (
        all_jobs_output[
            all_jobs_output["eligibility_status"].eq("ELIGIBLE")
        ]["priority_level"]
        .value_counts()
        .to_dict()
    )

    summary_rows = [
        {
            "metric": "total_complaints",
            "value": len(jobs),
        },
        {
            "metric": "eligible_jobs",
            "value": len(eligible_jobs),
        },
        {
            "metric": "excluded_jobs",
            "value": len(jobs) - len(eligible_jobs),
        },
        {
            "metric": "excluded_duplicate_children",
            "value": exclusion_counts.get("DUPLICATE_CHILD", 0),
        },
        {
            "metric": "excluded_uncertain_or_review",
            "value": exclusion_counts.get(
                "UNCERTAIN_OR_REVIEW_REQUIRED",
                0,
            ),
        },
        {
            "metric": "excluded_closed_or_completed",
            "value": exclusion_counts.get(
                "CLOSED_OR_COMPLETED",
                0,
            ),
        },
        {
            "metric": "excluded_invalid_gps",
            "value": exclusion_counts.get(
                "INVALID_GPS_OR_SRID",
                0,
            ),
        },
        {
            "metric": "excluded_unmapped_work_types",
            "value": exclusion_counts.get(
                "UNMAPPED_WORK_TYPE",
                0,
            ),
        },
        {
            "metric": "excluded_missing_or_invalid_resource_fields",
            "value": exclusion_counts.get(
                "MISSING_OR_INVALID_RESOURCE_FIELDS",
                0,
            ),
        },
        {
            "metric": "excluded_missing_or_invalid_priority",
            "value": exclusion_counts.get(
                "MISSING_OR_INVALID_PRIORITY",
                0,
            ),
        },
        {
            "metric": "excluded_category_issue_type_mismatch",
            "value": exclusion_counts.get(
                "CATEGORY_ISSUE_TYPE_MISMATCH",
                0,
            ),
        },
        {
            "metric": "work_type_road",
            "value": category_counts.get("ROAD", 0),
        },
        {
            "metric": "work_type_water",
            "value": category_counts.get("WATER", 0),
        },
        {
            "metric": "work_type_garbage",
            "value": category_counts.get("GARBAGE", 0),
        },
        {
            "metric": "work_type_electricity",
            "value": category_counts.get("ELECTRICITY", 0),
        },
        {
            "metric": "standalone_candidates",
            "value": "DETERMINED_DURING_CLUSTERING",
        },
    ]

    summary_df = pd.DataFrame(
        summary_rows,
        columns=["metric", "value"],
    )

    # ----------------------------------------------------------------------
    # Write outputs
    # ----------------------------------------------------------------------

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    eligible_jobs.to_csv(
        ELIGIBLE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary_df.to_csv(
        SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_df = pd.DataFrame(
        validation_rows,
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

    validation_pass = bool(
        (validation_df["status"] == "PASS").all()
    )

    summary_json = {
        "step": "13.1_build_eligible_jobs",
        "read_only_database": True,
        "project_root": str(PROJECT_ROOT),
        "source_files": {
            "step8": str(STEP8_FILE),
            "step10": str(STEP10_FILE),
            "step11": str(STEP11_FILE),
            "work_type_mapping": str(MAPPING_FILE),
        },
        "approved_work_types": sorted(APPROVED_WORK_TYPES),
        "step9_classes_unchanged": sorted(STEP9_CLASSES),
        "counts": {
            "total_complaints": int(len(jobs)),
            "eligible_jobs": int(len(eligible_jobs)),
            "excluded_jobs": int(len(jobs) - len(eligible_jobs)),
        },
        "exclusion_counts": exclusion_counts,
        "eligible_work_type_counts": category_counts,
        "eligible_priority_level_counts": priority_counts,
        "outputs": {
            "eligible_jobs": str(ELIGIBLE_FILE),
            "summary_csv": str(SUMMARY_FILE),
            "validation_csv": str(VALIDATION_FILE),
        },
        "gate": {
            "status": "PASS" if validation_pass else "FAIL",
            "next_step": (
                "Proceed to Step 13.2 team/resource normalization and "
                "team master only after this output is reviewed."
            ),
        },
    }

    SUMMARY_JSON.write_text(
        json.dumps(
            summary_json,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ----------------------------------------------------------------------
    # Console report
    # ----------------------------------------------------------------------

    print()
    print("-" * 80)
    print("ELIGIBLE JOB SUMMARY")
    print("-" * 80)
    print(f"Total complaints              : {len(jobs)}")
    print(f"Eligible jobs                 : {len(eligible_jobs)}")
    print(f"Excluded jobs                 : {len(jobs) - len(eligible_jobs)}")
    print()

    print("Eligible work types:")
    for work_type in sorted(APPROVED_WORK_TYPES):
        print(
            f"  {work_type:15} : "
            f"{category_counts.get(work_type, 0)}"
        )

    print()
    print("Exclusion reasons:")
    for reason, count in sorted(exclusion_counts.items()):
        print(f"  {reason:35} : {count}")

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validation_rows:
        print(
            f"{row['check_id']:38} : "
            f"{row['status']:4} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13.1 ELIGIBLE JOB BUILD GATE: "
        + ("PASS" if validation_pass else "FAIL")
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(f"Eligible jobs : {ELIGIBLE_FILE}")
    print(f"Summary       : {SUMMARY_FILE}")
    print(f"Validation    : {VALIDATION_FILE}")
    print(f"Summary JSON  : {SUMMARY_JSON}")

    if not validation_pass:
        raise RuntimeError(
            "Step 13.1 eligible job validation failed. "
            "Review the validation CSV before continuing."
        )


if __name__ == "__main__":
    main()
