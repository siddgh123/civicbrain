from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd


# ============================================================================
# CIVICBRAIN STEP 13 — CLUSTER SERVICEABILITY
#
# Purpose:
#   Determine whether each operational cluster can be executed by a configured
#   prototype team, and explicitly classify clusters that need splitting,
#   deferred scheduling, reassignment, or cannot be executed.
#
# Inputs:
#   data/optimization/clusters/cluster_results.csv
#   data/optimization/clusters/cluster_members.csv
#   data/optimization/jobs/normalized_job_resources.csv
#   data/optimization/teams/team_master.csv
#   data/optimization/teams/team_equipment.csv
#   data/optimization/teams/feasible_team_assignments.csv
#
# Outputs:
#   data/optimization/clusters/serviceability_results.csv
#   data/optimization/clusters/serviceability_validation.csv
#   data/optimization/clusters/serviceability_summary.json
#
# Serviceability rules:
#   SERVICEABLE
#       - compatible active team exists
#       - worker capacity is sufficient
#       - all required equipment is available
#       - total cluster service time <= 9-hour prototype shift
#       - every individual job is <= 9 hours
#
#   SPLIT
#       - compatible team/workers/equipment exist
#       - every individual job <= 9 hours
#       - total cluster service time > 9 hours
#       => cluster must be divided into multiple shift-sized execution blocks
#
#   SCHEDULE_LATER
#       - at least one individual job > 9 hours
#       => the job itself cannot fit in one prototype shift and requires
#          explicit multi-shift/deferred treatment in scheduling
#
#   REASSIGN
#       - no current team can satisfy the cluster constraints, but the
#         failure is attributable to current team configuration
#
#   UNSERVICEABLE
#       - cluster cannot be executed under the current prototype constraints
#         and there is no configured feasible team path
#
# Important:
#   - This stage does NOT perform routing.
#   - Travel time is NOT included yet.
#   - Depot coordinates remain TO_BE_CONFIGURED.
#   - No hotspot detection.
#   - No database writes.
#   - Step 11 priority formula is not changed.
#   - Step 12 duplicate logic is not changed.
#   - Existing cluster membership is not changed.
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

CLUSTER_RESULTS_FILE = (
    DATA_DIR
    / "optimization"
    / "clusters"
    / "cluster_results.csv"
)

CLUSTER_MEMBERS_FILE = (
    DATA_DIR
    / "optimization"
    / "clusters"
    / "cluster_members.csv"
)

RESOURCE_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "normalized_job_resources.csv"
)

TEAM_MASTER_FILE = (
    DATA_DIR
    / "optimization"
    / "teams"
    / "team_master.csv"
)

TEAM_EQUIPMENT_FILE = (
    DATA_DIR
    / "optimization"
    / "teams"
    / "team_equipment.csv"
)

ASSIGNMENT_FILE = (
    DATA_DIR
    / "optimization"
    / "teams"
    / "feasible_team_assignments.csv"
)

OUTPUT_DIR = DATA_DIR / "optimization" / "clusters"

SERVICEABILITY_RESULTS_FILE = (
    OUTPUT_DIR / "serviceability_results.csv"
)

VALIDATION_FILE = (
    OUTPUT_DIR / "serviceability_validation.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "serviceability_summary.json"
)

SHIFT_START = "08:00"
SHIFT_END = "17:00"
SHIFT_HOURS = 9.0

EXPECTED_ELIGIBLE_JOBS = 441
EXPECTED_CLUSTERS = 67

APPROVED_WORK_TYPES = {
    "ROAD",
    "WATER",
    "GARBAGE",
    "ELECTRICITY",
}


def normalize_equipment(value: object) -> str:
    """
    Normalize equipment labels so title-case labels from cluster outputs and
    snake_case labels from the canonical resource/team files compare safely.
    """
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    text = text.replace(";", "|")
    text = re.sub(r"\s+", " ", text)

    replacements = {
        "Joint Cutting Machine": "joint_cutting_machine",
        "Plate Compactor": "plate_compactor",
        "Drain Cleaning Tools": "drain_cleaning_tools",
        "Truck 5.5 cum per 10 MT": "truck_5_5_cum_per_10_mt",
        "Water Leakage Repair Tools": "water_leakage_repair_tools",
        "Manual Garbage Collection Tools": "manual_garbage_collection_tools",
        "Electrical Maintenance Tools": "electrical_maintenance_tools",
    }

    tokens = []

    for token in text.split("|"):
        token = token.strip()

        if not token:
            continue

        if token in replacements:
            tokens.append(replacements[token])
            continue

        snake = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            token,
        ).strip("_").lower()

        if snake:
            tokens.append(snake)

    return "|".join(sorted(set(tokens)))


def parse_equipment(value: object) -> set[str]:
    normalized = normalize_equipment(value)

    if not normalized:
        return set()

    return {
        token.strip()
        for token in normalized.split("|")
        if token.strip()
    }


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


def load_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{label} file not found:\n{path}"
        )
    return pd.read_csv(path)


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13 — CLUSTER SERVICEABILITY")
    print("=" * 80)

    print()
    print("READ-ONLY INPUTS")
    print("-" * 80)
    print(f"Cluster results : {CLUSTER_RESULTS_FILE}")
    print(f"Cluster members : {CLUSTER_MEMBERS_FILE}")
    print(f"Resources       : {RESOURCE_FILE}")
    print(f"Team master     : {TEAM_MASTER_FILE}")
    print(f"Team equipment  : {TEAM_EQUIPMENT_FILE}")
    print(f"Assignments     : {ASSIGNMENT_FILE}")
    print("Database        : NOT USED")
    print("Routing         : NOT USED")

    cluster_results = load_csv(
        CLUSTER_RESULTS_FILE,
        "cluster results",
    )

    cluster_members = load_csv(
        CLUSTER_MEMBERS_FILE,
        "cluster members",
    )

    resources = load_csv(
        RESOURCE_FILE,
        "normalized resources",
    )

    teams = load_csv(
        TEAM_MASTER_FILE,
        "team master",
    )

    team_equipment = load_csv(
        TEAM_EQUIPMENT_FILE,
        "team equipment",
    )

    assignments = load_csv(
        ASSIGNMENT_FILE,
        "feasible team assignments",
    )

    # ----------------------------------------------------------------------
    # Input validation
    # ----------------------------------------------------------------------

    required_cluster_results = {
        "cluster_id",
        "cluster_type",
        "work_type",
        "complaint_count",
        "max_internal_distance_m",
        "total_service_duration_hours",
        "max_workers_required",
        "required_equipment",
        "priority_max",
        "priority_mean",
        "estimated_cost_total",
    }

    required_members = {
        "cluster_id",
        "job_id",
        "complaint_id",
        "sequence_candidate",
    }

    required_resources = {
        "job_id",
        "complaint_id",
        "work_type",
        "workers_required",
        "service_duration_hours",
        "required_equipment",
    }

    required_teams = {
        "team_id",
        "team_type",
        "worker_capacity",
        "working_start",
        "working_end",
        "status",
    }

    required_equipment = {
        "team_id",
        "equipment_type",
        "quantity",
        "available",
    }

    for label, df, required in [
        (
            "cluster results",
            cluster_results,
            required_cluster_results,
        ),
        (
            "cluster members",
            cluster_members,
            required_members,
        ),
        (
            "normalized resources",
            resources,
            required_resources,
        ),
        (
            "team master",
            teams,
            required_teams,
        ),
        (
            "team equipment",
            team_equipment,
            required_equipment,
        ),
    ]:
        missing = required - set(df.columns)

        if missing:
            raise ValueError(
                f"{label} missing columns: "
                + ", ".join(sorted(missing))
            )

    cluster_results["cluster_id"] = (
        cluster_results["cluster_id"]
        .astype(str)
        .str.strip()
    )

    cluster_members["cluster_id"] = (
        cluster_members["cluster_id"]
        .astype(str)
        .str.strip()
    )

    cluster_members["job_id"] = (
        cluster_members["job_id"]
        .astype(str)
        .str.strip()
    )

    resources["job_id"] = (
        resources["job_id"]
        .astype(str)
        .str.strip()
    )

    resources["complaint_id"] = (
        resources["complaint_id"]
        .astype(str)
        .str.strip()
    )

    resources["work_type"] = (
        resources["work_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    resources["workers_required"] = pd.to_numeric(
        resources["workers_required"],
        errors="coerce",
    )

    resources["service_duration_hours"] = pd.to_numeric(
        resources["service_duration_hours"],
        errors="coerce",
    )

    teams["team_id"] = (
        teams["team_id"].astype(str).str.strip()
    )

    teams["team_type"] = (
        teams["team_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    teams["worker_capacity"] = pd.to_numeric(
        teams["worker_capacity"],
        errors="coerce",
    )

    teams["status"] = (
        teams["status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    team_equipment["team_id"] = (
        team_equipment["team_id"]
        .astype(str)
        .str.strip()
    )

    team_equipment["quantity"] = pd.to_numeric(
        team_equipment["quantity"],
        errors="coerce",
    )

    team_equipment["available"] = (
        team_equipment["available"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    # ----------------------------------------------------------------------
    # Base counts
    # ----------------------------------------------------------------------

    if len(cluster_results) != EXPECTED_CLUSTERS:
        raise ValueError(
            f"Expected {EXPECTED_CLUSTERS} clusters, "
            f"found {len(cluster_results)}."
        )

    member_count = len(cluster_members)

    if member_count != EXPECTED_ELIGIBLE_JOBS:
        raise ValueError(
            f"Expected {EXPECTED_ELIGIBLE_JOBS} cluster memberships, "
            f"found {member_count}."
        )

    duplicate_job_members = int(
        cluster_members["job_id"].duplicated().sum()
    )

    if duplicate_job_members != 0:
        raise ValueError(
            "A job appears in more than one cluster."
        )

    if not set(
        cluster_results["work_type"].unique()
    ).issubset(APPROVED_WORK_TYPES):
        invalid_types = sorted(
            set(cluster_results["work_type"].unique())
            - APPROVED_WORK_TYPES
        )
        raise ValueError(
            "Unsupported cluster work types: "
            + ", ".join(invalid_types)
        )

    # ----------------------------------------------------------------------
    # Team/equipment lookup
    # ----------------------------------------------------------------------

    teams_by_type: dict[str, list[dict]] = {}

    for _, row in teams.iterrows():
        teams_by_type.setdefault(
            str(row["team_type"]),
            [],
        ).append(row.to_dict())

    available_equipment_by_team: dict[str, set[str]] = {}

    for _, row in team_equipment.iterrows():
        team_id = str(row["team_id"]).strip()

        if (
            not bool(row["available"])
            or pd.isna(row["quantity"])
            or float(row["quantity"]) <= 0
        ):
            continue

        equipment = normalize_equipment(
            row["equipment_type"]
        )

        for token in parse_equipment(equipment):
            available_equipment_by_team.setdefault(
                team_id,
                set(),
            ).add(token)

    resource_by_job = resources.set_index(
        "job_id",
        drop=False,
    )

    # ----------------------------------------------------------------------
    # Calculate serviceability for every cluster.
    # ----------------------------------------------------------------------

    results = []

    for cluster_id, members in cluster_members.groupby(
        "cluster_id",
        sort=False,
    ):
        if cluster_id not in set(
            cluster_results["cluster_id"]
        ):
            raise ValueError(
                f"Cluster {cluster_id} exists in members but not results."
            )

        summary_row = cluster_results[
            cluster_results["cluster_id"].eq(cluster_id)
        ].iloc[0]

        job_ids = [
            str(job_id).strip()
            for job_id in members["job_id"]
        ]

        missing_jobs = [
            job_id
            for job_id in job_ids
            if job_id not in resource_by_job.index
        ]

        if missing_jobs:
            raise ValueError(
                f"Cluster {cluster_id} has missing resource jobs: "
                + ", ".join(missing_jobs)
            )

        job_rows = resources[
            resources["job_id"].isin(job_ids)
        ].copy()

        work_types = sorted(
            job_rows["work_type"].unique().tolist()
        )

        if len(work_types) != 1:
            raise ValueError(
                f"Cluster {cluster_id} contains multiple work types: "
                + ", ".join(work_types)
            )

        work_type = work_types[0]

        total_duration = float(
            job_rows["service_duration_hours"].sum()
        )

        max_workers = float(
            job_rows["workers_required"].max()
        )

        max_single_job_duration = float(
            job_rows["service_duration_hours"].max()
        )

        all_required_equipment: set[str] = set()

        for value in job_rows["required_equipment"]:
            all_required_equipment.update(
                parse_equipment(value)
            )

        teams_for_type = teams_by_type.get(
            work_type,
            [],
        )

        active_teams = [
            team
            for team in teams_for_type
            if str(team["status"]).upper() == "ACTIVE"
        ]

        feasible_team_ids = []

        failure_notes = []

        for team in active_teams:
            team_id = str(team["team_id"]).strip()
            capacity = float(team["worker_capacity"])

            workers_ok = (
                max_workers <= capacity
            )

            team_equipment = available_equipment_by_team.get(
                team_id,
                set(),
            )

            missing_equipment = sorted(
                all_required_equipment - team_equipment
            )

            equipment_ok = (
                len(missing_equipment) == 0
            )

            if workers_ok and equipment_ok:
                feasible_team_ids.append(team_id)
            else:
                local_reasons = []

                if not workers_ok:
                    local_reasons.append(
                        "INSUFFICIENT_WORKER_CAPACITY"
                    )

                if not equipment_ok:
                    local_reasons.append(
                        "EQUIPMENT_UNAVAILABLE:"
                        + "|".join(missing_equipment)
                    )

                failure_notes.append(
                    f"{team_id}="
                    + ",".join(local_reasons)
                )

        has_feasible_team = (
            len(feasible_team_ids) > 0
        )

        internal_distance = float(
            summary_row["max_internal_distance_m"]
        )

        radius_ok = (
            internal_distance <= 2000.0
        )

        if not radius_ok:
            raise ValueError(
                f"Cluster {cluster_id} violates the 2 km validated radius."
            )

        # ------------------------------------------------------------------
        # Classification.
        #
        # Serviceability is intentionally NOT based on travel time yet.
        # Travel enters scheduling/routing later.
        # ------------------------------------------------------------------

        if not has_feasible_team:
            if active_teams:
                status = "UNSERVICEABLE"
                reason = (
                    "No active prototype team can satisfy the "
                    "cluster worker/equipment requirements."
                )
            else:
                status = "UNSERVICEABLE"
                reason = (
                    "No active prototype team is configured for "
                    f"work type {work_type}."
                )

        elif max_single_job_duration > SHIFT_HOURS:
            status = "SCHEDULE_LATER"
            reason = (
                "At least one member job exceeds the single "
                "09-hour prototype shift; explicit multi-shift/"
                "deferred scheduling is required."
            )

        elif total_duration > SHIFT_HOURS:
            required_shift_blocks = int(
                math.ceil(total_duration / SHIFT_HOURS)
            )
            status = "SPLIT"
            reason = (
                f"Cluster total service duration is {total_duration:.2f} h "
                f"> {SHIFT_HOURS:.2f} h. Split into approximately "
                f"{required_shift_blocks} shift-sized execution blocks "
                "before scheduling."
            )

        else:
            required_shift_blocks = 1
            status = "SERVICEABLE"
            reason = (
                "Compatible active team, worker capacity and equipment "
                "are available and the cluster fits within one prototype "
                "shift before travel time."
            )

        required_shift_blocks = int(
            math.ceil(
                total_duration / SHIFT_HOURS
            )
        )

        results.append(
            {
                "cluster_id": cluster_id,
                "cluster_type": str(
                    summary_row["cluster_type"]
                ),
                "work_type": work_type,
                "complaint_count": int(
                    len(job_rows)
                ),
                "max_internal_distance_m": round(
                    internal_distance,
                    3,
                ),
                "total_service_duration_hours": round(
                    total_duration,
                    3,
                ),
                "max_workers_required": max_workers,
                "max_single_job_duration_hours": round(
                    max_single_job_duration,
                    3,
                ),
                "required_equipment": "|".join(
                    sorted(all_required_equipment)
                ),
                "feasible_team_ids": "|".join(
                    feasible_team_ids
                ),
                "feasible_team_count": int(
                    len(feasible_team_ids)
                ),
                "required_shift_blocks": required_shift_blocks,
                "shift_hours": SHIFT_HOURS,
                "hours_fit_one_shift": bool(
                    total_duration <= SHIFT_HOURS
                ),
                "individual_jobs_fit_one_shift": bool(
                    max_single_job_duration <= SHIFT_HOURS
                ),
                "workers_feasible": bool(
                    has_feasible_team
                ),
                "equipment_feasible": bool(
                    has_feasible_team
                ),
                "radius_valid": radius_ok,
                "depot_status": "TO_BE_CONFIGURED",
                "serviceability_status": status,
                "serviceability_reason": reason,
                "team_failure_notes": ";".join(
                    failure_notes
                ),
                "travel_time_included": False,
                "priority_max": float(
                    summary_row["priority_max"]
                ),
                "priority_mean": float(
                    summary_row["priority_mean"]
                ),
                "estimated_cost_total": float(
                    summary_row["estimated_cost_total"]
                ),
            }
        )

    serviceability_results = pd.DataFrame(
        results
    )

    # ----------------------------------------------------------------------
    # Integrity checks
    # ----------------------------------------------------------------------

    cluster_ids_unique = int(
        serviceability_results["cluster_id"]
        .duplicated()
        .sum()
    )

    member_total = int(
        serviceability_results["complaint_count"].sum()
    )

    invalid_status = int(
        (
            ~serviceability_results[
                "serviceability_status"
            ].isin(
                {
                    "SERVICEABLE",
                    "SPLIT",
                    "REASSIGN",
                    "SCHEDULE_LATER",
                    "UNSERVICEABLE",
                }
            )
        ).sum()
    )

    service_duration_mismatch = 0
    workers_mismatch = 0
    equipment_mismatch = 0

    for _, row in serviceability_results.iterrows():
        cluster_id = row["cluster_id"]

        members = cluster_members[
            cluster_members["cluster_id"].eq(
                cluster_id
            )
        ]

        job_rows = resources[
            resources["job_id"].isin(
                members["job_id"].astype(str)
            )
        ]

        expected_duration = float(
            job_rows["service_duration_hours"].sum()
        )

        expected_workers = float(
            job_rows["workers_required"].max()
        )

        expected_equipment: set[str] = set()

        for value in job_rows["required_equipment"]:
            expected_equipment.update(
                parse_equipment(value)
            )

        actual_equipment = set(
            parse_equipment(
                row["required_equipment"]
            )
        )

        if not math.isclose(
            float(row["total_service_duration_hours"]),
            expected_duration,
            rel_tol=0.0,
            abs_tol=0.001,
        ):
            service_duration_mismatch += 1

        if not math.isclose(
            float(row["max_workers_required"]),
            expected_workers,
            rel_tol=0.0,
            abs_tol=0.001,
        ):
            workers_mismatch += 1

        if actual_equipment != expected_equipment:
            equipment_mismatch += 1

    status_counts = (
        serviceability_results[
            "serviceability_status"
        ]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    validation_rows = []

    def add_validation(
        check_id: str,
        status: str,
        actual: object,
        expected: object,
        notes: str,
    ):
        validation_rows.append(
            validation_row(
                check_id,
                status,
                actual,
                expected,
                notes,
            )
        )

    add_validation(
        "CLUSTER_COUNT",
        "PASS"
        if len(serviceability_results) == EXPECTED_CLUSTERS
        else "FAIL",
        len(serviceability_results),
        EXPECTED_CLUSTERS,
        "Every clustering output cluster receives a serviceability result.",
    )

    add_validation(
        "CLUSTER_ID_UNIQUENESS",
        "PASS"
        if cluster_ids_unique == 0
        else "FAIL",
        cluster_ids_unique,
        0,
        "One serviceability result per cluster.",
    )

    add_validation(
        "ALL_CLUSTER_MEMBERS_ACCOUNTED",
        "PASS"
        if member_total == EXPECTED_ELIGIBLE_JOBS
        else "FAIL",
        member_total,
        EXPECTED_ELIGIBLE_JOBS,
        "All 441 eligible jobs remain represented through their clusters.",
    )

    add_validation(
        "WORK_TYPE_SCOPE",
        "PASS"
        if set(
            serviceability_results["work_type"]
        ).issubset(APPROVED_WORK_TYPES)
        else "FAIL",
        sorted(
            serviceability_results["work_type"].unique().tolist()
        ),
        sorted(APPROVED_WORK_TYPES),
        "Only the four approved operational work types are permitted.",
    )

    add_validation(
        "SERVICE_DURATION_RECOMPUTATION",
        "PASS"
        if service_duration_mismatch == 0
        else "FAIL",
        service_duration_mismatch,
        0,
        "Cluster duration equals the sum of member-job service durations.",
    )

    add_validation(
        "MAX_WORKER_RECOMPUTATION",
        "PASS"
        if workers_mismatch == 0
        else "FAIL",
        workers_mismatch,
        0,
        "Cluster worker requirement equals maximum simultaneous job workers.",
    )

    add_validation(
        "EQUIPMENT_RECOMPUTATION",
        "PASS"
        if equipment_mismatch == 0
        else "FAIL",
        equipment_mismatch,
        0,
        "Cluster equipment equals the union of member-job equipment needs.",
    )

    add_validation(
        "INTERNAL_DISTANCE_VALID",
        "PASS"
        if int(
            (~serviceability_results["radius_valid"]).sum()
        ) == 0
        else "FAIL",
        int(
            (~serviceability_results["radius_valid"]).sum()
        ),
        0,
        "Existing validated cluster geometry remains within 2 km.",
    )

    add_validation(
        "VALID_SERVICEABILITY_STATUS",
        "PASS"
        if invalid_status == 0
        else "FAIL",
        invalid_status,
        0,
        "No cluster may receive an undefined serviceability status.",
    )

    overall_pass = bool(
        pd.DataFrame(
            validation_rows
        )["status"].eq("PASS").all()
    )

    # ----------------------------------------------------------------------
    # Output files
    # ----------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    serviceability_results.to_csv(
        SERVICEABILITY_RESULTS_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_df = pd.DataFrame(
        validation_rows
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary = {
        "step": "13_serviceability",
        "project_root": str(PROJECT_ROOT),
        "read_only": True,
        "input_clusters": int(
            len(serviceability_results)
        ),
        "input_eligible_jobs": EXPECTED_ELIGIBLE_JOBS,
        "configuration": {
            "shift_start": SHIFT_START,
            "shift_end": SHIFT_END,
            "shift_hours": SHIFT_HOURS,
            "max_internal_distance_meters": 2000,
            "travel_time_included": False,
            "depot_status": "TO_BE_CONFIGURED",
        },
        "status_counts": {
            key: int(value)
            for key, value in status_counts.items()
        },
        "required_shift_blocks_total": int(
            serviceability_results[
                "required_shift_blocks"
            ].sum()
        ),
        "notes": [
            "SERVICEABLE means the cluster fits one prototype shift before travel time.",
            "SPLIT means all individual jobs fit one shift but the combined cluster does not.",
            "SCHEDULE_LATER means at least one individual job exceeds one prototype shift.",
            "Routing/travel feasibility is intentionally deferred to later phases.",
            "Cluster membership is unchanged in this serviceability phase.",
            "No depot coordinates were invented.",
        ],
        "validation": {
            "status": "PASS" if overall_pass else "FAIL",
            "checks_total": int(
                len(validation_rows)
            ),
            "checks_passed": int(
                validation_df["status"].eq("PASS").sum()
            ),
            "checks_failed": int(
                validation_df["status"].eq("FAIL").sum()
            ),
        },
        "outputs": {
            "serviceability_results": str(
                SERVICEABILITY_RESULTS_FILE
            ),
            "validation": str(
                VALIDATION_FILE
            ),
            "summary": str(
                SUMMARY_FILE
            ),
        },
        "next_step": (
            "Use SERVICEABLE clusters directly; split SPLIT clusters into "
            "shift-sized execution blocks; handle SCHEDULE_LATER jobs "
            "explicitly; then proceed to scheduling."
        ),
    }

    SUMMARY_FILE.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print("-" * 80)
    print("SERVICEABILITY SUMMARY")
    print("-" * 80)
    print(
        f"Clusters evaluated          : {len(serviceability_results)}"
    )
    print(
        f"Jobs accounted for          : {member_total}"
    )

    print()
    print("Serviceability status:")
    for status in [
        "SERVICEABLE",
        "SPLIT",
        "SCHEDULE_LATER",
        "REASSIGN",
        "UNSERVICEABLE",
    ]:
        print(
            f"  {status:18} : "
            f"{status_counts.get(status, 0)}"
        )

    print()
    print(
        f"Required shift blocks total : "
        f"{int(serviceability_results['required_shift_blocks'].sum())}"
    )

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validation_rows:
        print(
            f"{row['check_id']:35} : "
            f"{row['status']:6} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13 SERVICEABILITY GATE: "
        + ("PASS" if overall_pass else "FAIL")
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(
        f"Serviceability : {SERVICEABILITY_RESULTS_FILE}"
    )
    print(
        f"Validation     : {VALIDATION_FILE}"
    )
    print(
        f"Summary        : {SUMMARY_FILE}"
    )

    if not overall_pass:
        raise RuntimeError(
            "Serviceability validation failed. "
            "Review serviceability_validation.csv."
        )


if __name__ == "__main__":
    main()
