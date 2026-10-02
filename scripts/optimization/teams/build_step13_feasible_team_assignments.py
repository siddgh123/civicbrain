from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# ============================================================================
# CIVICBRAIN STEP 13.3/13.4 — FEASIBLE TEAM ASSIGNMENTS
#
# Purpose:
#   Evaluate which prototype team(s) can perform each canonical Step 13 job
#   BEFORE clustering and scheduling.
#
# Inputs:
#   data/optimization/jobs/normalized_job_resources.csv
#   data/optimization/teams/team_master.csv
#   data/optimization/teams/team_equipment.csv
#
# Output:
#   data/optimization/teams/feasible_team_assignments.csv
#   data/optimization/teams/feasible_team_assignments_summary.json
#   data/optimization/teams/feasible_team_assignments_validation.csv
#
# Important project rules:
#   - Four operational work types only.
#   - One prototype team is currently configured for each work type.
#   - Sequential jobs use MAX workers, not the sum of workers.
#   - Equipment must be available to the team.
#   - A single-shift service-duration feasibility check uses 08:00-17:00
#     = 9 hours as the prototype shift length.
#   - Jobs requiring > 9 service hours are NOT silently discarded.
#     They remain jobs but receive hours_feasible=FALSE and a clear reason.
#   - Depot coordinates are still TO_BE_CONFIGURED; this does not invent
#     a depot or mark the team as unavailable.
#   - No PostgreSQL writes.
#   - No Step 11 or Step 12 modifications.
#   - No hotspot detection.
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

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

OUTPUT_DIR = DATA_DIR / "optimization" / "teams"

OUTPUT_FILE = OUTPUT_DIR / "feasible_team_assignments.csv"
VALIDATION_FILE = OUTPUT_DIR / "feasible_team_assignments_validation.csv"
SUMMARY_JSON = OUTPUT_DIR / "feasible_team_assignments_summary.json"

APPROVED_WORK_TYPES = {
    "ROAD",
    "WATER",
    "GARBAGE",
    "ELECTRICITY",
}

SHIFT_START = "08:00"
SHIFT_END = "17:00"
SHIFT_HOURS = 9.0


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_equipment(value: object) -> set[str]:
    raw = clean_text(value)
    if not raw:
        return set()

    return {
        token.strip()
        for token in raw.split("|")
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


def load_inputs():
    for path, label in [
        (RESOURCE_FILE, "normalized resources"),
        (TEAM_MASTER_FILE, "team master"),
        (TEAM_EQUIPMENT_FILE, "team equipment"),
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"{label} file not found:\n{path}"
            )

    resources = pd.read_csv(RESOURCE_FILE)
    team_master = pd.read_csv(TEAM_MASTER_FILE)
    team_equipment = pd.read_csv(TEAM_EQUIPMENT_FILE)

    required_resources = {
        "complaint_id",
        "job_id",
        "work_type",
        "workers_required",
        "service_duration_hours",
        "required_equipment",
    }

    required_team_master = {
        "team_id",
        "team_type",
        "worker_capacity",
        "working_start",
        "working_end",
        "status",
    }

    required_team_equipment = {
        "team_id",
        "equipment_type",
        "quantity",
        "available",
    }

    for label, df, required in [
        ("normalized resources", resources, required_resources),
        ("team master", team_master, required_team_master),
        ("team equipment", team_equipment, required_team_equipment),
    ]:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"{label} missing required columns: "
                + ", ".join(sorted(missing))
            )

    return resources, team_master, team_equipment


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13.3 — FEASIBLE TEAM ASSIGNMENTS")
    print("=" * 80)

    print()
    print("READ-ONLY INPUTS")
    print("-" * 80)
    print(f"Resources       : {RESOURCE_FILE}")
    print(f"Team master     : {TEAM_MASTER_FILE}")
    print(f"Team equipment  : {TEAM_EQUIPMENT_FILE}")
    print("Database        : NOT USED")

    resources, teams, team_equipment = load_inputs()

    resources["work_type"] = (
        resources["work_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    teams["team_type"] = (
        teams["team_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    teams["status"] = (
        teams["status"]
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

    team_master_capacity = pd.to_numeric(
        teams["worker_capacity"],
        errors="coerce",
    )

    # ----------------------------------------------------------------------
    # Validate team master coverage before evaluating jobs.
    # ----------------------------------------------------------------------

    duplicate_team_ids = int(
        teams["team_id"].duplicated().sum()
    )

    if duplicate_team_ids:
        raise ValueError(
            f"Team master contains {duplicate_team_ids} duplicate team IDs."
        )

    work_type_team_count = (
        teams.groupby("team_type")["team_id"]
        .count()
        .to_dict()
    )

    missing_team_types = sorted(
        APPROVED_WORK_TYPES
        - set(work_type_team_count.keys())
    )

    if missing_team_types:
        raise ValueError(
            "No prototype team exists for: "
            + ", ".join(missing_team_types)
        )

    # ----------------------------------------------------------------------
    # Build equipment sets only from teams marked available.
    # ----------------------------------------------------------------------

    team_equipment["equipment_type"] = (
        team_equipment["equipment_type"]
        .fillna("")
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

    available_equipment: dict[str, set[str]] = {}

    for _, row in team_equipment.iterrows():
        if not bool(row["available"]):
            continue

        if pd.isna(row["quantity"]) or float(row["quantity"]) <= 0:
            continue

        team_id = str(row["team_id"]).strip()
        equipment_type = clean_text(row["equipment_type"])

        if not equipment_type:
            continue

        available_equipment.setdefault(team_id, set()).add(
            equipment_type
        )

    # ----------------------------------------------------------------------
    # Evaluate every job against every prototype team.
    # ----------------------------------------------------------------------

    assignment_rows = []

    for _, job in resources.iterrows():
        job_id = str(job["job_id"]).strip()
        complaint_id = str(job["complaint_id"]).strip()
        work_type = str(job["work_type"]).strip().upper()

        required_workers = float(job["workers_required"])
        service_hours = float(job["service_duration_hours"])

        required_equipment = parse_equipment(
            job["required_equipment"]
        )

        candidate_teams = teams[
            teams["team_type"].eq(work_type)
        ].copy()

        for _, team in candidate_teams.iterrows():
            team_id = str(team["team_id"]).strip()
            team_capacity = float(team_master_capacity.loc[team.name])

            work_type_compatible = (
                work_type in APPROVED_WORK_TYPES
                and str(team["team_type"]).strip().upper()
                == work_type
            )

            workers_feasible = (
                required_workers <= team_capacity
            )

            team_equipment_set = available_equipment.get(
                team_id,
                set(),
            )

            equipment_missing = sorted(
                required_equipment - team_equipment_set
            )

            equipment_feasible = (
                len(equipment_missing) == 0
            )

            hours_feasible = (
                service_hours <= SHIFT_HOURS
            )

            availability_feasible = (
                str(team["status"]).strip().upper() == "ACTIVE"
            )

            all_feasible = (
                work_type_compatible
                and workers_feasible
                and equipment_feasible
                and hours_feasible
                and availability_feasible
            )

            reasons = []

            if not work_type_compatible:
                reasons.append("WORK_TYPE_INCOMPATIBLE")

            if not workers_feasible:
                reasons.append(
                    "INSUFFICIENT_WORKER_CAPACITY"
                )

            if not equipment_feasible:
                reasons.append(
                    "EQUIPMENT_UNAVAILABLE:"
                    + "|".join(equipment_missing)
                )

            if not hours_feasible:
                reasons.append(
                    "SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT"
                )

            if not availability_feasible:
                reasons.append("TEAM_NOT_ACTIVE")

            if all_feasible:
                reason = "FEASIBLE"
            else:
                reason = ";".join(reasons)

            assignment_rows.append(
                {
                    "job_or_cluster_id": job_id,
                    "job_id": job_id,
                    "complaint_id": complaint_id,
                    "team_id": team_id,
                    "work_type": work_type,
                    "work_type_compatible": work_type_compatible,
                    "workers_required": required_workers,
                    "team_worker_capacity": team_capacity,
                    "workers_feasible": workers_feasible,
                    "required_equipment": "|".join(
                        sorted(required_equipment)
                    ),
                    "team_available_equipment": "|".join(
                        sorted(team_equipment_set)
                    ),
                    "equipment_missing": "|".join(
                        equipment_missing
                    ),
                    "equipment_feasible": equipment_feasible,
                    "service_duration_hours": service_hours,
                    "shift_hours": SHIFT_HOURS,
                    "hours_feasible": hours_feasible,
                    "availability_feasible": availability_feasible,
                    "overall_feasible": all_feasible,
                    "reason": reason,
                    "depot_status": clean_text(
                        team.get(
                            "depot_status",
                            "TO_BE_CONFIGURED",
                        )
                    ),
                    "source": clean_text(
                        team.get(
                            "source",
                            "synthetic_prototype",
                        )
                    ),
                }
            )

    assignments = pd.DataFrame(assignment_rows)

    # ----------------------------------------------------------------------
    # Every job must have at least one row in the assignment matrix.
    # ----------------------------------------------------------------------

    job_count = int(
        resources["job_id"].nunique()
    )

    assignment_job_count = int(
        assignments["job_id"].nunique()
    )

    feasible_job_count = int(
        assignments.groupby("job_id")["overall_feasible"]
        .any()
        .sum()
    )

    no_feasible_jobs = int(
        job_count - feasible_job_count
    )

    duplicate_assignment_keys = int(
        assignments.duplicated(
            subset=["job_id", "team_id"]
        ).sum()
    )

    validations = []

    validations.append(
        validation_row(
            "INPUT_JOB_COUNT",
            "PASS" if len(resources) == 441 else "FAIL",
            len(resources),
            441,
            "Current canonical Step 13 executable-job count.",
        )
    )

    validations.append(
        validation_row(
            "ASSIGNMENT_JOB_COVERAGE",
            "PASS"
            if assignment_job_count == job_count
            else "FAIL",
            assignment_job_count,
            job_count,
            "Every canonical job must be evaluated against a compatible team.",
        )
    )

    validations.append(
        validation_row(
            "APPROVED_WORK_TYPE_SCOPE",
            "PASS"
            if set(assignments["work_type"]).issubset(
                APPROVED_WORK_TYPES
            )
            else "FAIL",
            sorted(assignments["work_type"].unique().tolist()),
            sorted(APPROVED_WORK_TYPES),
            "No fifth operational work type is permitted.",
        )
    )

    validations.append(
        validation_row(
            "ASSIGNMENT_KEY_UNIQUENESS",
            "PASS"
            if duplicate_assignment_keys == 0
            else "FAIL",
            duplicate_assignment_keys,
            0,
            "One evaluation row per job/team pair.",
        )
    )

    validations.append(
        validation_row(
            "VALID_WORK_TYPE_COMPATIBILITY",
            "PASS"
            if int(
                (~assignments["work_type_compatible"]).sum()
            ) == 0
            else "FAIL",
            int(
                (~assignments["work_type_compatible"]).sum()
            ),
            0,
            "Only work-type-compatible team rows are generated.",
        )
    )

    validations.append(
        validation_row(
            "ACTIVE_TEAM_AVAILABILITY",
            "PASS"
            if int(
                (~assignments["availability_feasible"]).sum()
            ) == 0
            else "FAIL",
            int(
                (~assignments["availability_feasible"]).sum()
            ),
            0,
            "Configured prototype teams must be ACTIVE.",
        )
    )

    validations.append(
        validation_row(
            "FEASIBLE_JOB_COVERAGE",
            "PASS"
            if feasible_job_count > 0
            else "FAIL",
            feasible_job_count,
            ">0",
            (
                "At least some jobs must have a feasible prototype team. "
                "Jobs with no feasible team are retained and documented."
            ),
        )
    )

    # Depot is intentionally not treated as a team feasibility failure at
    # this stage; routing later must resolve it.
    depot_configured_count = int(
        (
            teams["depot_status"]
            .fillna("")
            .astype(str)
            .str.strip()
            .ne("TO_BE_CONFIGURED")
        ).sum()
    )

    validations.append(
        validation_row(
            "DEPOT_NOT_INVENTED",
            "PASS"
            if depot_configured_count == 0
            else "REVIEW",
            depot_configured_count,
            0,
            (
                "Depot coordinates remain unresolved rather than being "
                "invented. Routing phase will resolve depot coordinates."
            ),
        )
    )

    validation_df = pd.DataFrame(validations)

    overall_pass = bool(
        validation_df["status"].eq("PASS").all()
    )

    # ----------------------------------------------------------------------
    # Summary JSON
    # ----------------------------------------------------------------------

    feasible_assignment_count = int(
        assignments["overall_feasible"].sum()
    )

    infeasible_assignment_count = int(
        (~assignments["overall_feasible"]).sum()
    )

    no_feasible_job_ids = sorted(
        assignments.loc[
            ~assignments.groupby("job_id")["overall_feasible"]
            .transform("any"),
            "job_id",
        ].unique().tolist()
    )

    team_feasible_counts = (
        assignments[
            assignments["overall_feasible"]
        ]["team_id"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    reason_counts = (
        assignments[
            ~assignments["overall_feasible"]
        ]["reason"]
        .value_counts()
        .to_dict()
    )

    summary = {
        "step": "13.3_feasible_team_assignments",
        "project_root": str(PROJECT_ROOT),
        "read_only": True,
        "approved_work_types": sorted(APPROVED_WORK_TYPES),
        "shift": {
            "start": SHIFT_START,
            "end": SHIFT_END,
            "hours": SHIFT_HOURS,
        },
        "counts": {
            "canonical_jobs": int(job_count),
            "assignment_rows": int(len(assignments)),
            "feasible_assignment_rows": feasible_assignment_count,
            "infeasible_assignment_rows": infeasible_assignment_count,
            "jobs_with_at_least_one_feasible_team": feasible_job_count,
            "jobs_with_no_feasible_team": no_feasible_jobs,
        },
        "feasible_assignment_counts_by_team": {
            key: int(value)
            for key, value in team_feasible_counts.items()
        },
        "infeasible_reason_counts": {
            key: int(value)
            for key, value in reason_counts.items()
        },
        "jobs_with_no_feasible_team": no_feasible_job_ids,
        "depot_policy": (
            "Depot remains TO_BE_CONFIGURED. It is not fabricated and is "
            "not used as a reason to discard jobs at team-matching stage."
        ),
        "validation": {
            "status": "PASS" if overall_pass else "FAIL",
            "checks_total": int(len(validation_df)),
            "checks_passed": int(
                validation_df["status"].eq("PASS").sum()
            ),
            "checks_failed": int(
                validation_df["status"].eq("FAIL").sum()
            ),
            "checks_review": int(
                validation_df["status"].eq("REVIEW").sum()
            ),
        },
        "outputs": {
            "feasible_assignments": str(OUTPUT_FILE),
            "validation": str(VALIDATION_FILE),
        },
        "next_step": (
            "Proceed to operational clustering after reviewing which "
            "jobs have no feasible team and why."
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    assignments.to_csv(
        OUTPUT_FILE,
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

    print()
    print("-" * 80)
    print("ASSIGNMENT SUMMARY")
    print("-" * 80)
    print(f"Canonical jobs                  : {job_count}")
    print(f"Assignment rows                 : {len(assignments)}")
    print(
        f"Feasible assignment rows        : "
        f"{feasible_assignment_count}"
    )
    print(
        f"Jobs with >=1 feasible team     : "
        f"{feasible_job_count}"
    )
    print(
        f"Jobs with NO feasible team      : "
        f"{no_feasible_jobs}"
    )

    print()
    print("Feasible assignments by team:")
    for team_id in sorted(
        team_feasible_counts
    ):
        print(
            f"  {team_id:8} : "
            f"{team_feasible_counts[team_id]}"
        )

    print()
    print("Jobs with no feasible team:")
    if no_feasible_job_ids:
        print(
            "  "
            + ", ".join(no_feasible_job_ids[:30])
        )
        if len(no_feasible_job_ids) > 30:
            print(
                f"  ... and {len(no_feasible_job_ids) - 30} more"
            )
    else:
        print("  NONE")

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validations:
        print(
            f"{row['check_id']:40} : "
            f"{row['status']:6} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13.3 FEASIBLE TEAM ASSIGNMENT GATE: "
        + ("PASS" if overall_pass else "FAIL")
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(f"Assignments : {OUTPUT_FILE}")
    print(f"Validation  : {VALIDATION_FILE}")
    print(f"Summary     : {SUMMARY_JSON}")

    if not overall_pass:
        raise RuntimeError(
            "Feasible team assignment validation failed. "
            "Review the generated validation file before continuing."
        )


if __name__ == "__main__":
    main()
