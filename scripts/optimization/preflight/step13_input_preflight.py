from __future__ import annotations

import getpass
import json
import os
from pathlib import Path

import pandas as pd
import psycopg2


# ============================================================================
# CIVICBRAIN STEP 13.0 — INPUT PREFLIGHT
#
# IMPORTANT PATH DECISION
# The project already has:
#   CivicBrain\data
#
# This script NEVER creates a second "data" directory.
# It uses the EXISTING:
#   CivicBrain\data
#
# Script location:
#   CivicBrain\scripts\optimization\preflight\step13_input_preflight.py
#
# Therefore:
#   parents[0] = preflight
#   parents[1] = optimization
#   parents[2] = scripts
#   parents[3] = CivicBrain
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

PREFLIGHT_DIR = DATA_DIR / "optimization" / "preflight"

CHECKS_CSV = PREFLIGHT_DIR / "step13_input_preflight.csv"
SUMMARY_JSON = PREFLIGHT_DIR / "step13_input_preflight_summary.json"


# ============================================================================
# EXACT PATHS VERIFIED FROM THE CIVICBRAIN PROJECT HISTORY
# ============================================================================

STEP8_COMPLAINT_FILE = (
    DATA_DIR
    / "complaints"
    / "verified"
    / "complaints_verified.csv"
)

STEP10_RESOURCE_FILE = (
    DATA_DIR
    / "resources"
    / "processed"
    / "resource_dataset.csv"
)

STEP11_PRIORITY_FACTOR_FILE = (
    DATA_DIR
    / "priority"
    / "priority_factor_dataset.csv"
)

STEP11_PRIORITY_SCORE_FILE = (
    DATA_DIR
    / "priority"
    / "priority_scores.csv"
)

STEP12_ENGINE_RESULTS_FILE = (
    DATA_DIR
    / "duplicates"
    / "duplicate_engine_results.csv"
)

STEP12_ENGINE_CONFIG_FILE = (
    DATA_DIR
    / "duplicates"
    / "duplicate_engine_config.json"
)

# Step 12 support outputs. These are useful for audit/reproducibility.
STEP12_SUPPORT_FILES = [
    DATA_DIR / "duplicates" / "candidate_pairs.csv",
    DATA_DIR / "duplicates" / "duplicate_benchmark.csv",
    DATA_DIR / "duplicates" / "duplicate_benchmark_config.json",
    DATA_DIR / "duplicates" / "duplicate_benchmark_v2.csv",
    DATA_DIR / "duplicates" / "duplicate_benchmark_v2_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_benchmark_v2_config.json",
    DATA_DIR / "duplicates" / "duplicate_text_similarity.csv",
    DATA_DIR / "duplicates" / "duplicate_feature_analysis.csv",
    DATA_DIR / "duplicates" / "duplicate_feature_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_combination_evaluation.csv",
    DATA_DIR / "duplicates" / "duplicate_selected_config.json",
    DATA_DIR / "duplicates" / "duplicate_stability_evaluation.csv",
    DATA_DIR / "duplicates" / "duplicate_stability_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_stability_config.json",
    DATA_DIR / "duplicates" / "duplicate_time_window_evaluation.csv",
    DATA_DIR / "duplicates" / "duplicate_time_window_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_time_window_config.json",
    DATA_DIR / "duplicates" / "duplicate_threshold_evaluation.csv",
    DATA_DIR / "duplicates" / "duplicate_threshold_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_final_threshold_config.json",
    DATA_DIR / "duplicates" / "duplicate_nested_threshold_evaluation.csv",
    DATA_DIR / "duplicates" / "duplicate_nested_threshold_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_nested_threshold_config.json",
    DATA_DIR / "duplicates" / "duplicate_edge_case_validation.csv",
    DATA_DIR / "duplicates" / "duplicate_edge_case_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_3state_config.json",
    DATA_DIR / "duplicates" / "duplicate_master_issue_validation.csv",
    DATA_DIR / "duplicates" / "duplicate_master_issue_summary.csv",
    DATA_DIR / "duplicates" / "duplicate_master_issue_config.json",
]

# Step 9 final classes were frozen earlier in the project.
STEP9_CLASSES = {
    0: "Pothole",
    1: "Garbage Accumulation",
    2: "Waterlogging",
    3: "Road Damage",
}


def add_check(
    checks: list[dict],
    check_id: str,
    category: str,
    status: str,
    actual_value: object,
    notes: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "category": category,
            "status": status,
            "actual_value": str(actual_value),
            "notes": notes,
        }
    )


def validate_project_root() -> None:
    expected = [PROJECT_ROOT, DATA_DIR, SCRIPTS_DIR]

    missing = [
        path
        for path in expected
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Project root/path validation failed.\n"
            + "\n".join(
                f"Missing: {path}"
                for path in missing
            )
            + f"\nResolved PROJECT_ROOT: {PROJECT_ROOT}"
        )


def read_csv(
    path: Path,
    checks: list[dict],
    check_id: str,
    expected_columns: list[str] | None = None,
) -> pd.DataFrame | None:
    if not path.exists():
        add_check(
            checks,
            check_id,
            "file",
            "MISSING",
            path,
            "Expected file does not exist.",
        )
        return None

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        add_check(
            checks,
            check_id,
            "file",
            "FAIL",
            path,
            f"CSV could not be read: {exc}",
        )
        return None

    add_check(
        checks,
        check_id,
        "file",
        "PASS",
        f"{path} | rows={len(df)}",
        "CSV loaded successfully.",
    )

    if expected_columns:
        missing = [
            column
            for column in expected_columns
            if column not in df.columns
        ]

        add_check(
            checks,
            f"{check_id}_COLUMNS",
            "schema",
            "PASS" if not missing else "FAIL",
            list(df.columns),
            (
                "All expected columns are present."
                if not missing
                else
                "Missing columns: " + ", ".join(missing)
            ),
        )

    return df


def check_unique_ids(
    df: pd.DataFrame,
    column: str,
    checks: list[dict],
    check_id: str,
    label: str,
) -> None:
    if column not in df.columns:
        return

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    duplicates = int(values.duplicated().sum())

    add_check(
        checks,
        check_id,
        "data_quality",
        "PASS" if duplicates == 0 else "FAIL",
        duplicates,
        f"{label}: duplicated {column} values.",
    )


def connect_db():
    host = os.getenv(
        "CIVICBRAIN_DB_HOST",
        "localhost",
    )
    port = int(
        os.getenv(
            "CIVICBRAIN_DB_PORT",
            "5432",
        )
    )
    dbname = os.getenv(
        "CIVICBRAIN_DB_NAME",
        "civicbrain",
    )
    user = os.getenv(
        "CIVICBRAIN_DB_USER",
        "postgres",
    )
    password = os.getenv(
        "CIVICBRAIN_DB_PASSWORD"
    )

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
            "PostgreSQL connection failed. "
            "Check PostgreSQL service and credentials."
        ) from exc


def database_preflight(
    connection,
    checks: list[dict],
) -> dict:
    summary: dict = {}

    with connection.cursor() as cur:

        # ------------------------------------------------------------------
        # Database identity
        # ------------------------------------------------------------------
        cur.execute(
            "SELECT current_database(), current_user"
        )
        db_name, db_user = cur.fetchone()

        summary["database"] = db_name
        summary["database_user"] = db_user

        add_check(
            checks,
            "DB_IDENTITY",
            "database",
            "PASS",
            f"{db_name} / {db_user}",
            "Database connection successful.",
        )

        # ------------------------------------------------------------------
        # Complaints count
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.complaints
            """
        )
        complaint_count = int(cur.fetchone()[0])

        summary["complaint_count"] = complaint_count

        add_check(
            checks,
            "DB_COMPLAINT_COUNT",
            "database",
            "PASS" if complaint_count == 500 else "REVIEW",
            complaint_count,
            "Step 8 database contains the 500 synthetic complaints.",
        )

        # ------------------------------------------------------------------
        # Complaint operational status
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT status, COUNT(*)
            FROM public.complaints
            GROUP BY status
            ORDER BY status
            """
        )
        statuses = cur.fetchall()

        status_dict = {
            str(status): int(count)
            for status, count in statuses
        }

        summary["complaint_status_counts"] = status_dict

        add_check(
            checks,
            "DB_COMPLAINT_STATUSES",
            "eligibility",
            "PASS",
            status_dict,
            (
                "Actual values are reported here. "
                "Step 13 must not invent a VERIFIED/ASSIGNABLE "
                "status if it does not exist in this database."
            ),
        )

        # ------------------------------------------------------------------
        # Complaint location
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE location IS NULL
                ),
                COUNT(*) FILTER (
                    WHERE location IS NOT NULL
                      AND ST_SRID(location) <> 4326
                ),
                COUNT(*) FILTER (
                    WHERE location IS NOT NULL
                      AND (
                          ST_X(location) < -180
                          OR ST_X(location) > 180
                          OR ST_Y(location) < -90
                          OR ST_Y(location) > 90
                      )
                )
            FROM public.complaints
            """
        )

        null_location, wrong_srid, invalid_coordinates = (
            cur.fetchone()
        )

        location_ok = (
            null_location == 0
            and wrong_srid == 0
            and invalid_coordinates == 0
        )

        summary["location_checks"] = {
            "null_location": int(null_location),
            "wrong_srid": int(wrong_srid),
            "invalid_coordinates": int(
                invalid_coordinates
            ),
        }

        add_check(
            checks,
            "DB_LOCATION_VALIDITY",
            "geospatial",
            "PASS" if location_ok else "FAIL",
            summary["location_checks"],
            "Step 13 route jobs require usable coordinates.",
        )

        # ------------------------------------------------------------------
        # Step 12 complaint-level state
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT duplicate_status, COUNT(*)
            FROM public.complaints
            GROUP BY duplicate_status
            ORDER BY duplicate_status
            """
        )

        duplicate_status_rows = cur.fetchall()

        duplicate_status = {
            str(status): int(count)
            for status, count in duplicate_status_rows
        }

        summary["duplicate_status"] = duplicate_status

        add_check(
            checks,
            "DB_DUPLICATE_STATUS",
            "step12",
            "PASS",
            duplicate_status,
            (
                "Informational only. A duplicate pair may mark both "
                "complaints as DUPLICATE while only the child receives "
                "master_complaint_id."
            ),
        )

        # ------------------------------------------------------------------
        # Step 12 relation state
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.duplicate_relation
            """
        )
        relation_count = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT decision, COUNT(*)
            FROM public.duplicate_relation
            GROUP BY decision
            ORDER BY decision
            """
        )
        relation_decisions = cur.fetchall()

        relation_dict = {
            str(decision): int(count)
            for decision, count in relation_decisions
        }

        summary["duplicate_relation_count"] = relation_count
        summary["duplicate_relation_decisions"] = (
            relation_dict
        )

        add_check(
            checks,
            "DB_DUPLICATE_RELATION",
            "step12",
            "PASS",
            (
                f"rows={relation_count} | "
                f"decisions={relation_dict}"
            ),
            (
                "Current frozen Step 12 database output. "
                "Do not retune it in Step 13."
            ),
        )

        # ------------------------------------------------------------------
        # Master/review integrity
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE master_complaint_id IS NOT NULL
                ),
                COUNT(*) FILTER (
                    WHERE duplicate_review_required = TRUE
                )
            FROM public.complaints
            """
        )

        with_master, review_required = cur.fetchone()

        summary["complaints_with_master"] = int(
            with_master
        )
        summary["complaints_requiring_review"] = int(
            review_required
        )

        add_check(
            checks,
            "DB_MASTER_LINK_COUNT",
            "step12",
            "PASS",
            with_master,
            "Complaint rows with a master_complaint_id.",
        )

        add_check(
            checks,
            "DB_REVIEW_FLAG_COUNT",
            "step12",
            "PASS",
            review_required,
            "Complaint rows requiring review.",
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.complaints c
            LEFT JOIN public.complaints m
              ON m.complaint_id = c.master_complaint_id
            WHERE c.master_complaint_id IS NOT NULL
              AND m.complaint_id IS NULL
            """
        )

        invalid_master_links = int(
            cur.fetchone()[0]
        )

        add_check(
            checks,
            "DB_INVALID_MASTER_LINKS",
            "integrity",
            "PASS"
            if invalid_master_links == 0
            else "FAIL",
            invalid_master_links,
            "Must be zero.",
        )

        cur.execute(
            """
            SELECT COUNT(*)
            FROM public.duplicate_relation
            WHERE decision = 'UNCERTAIN'
              AND (
                  review_required <> TRUE
                  OR master_complaint_id IS NOT NULL
              )
            """
        )

        unsafe_uncertain = int(
            cur.fetchone()[0]
        )

        add_check(
            checks,
            "DB_UNSAFE_UNCERTAIN",
            "integrity",
            "PASS" if unsafe_uncertain == 0 else "FAIL",
            unsafe_uncertain,
            "UNCERTAIN must remain review-only.",
        )

        # ------------------------------------------------------------------
        # Step 12 required objects
        # ------------------------------------------------------------------
        cur.execute(
            """
            SELECT
                to_regclass('public.duplicate_relation'),
                to_regclass('public.v_duplicate_review_queue')
            """
        )

        relation_table, review_view = cur.fetchone()

        objects_ok = (
            relation_table is not None
            and review_view is not None
        )

        add_check(
            checks,
            "DB_STEP12_OBJECTS",
            "database",
            "PASS" if objects_ok else "FAIL",
            (
                f"duplicate_relation={relation_table} | "
                f"review_view={review_view}"
            ),
            "Required Step 12 dependency objects.",
        )

    return summary


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.0 — INPUT PREFLIGHT")
    print("=" * 80)

    print()
    print("READ-ONLY")
    print("-" * 80)
    print(
        "This script does not create, alter, insert, update or delete "
        "database data."
    )

    validate_project_root()

    print(
        f"Project root                : {PROJECT_ROOT}"
    )
    print(
        f"Existing data directory     : {DATA_DIR}"
    )

    checks: list[dict] = []

    # ========================================================================
    # Step 8 exact source file
    # ========================================================================
    step8 = read_csv(
        STEP8_COMPLAINT_FILE,
        checks,
        "STEP8_COMPLAINT_FILE",
        expected_columns=[
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
        ],
    )

    if step8 is not None:
        add_check(
            checks,
            "STEP8_ROW_COUNT",
            "step8",
            "PASS" if len(step8) == 500 else "REVIEW",
            len(step8),
            "Expected 500 synthetic complaints.",
        )
        check_unique_ids(
            step8,
            "complaint_id",
            checks,
            "STEP8_DUPLICATE_IDS",
            "Step 8 complaints",
        )

    # ========================================================================
    # Step 10
    # ========================================================================
    step10 = read_csv(
        STEP10_RESOURCE_FILE,
        checks,
        "STEP10_RESOURCE_FILE",
        expected_columns=[
            "complaint_id",
        ],
    )

    if step10 is not None:
        add_check(
            checks,
            "STEP10_ROW_COUNT",
            "step10",
            "PASS" if len(step10) == 500 else "REVIEW",
            len(step10),
            "Expected 500 resource-estimation records.",
        )
        check_unique_ids(
            step10,
            "complaint_id",
            checks,
            "STEP10_DUPLICATE_IDS",
            "Step 10 resource dataset",
        )

    # ========================================================================
    # Step 11 — frozen outputs
    # ========================================================================
    step11_factor = read_csv(
        STEP11_PRIORITY_FACTOR_FILE,
        checks,
        "STEP11_PRIORITY_FACTOR_FILE",
        expected_columns=[
            "complaint_id",
        ],
    )

    if step11_factor is not None:
        add_check(
            checks,
            "STEP11_FACTOR_ROW_COUNT",
            "step11",
            "PASS"
            if len(step11_factor) == 500
            else "REVIEW",
            len(step11_factor),
            "Expected 500 rows.",
        )
        check_unique_ids(
            step11_factor,
            "complaint_id",
            checks,
            "STEP11_FACTOR_DUPLICATE_IDS",
            "Step 11 factor dataset",
        )

    step11_score = read_csv(
        STEP11_PRIORITY_SCORE_FILE,
        checks,
        "STEP11_PRIORITY_SCORE_FILE",
        expected_columns=[
            "complaint_id",
            "priority_score",
            "priority_level",
        ],
    )

    if step11_score is not None:
        add_check(
            checks,
            "STEP11_SCORE_ROW_COUNT",
            "step11",
            "PASS"
            if len(step11_score) == 500
            else "REVIEW",
            len(step11_score),
            "Expected 500 frozen priority scores.",
        )
        check_unique_ids(
            step11_score,
            "complaint_id",
            checks,
            "STEP11_SCORE_DUPLICATE_IDS",
            "Step 11 priority scores",
        )

        score_values = pd.to_numeric(
            step11_score["priority_score"],
            errors="coerce",
        )

        invalid_scores = int(
            score_values.isna().sum()
        )

        invalid_scores += int(
            (
                ~score_values.between(
                    0,
                    100,
                    inclusive="both",
                )
            ).sum()
        )

        add_check(
            checks,
            "STEP11_PRIORITY_RANGE",
            "step11",
            "PASS"
            if invalid_scores == 0
            else "FAIL",
            invalid_scores,
            "Priority scores must be numeric and 0–100.",
        )

    # ========================================================================
    # Step 12 — frozen output files
    # ========================================================================
    step12_results = read_csv(
        STEP12_ENGINE_RESULTS_FILE,
        checks,
        "STEP12_ENGINE_RESULTS_FILE",
        expected_columns=[
            "complaint_id_1",
            "complaint_id_2",
            "duplicate_score",
            "decision",
        ],
    )

    if step12_results is not None:
        add_check(
            checks,
            "STEP12_ENGINE_ROW_COUNT",
            "step12",
            "PASS"
            if len(step12_results) == 109
            else "REVIEW",
            len(step12_results),
            "Expected 109 current engine relations.",
        )

        invalid_decisions = int(
            (
                ~step12_results["decision"]
                .astype(str)
                .isin(
                    [
                        "DUPLICATE",
                        "UNCERTAIN",
                        "NOT_DUPLICATE",
                    ]
                )
            ).sum()
        )

        add_check(
            checks,
            "STEP12_ENGINE_DECISIONS",
            "step12",
            "PASS"
            if invalid_decisions == 0
            else "FAIL",
            invalid_decisions,
            "All decisions must use the frozen 3-state vocabulary.",
        )

    if STEP12_ENGINE_CONFIG_FILE.exists():
        try:
            with STEP12_ENGINE_CONFIG_FILE.open(
                "r",
                encoding="utf-8",
            ) as f:
                engine_config = json.load(f)

            add_check(
                checks,
                "STEP12_ENGINE_CONFIG",
                "step12",
                "PASS",
                (
                    f"7d | "
                    f"weights="
                    f"{engine_config.get('text_weight')}/"
                    f"{engine_config.get('distance_weight')}/"
                    f"{engine_config.get('recency_weight')} | "
                    f"threshold="
                    f"{engine_config.get('duplicate_threshold')}"
                ),
                "Frozen Step 12 engine configuration.",
            )
        except Exception as exc:
            add_check(
                checks,
                "STEP12_ENGINE_CONFIG",
                "step12",
                "FAIL",
                STEP12_ENGINE_CONFIG_FILE,
                f"Could not read config: {exc}",
            )
    else:
        add_check(
            checks,
            "STEP12_ENGINE_CONFIG",
            "step12",
            "MISSING",
            STEP12_ENGINE_CONFIG_FILE,
            "Frozen Step 12 engine config not found.",
        )

    # ========================================================================
    # Step 9
    #
    # Do NOT force an exact final YOLO file path here because the project
    # history contains multiple raw/conversion locations. Step 13 only needs
    # a verified work/defect mapping; it must not invent one.
    #
    # We therefore treat Step 9 path discovery as informational.
    # ========================================================================
    yolo_root = DATA_DIR / "yolo"

    if yolo_root.exists():
        yolo_files = [
            str(
                p.relative_to(PROJECT_ROOT)
            )
            for p in yolo_root.rglob("*")
            if p.is_file()
        ]

        add_check(
            checks,
            "STEP9_YOLO_ROOT",
            "step9",
            "PASS",
            f"{yolo_root} | files={len(yolo_files)}",
            (
                "Step 9 YOLO data directory exists. "
                "Frozen classes are: "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in STEP9_CLASSES.items()
                )
            ),
        )
    else:
        add_check(
            checks,
            "STEP9_YOLO_ROOT",
            "step9",
            "INFO",
            yolo_root,
            (
                "No data/yolo directory found. This is not a Step 13 "
                "failure because Step 13 does not require a raw YOLO "
                "directory when verified work_type/category information "
                "is already available from the existing project data."
            ),
        )

    # ========================================================================
    # Support-file audit
    # ========================================================================
    existing_support = [
        str(
            path.relative_to(PROJECT_ROOT)
        )
        for path in STEP12_SUPPORT_FILES
        if path.exists()
    ]

    missing_support = [
        str(
            path.relative_to(PROJECT_ROOT)
        )
        for path in STEP12_SUPPORT_FILES
        if not path.exists()
    ]

    add_check(
        checks,
        "STEP12_SUPPORT_FILE_AUDIT",
        "audit",
        "PASS",
        (
            f"present={len(existing_support)} / "
            f"expected={len(STEP12_SUPPORT_FILES)}"
        ),
        (
            "Support-file audit only; missing historical/audit files "
            "do not invalidate the frozen database state."
            + (
                " Missing examples: "
                + ", ".join(missing_support[:5])
                if missing_support
                else ""
            )
        ),
    )

    # ========================================================================
    # Database
    # ========================================================================
    connection = None
    db_summary: dict = {}

    try:
        connection = connect_db()
        db_summary = database_preflight(
            connection,
            checks,
        )
    except Exception as exc:
        add_check(
            checks,
            "DB_CONNECTION",
            "database",
            "FAIL",
            "connection failed",
            str(exc),
        )
    finally:
        if connection is not None:
            connection.close()

    # ========================================================================
    # Overall gate
    # ========================================================================
    checks_df = pd.DataFrame(checks)

    fail_count = int(
        (checks_df["status"] == "FAIL").sum()
    )

    review_count = int(
        (checks_df["status"] == "REVIEW").sum()
    )

    missing_count = int(
        (checks_df["status"] == "MISSING").sum()
    )

    info_count = int(
        (checks_df["status"] == "INFO").sum()
    )

    pass_count = int(
        (checks_df["status"] == "PASS").sum()
    )

    # No fatal failures is the technical gate.
    overall = (
        "PASS"
        if fail_count == 0
        else "FAIL"
    )

    PREFLIGHT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    checks_df.to_csv(
        CHECKS_CSV,
        index=False,
        encoding="utf-8",
    )

    summary = {
        "step": "13.0_input_preflight",
        "project_root": str(PROJECT_ROOT),
        "existing_data_directory": str(DATA_DIR),
        "read_only": True,
        "overall_gate": overall,
        "checks_total": len(checks_df),
        "checks_passed": pass_count,
        "checks_review": review_count,
        "checks_missing": missing_count,
        "checks_info": info_count,
        "checks_failed": fail_count,
        "exact_known_paths": {
            "step8_complaints": str(
                STEP8_COMPLAINT_FILE
            ),
            "step10_resources": str(
                STEP10_RESOURCE_FILE
            ),
            "step11_priority_factor_dataset": str(
                STEP11_PRIORITY_FACTOR_FILE
            ),
            "step11_priority_scores": str(
                STEP11_PRIORITY_SCORE_FILE
            ),
            "step12_engine_results": str(
                STEP12_ENGINE_RESULTS_FILE
            ),
            "step12_engine_config": str(
                STEP12_ENGINE_CONFIG_FILE
            ),
        },
        "step9_classes": STEP9_CLASSES,
        "database_summary": db_summary,
        "next_step_gate": (
            "Proceed to Step 13.1 eligible jobs only after reviewing "
            "any REVIEW/MISSING item that affects the actual job join. "
            "INFO items alone do not block."
        ),
    }

    SUMMARY_JSON.write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("STEP 13.0 PREFLIGHT SUMMARY")
    print("=" * 80)

    print(
        f"PASS checks                  : {pass_count}"
    )
    print(
        f"REVIEW checks                : {review_count}"
    )
    print(
        f"MISSING checks               : {missing_count}"
    )
    print(
        f"INFO checks                  : {info_count}"
    )
    print(
        f"FAIL checks                  : {fail_count}"
    )

    print()
    print(
        f"Overall gate                 : {overall}"
    )

    if review_count:
        print()
        print("REVIEW ITEMS")
        print("-" * 80)
        print(
            checks_df.loc[
                checks_df["status"] == "REVIEW",
                [
                    "check_id",
                    "actual_value",
                    "notes",
                ],
            ].to_string(index=False)
        )

    if missing_count:
        print()
        print("MISSING ITEMS")
        print("-" * 80)
        print(
            checks_df.loc[
                checks_df["status"] == "MISSING",
                [
                    "check_id",
                    "actual_value",
                    "notes",
                ],
            ].to_string(index=False)
        )

    print()
    print("OUTPUT FILES")
    print("-" * 80)
    print(f"Preflight CSV                : {CHECKS_CSV}")
    print(f"Preflight summary JSON       : {SUMMARY_JSON}")

    print()
    if fail_count:
        print(
            "STOP: Fix FAIL items before continuing Step 13."
        )
    else:
        print(
            "No fatal preflight failures detected."
        )
        print(
            "Review only the items that affect the Step 13 job join."
        )

    print()
    print("=" * 80)
    print("STEP 13.0 INPUT PREFLIGHT COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
