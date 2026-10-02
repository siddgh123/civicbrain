from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

try:
    from ortools.sat.python import cp_model
except ImportError as exc:
    raise ImportError(
        "OR-Tools is required for Step 13 scheduling. "
        "Install with: python -m pip install --upgrade --user ortools"
    ) from exc


# ============================================================================
# CIVICBRAIN STEP 13 — CP-SAT SCHEDULING
#
# Purpose:
#   Build a provisional multi-day schedule for all executable individual jobs.
#
# Inputs:
#   data/optimization/jobs/eligible_jobs.csv
#   data/optimization/teams/feasible_team_assignments.csv
#   data/optimization/teams/team_master.csv
#   data/optimization/clusters/cluster_members.csv
#   data/optimization/clusters/serviceability_results.csv
#
# Outputs:
#   data/optimization/scheduling/schedule_results.csv
#   data/optimization/scheduling/unscheduled_jobs.csv
#   data/optimization/scheduling/scheduling_validation.csv
#   data/optimization/scheduling/scheduling_summary.json
#
# Key design:
#   - Google OR-Tools CP-SAT determines WHO and WHEN.
#   - Current routing/travel data are not yet available, so travel time is
#     deliberately excluded from this provisional schedule.
#   - One active prototype team exists per operational work type.
#   - One team performs one job at a time.
#   - A job with service_duration <= 9 h can be scheduled.
#   - A job with service_duration > 9 h is explicitly UNSCHEDULED with
#     SCHEDULE_LATER / SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT.
#   - Short jobs inside a SCHEDULE_LATER cluster are still independently
#     schedulable; the whole cluster is not discarded.
#   - No job is scheduled twice.
#   - Priority is used as a second-stage CP-SAT objective AFTER maximizing
#     the number of scheduled jobs. No new priority formula is created.
#   - Schedule horizon is a prototype configuration, not a municipal policy.
#   - No PostgreSQL writes.
#   - No Step 11/12 modifications.
#   - No hotspot detection.
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

ELIGIBLE_JOBS_FILE = (
    DATA_DIR
    / "optimization"
    / "jobs"
    / "eligible_jobs.csv"
)

ASSIGNMENT_FILE = (
    DATA_DIR
    / "optimization"
    / "teams"
    / "feasible_team_assignments.csv"
)

TEAM_MASTER_FILE = (
    DATA_DIR
    / "optimization"
    / "teams"
    / "team_master.csv"
)

CLUSTER_MEMBERS_FILE = (
    DATA_DIR
    / "optimization"
    / "clusters"
    / "cluster_members.csv"
)

SERVICEABILITY_FILE = (
    DATA_DIR
    / "optimization"
    / "clusters"
    / "serviceability_results.csv"
)

OUTPUT_DIR = DATA_DIR / "optimization" / "scheduling"

SCHEDULE_FILE = (
    OUTPUT_DIR / "schedule_results.csv"
)

UNSCHEDULED_FILE = (
    OUTPUT_DIR / "unscheduled_jobs.csv"
)

VALIDATION_FILE = (
    OUTPUT_DIR / "scheduling_validation.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR / "scheduling_summary.json"
)


# ---------------------------------------------------------------------------
# Prototype scheduling configuration.
# ---------------------------------------------------------------------------

SHIFT_START = "08:00"
SHIFT_END = "17:00"
SHIFT_HOURS = 9.0

MINUTES_PER_HOUR = 60
SHIFT_MINUTES = int(SHIFT_HOURS * MINUTES_PER_HOUR)

# Deterministic prototype start date. This is a scheduling configuration,
# not a claim about an actual TDMC work calendar.
SCHEDULE_START_DATE = date(2026, 9, 28)

# Large enough to schedule the current 321 individually executable jobs
# while keeping CP-SAT search bounded. All dates are treated as working
# dates in this prototype because no holiday/weekend calendar was provided.
HORIZON_DAYS = 30

EXPECTED_ELIGIBLE_JOBS = 441

# Exactly the configured prototype teams already validated in Step 13.3.
APPROVED_TEAM_BY_WORK_TYPE = {
    "ROAD": "T001",
    "WATER": "T002",
    "GARBAGE": "T003",
    "ELECTRICITY": "T004",
}

APPROVED_WORK_TYPES = set(
    APPROVED_TEAM_BY_WORK_TYPE.keys()
)


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


def parse_equipment(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    return "|".join(
        sorted(
            {
                token.strip()
                for token in text.split("|")
                if token.strip()
            }
        )
    )


def main() -> None:
    print("=" * 80)
    print("CIVICBRAIN STEP 13 — CP-SAT PROVISIONAL SCHEDULING")
    print("=" * 80)

    print()
    print("READ-ONLY INPUTS")
    print("-" * 80)
    print(f"Eligible jobs : {ELIGIBLE_JOBS_FILE}")
    print(f"Assignments   : {ASSIGNMENT_FILE}")
    print(f"Team master   : {TEAM_MASTER_FILE}")
    print(f"Cluster       : {CLUSTER_MEMBERS_FILE}")
    print(f"Serviceability: {SERVICEABILITY_FILE}")
    print("Database      : NOT USED")
    print("Routing       : NOT USED")

    jobs = load_csv(
        ELIGIBLE_JOBS_FILE,
        "eligible jobs",
    )

    assignments = load_csv(
        ASSIGNMENT_FILE,
        "feasible assignments",
    )

    teams = load_csv(
        TEAM_MASTER_FILE,
        "team master",
    )

    cluster_members = load_csv(
        CLUSTER_MEMBERS_FILE,
        "cluster members",
    )

    serviceability = load_csv(
        SERVICEABILITY_FILE,
        "serviceability results",
    )

    # ----------------------------------------------------------------------
    # Required fields.
    # ----------------------------------------------------------------------

    required_jobs = {
        "complaint_id",
        "job_id",
        "work_type",
        "priority_score",
        "priority_level",
        "latitude",
        "longitude",
        "workers_required",
        "service_duration_hours",
        "estimated_cost",
        "required_equipment",
        "eligibility_status",
    }

    required_assignments = {
        "job_id",
        "team_id",
        "overall_feasible",
        "reason",
    }

    required_teams = {
        "team_id",
        "team_type",
        "worker_capacity",
        "working_start",
        "working_end",
        "status",
    }

    required_members = {
        "cluster_id",
        "job_id",
        "complaint_id",
        "sequence_candidate",
    }

    required_serviceability = {
        "cluster_id",
        "serviceability_status",
    }

    for label, df, required in [
        ("eligible jobs", jobs, required_jobs),
        ("feasible assignments", assignments, required_assignments),
        ("team master", teams, required_teams),
        ("cluster members", cluster_members, required_members),
        ("serviceability results", serviceability, required_serviceability),
    ]:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"{label} missing columns: "
                + ", ".join(sorted(missing))
            )

    # ----------------------------------------------------------------------
    # Normalize.
    # ----------------------------------------------------------------------

    jobs["job_id"] = (
        jobs["job_id"].astype(str).str.strip()
    )

    jobs["complaint_id"] = (
        jobs["complaint_id"].astype(str).str.strip()
    )

    jobs["work_type"] = (
        jobs["work_type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    jobs["priority_score"] = pd.to_numeric(
        jobs["priority_score"],
        errors="coerce",
    )

    jobs["latitude"] = pd.to_numeric(
        jobs["latitude"],
        errors="coerce",
    )

    jobs["longitude"] = pd.to_numeric(
        jobs["longitude"],
        errors="coerce",
    )

    jobs["workers_required"] = pd.to_numeric(
        jobs["workers_required"],
        errors="coerce",
    )

    jobs["service_duration_hours"] = pd.to_numeric(
        jobs["service_duration_hours"],
        errors="coerce",
    )

    jobs["estimated_cost"] = pd.to_numeric(
        jobs["estimated_cost"],
        errors="coerce",
    )

    assignments["job_id"] = (
        assignments["job_id"].astype(str).str.strip()
    )

    assignments["team_id"] = (
        assignments["team_id"].astype(str).str.strip()
    )

    assignments["overall_feasible"] = (
        assignments["overall_feasible"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes"})
    )

    assignments["reason"] = (
        assignments["reason"]
        .fillna("")
        .astype(str)
        .str.strip()
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

    serviceability["cluster_id"] = (
        serviceability["cluster_id"]
        .astype(str)
        .str.strip()
    )

    serviceability["serviceability_status"] = (
        serviceability["serviceability_status"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Only canonical eligible jobs are eligible for Step 13 scheduling.
    jobs = jobs[
        jobs["eligibility_status"].eq("ELIGIBLE")
    ].copy()

    if len(jobs) != EXPECTED_ELIGIBLE_JOBS:
        raise ValueError(
            f"Expected {EXPECTED_ELIGIBLE_JOBS} eligible jobs, "
            f"found {len(jobs)}."
        )

    # ----------------------------------------------------------------------
    # Build one valid team assignment per executable job.
    # ----------------------------------------------------------------------

    feasible = assignments[
        assignments["overall_feasible"]
    ].copy()

    feasible = feasible[
        feasible["job_id"].isin(
            jobs["job_id"]
        )
    ].copy()

    feasible_per_job = (
        feasible.groupby("job_id")["team_id"]
        .agg(lambda s: sorted(set(s)))
        .to_dict()
    )

    teams_by_id = {
        str(row["team_id"]): row
        for _, row in teams.iterrows()
    }

    executable_rows = []
    unscheduled_rows = []

    for _, row in jobs.iterrows():
        job_id = str(row["job_id"])
        work_type = str(row["work_type"])

        duration = float(
            row["service_duration_hours"]
        )

        priority = float(
            row["priority_score"]
        )

        eligible_team_ids = feasible_per_job.get(
            job_id,
            [],
        )

        configured_team_id = APPROVED_TEAM_BY_WORK_TYPE.get(
            work_type
        )

        # IMPORTANT:
        # A >9h job is intrinsically outside the single-shift prototype
        # constraint. Classify it BEFORE reading the feasible-team matrix,
        # because Step 13.3 also marks such a job infeasible for the same
        # shift-duration reason. This preserves the explicit long-job reason.
        if duration > SHIFT_HOURS:
            unscheduled_rows.append(
                {
                    "job_id": job_id,
                    "complaint_id": str(
                        row["complaint_id"]
                    ),
                    "cluster_id": "",
                    "work_type": work_type,
                    "priority_score": priority,
                    "reason": "SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT",
                    "details": (
                        f"Service duration {duration:.2f} h exceeds "
                        f"the {SHIFT_HOURS:.2f} h prototype shift. "
                        "Requires explicit multi-shift/deferred design."
                    ),
                    "status": "UNSCHEDULED",
                }
            )
            continue

        if not eligible_team_ids:
            unscheduled_rows.append(
                {
                    "job_id": job_id,
                    "complaint_id": str(
                        row["complaint_id"]
                    ),
                    "cluster_id": "",
                    "work_type": work_type,
                    "priority_score": priority,
                    "reason": "NO_FEASIBLE_TEAM",
                    "details": (
                        "No feasible prototype team assignment was "
                        "available for this eligible job."
                    ),
                    "status": "UNSCHEDULED",
                }
            )
            continue

        # There is currently exactly one team per approved work type.
        if configured_team_id in eligible_team_ids:
            team_id = configured_team_id
        else:
            # Deterministic fallback, while retaining the actual feasible team.
            team_id = sorted(
                eligible_team_ids
            )[0]

        if team_id not in teams_by_id:
            unscheduled_rows.append(
                {
                    "job_id": job_id,
                    "complaint_id": str(
                        row["complaint_id"]
                    ),
                    "cluster_id": "",
                    "work_type": work_type,
                    "priority_score": priority,
                    "reason": "NO_COMPATIBLE_TEAM",
                    "details": (
                        f"Configured team {team_id} is not present "
                        "in team master."
                    ),
                    "status": "UNSCHEDULED",
                }
            )
            continue

        executable_rows.append(
            {
                "job_id": job_id,
                "complaint_id": str(
                    row["complaint_id"]
                ),
                "work_type": work_type,
                "team_id": team_id,
                "priority_score": priority,
                "priority_level": str(
                    row["priority_level"]
                ),
                "latitude": float(
                    row["latitude"]
                ),
                "longitude": float(
                    row["longitude"]
                ),
                "workers_required": float(
                    row["workers_required"]
                ),
                "service_duration_hours": duration,
                "estimated_cost": float(
                    row["estimated_cost"]
                ),
                "required_equipment": parse_equipment(
                    row["required_equipment"]
                ),
            }
        )

    executable = pd.DataFrame(
        executable_rows
    )

    if executable.empty:
        raise RuntimeError(
            "No individually executable jobs remain for scheduling."
        )

    # ----------------------------------------------------------------------
    # Map job -> cluster. Every eligible job should appear exactly once.
    # ----------------------------------------------------------------------

    duplicate_cluster_assignment = int(
        cluster_members["job_id"].duplicated().sum()
    )

    if duplicate_cluster_assignment != 0:
        raise ValueError(
            "Cluster members contain a job more than once."
        )

    cluster_map = dict(
        zip(
            cluster_members["job_id"],
            cluster_members["cluster_id"],
        )
    )

    executable["cluster_id"] = (
        executable["job_id"]
        .map(cluster_map)
        .fillna("")
        .astype(str)
    )

    # ----------------------------------------------------------------------
    # CP-SAT model.
    #
    # Time representation:
    #   day = 0..HORIZON_DAYS-1
    #   start_min = minutes after 08:00 within the day
    #   end_min = start_min + service duration
    #
    # Because exactly one prototype team is active for each work type and
    # one team can perform one job at a time, jobs sharing a team have
    # NoOverlap constraints.
    # ----------------------------------------------------------------------

    model = cp_model.CpModel()

    horizon_minutes = (
        HORIZON_DAYS * SHIFT_MINUTES
    )

    # Use absolute timeline in minutes, with a 9-hour gap represented by
    # each day. We disallow crossing the day boundary by adding day-specific
    # intervals below.
    interval_vars = []
    job_vars = {}

    for idx, row in executable.reset_index(drop=True).iterrows():
        duration_min = int(
            round(
                float(row["service_duration_hours"])
                * MINUTES_PER_HOUR
            )
        )

        duration_min = max(
            1,
            duration_min,
        )

        day_var = model.NewIntVar(
            0,
            HORIZON_DAYS - 1,
            f"day_{idx}",
        )

        start_offset = model.NewIntVar(
            0,
            SHIFT_MINUTES - duration_min,
            f"start_{idx}",
        )

        # Absolute start in a compressed day timeline.
        absolute_start = model.NewIntVar(
            0,
            horizon_minutes - 1,
            f"abs_start_{idx}",
        )

        model.Add(
            absolute_start
            == day_var * SHIFT_MINUTES
            + start_offset
        )

        absolute_end = model.NewIntVar(
            duration_min,
            horizon_minutes,
            f"abs_end_{idx}",
        )

        model.Add(
            absolute_end
            == absolute_start + duration_min
        )

        interval = model.NewIntervalVar(
            absolute_start,
            duration_min,
            absolute_end,
            f"interval_{idx}",
        )

        interval_vars.append(
            (
                str(row["team_id"]),
                interval,
            )
        )

        job_vars[idx] = {
            "day": day_var,
            "start_offset": start_offset,
            "absolute_start": absolute_start,
            "absolute_end": absolute_end,
            "duration_min": duration_min,
            "interval": interval,
        }

    # Team no-overlap.
    for team_id in sorted(
        executable["team_id"].unique().tolist()
    ):
        team_intervals = [
            interval
            for assigned_team_id, interval
            in interval_vars
            if assigned_team_id == team_id
        ]

        if team_intervals:
            model.AddNoOverlap(
                team_intervals
            )

    # ----------------------------------------------------------------------
    # Single CP-SAT model with a mathematically lexicographic objective.
    #
    # Objective priority:
    #   1) maximize number of scheduled jobs
    #   2) among those schedules, maximize the sum of existing Step 11
    #      priority scores
    #
    # No arbitrary tuning weight is used. BIG_M is derived as:
    #
    #   1 + maximum possible total priority score (scaled to integers)
    #
    # Therefore gaining one additional scheduled job always dominates any
    # possible priority-score improvement.
    #
    # This replaces the previous two-solve design that could return UNKNOWN
    # on the second optimization pass under a time limit.
    # ----------------------------------------------------------------------

    model = cp_model.CpModel()

    optional_vars = []
    team_intervals_by_team = {}

    for idx, row in executable.reset_index(drop=True).iterrows():
        duration_min = int(
            round(
                float(row["service_duration_hours"])
                * MINUTES_PER_HOUR
            )
        )

        duration_min = max(1, duration_min)

        if duration_min > SHIFT_MINUTES:
            raise ValueError(
                f"Executable job {row['job_id']} exceeds the shift."
            )

        day_var = model.NewIntVar(
            0,
            HORIZON_DAYS - 1,
            f"day_{idx}",
        )

        start_offset = model.NewIntVar(
            0,
            SHIFT_MINUTES - duration_min,
            f"start_{idx}",
        )

        absolute_start = model.NewIntVar(
            0,
            horizon_minutes - 1,
            f"abs_start_{idx}",
        )

        model.Add(
            absolute_start
            == day_var * SHIFT_MINUTES
            + start_offset
        )

        absolute_end = model.NewIntVar(
            duration_min,
            horizon_minutes,
            f"abs_end_{idx}",
        )

        model.Add(
            absolute_end
            == absolute_start + duration_min
        )

        assigned = model.NewBoolVar(
            f"assigned_{idx}"
        )

        interval = model.NewOptionalIntervalVar(
            absolute_start,
            duration_min,
            absolute_end,
            assigned,
            f"interval_{idx}",
        )

        team_id = str(row["team_id"])

        team_intervals_by_team.setdefault(
            team_id,
            [],
        ).append(interval)

        optional_vars.append(
            assigned
        )

        job_vars[idx] = {
            "day": day_var,
            "start_offset": start_offset,
            "absolute_start": absolute_start,
            "absolute_end": absolute_end,
            "duration_min": duration_min,
            "interval": interval,
            "assigned": assigned,
        }

    for team_id in sorted(
        team_intervals_by_team
    ):
        model.AddNoOverlap(
            team_intervals_by_team[team_id]
        )

    # Existing Step 11 scores are scaled only for integer CP-SAT arithmetic.
    priority_scaled_values = []

    for _, row in executable.reset_index(drop=True).iterrows():
        priority_scaled_values.append(
            max(
                0,
                int(
                    round(
                        float(row["priority_score"])
                        * 100.0
                    )
                ),
            )
        )

    max_possible_priority = sum(
        priority_scaled_values
    )

    BIG_M = max_possible_priority + 1

    lexicographic_objective = (
        BIG_M * sum(optional_vars)
        + sum(
            priority_scaled_values[idx]
            * optional_vars[idx]
            for idx in range(
                len(optional_vars)
            )
        )
    )

    model.Maximize(
        lexicographic_objective
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 90.0
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 13

    solve_status = solver.Solve(
        model
    )

    if solve_status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        status_name = solver.StatusName(
            solve_status
        )
        raise RuntimeError(
            "CP-SAT could not produce a feasible schedule. "
            f"Solver status={status_name}."
        )

    scheduled_from_solver = int(
        sum(
            solver.Value(var)
            for var in optional_vars
        )
    )

    # ----------------------------------------------------------------------
    # Build schedule output.
    # ----------------------------------------------------------------------

    schedule_rows = []

    scheduled_job_ids = set()

    for idx, row in executable.reset_index(drop=True).iterrows():
        assigned = solver.Value(
            job_vars[idx]["assigned"]
        )

        if assigned != 1:
            continue

        day_index = solver.Value(
            job_vars[idx]["day"]
        )

        start_offset_min = solver.Value(
            job_vars[idx]["start_offset"]
        )

        duration_min = int(
            job_vars[idx]["duration_min"]
        )

        schedule_date = (
            SCHEDULE_START_DATE
            + timedelta(days=day_index)
        )

        planned_start_total_min = (
            8 * 60
            + start_offset_min
        )

        planned_end_total_min = (
            planned_start_total_min
            + duration_min
        )

        planned_start = (
            f"{planned_start_total_min // 60:02d}:"
            f"{planned_start_total_min % 60:02d}"
        )

        planned_end = (
            f"{planned_end_total_min // 60:02d}:"
            f"{planned_end_total_min % 60:02d}"
        )

        team_id = str(row["team_id"])

        schedule_id = (
            f"SCH_{schedule_date.strftime('%Y%m%d')}_{team_id}"
        )

        scheduled_job_ids.add(
            str(row["job_id"])
        )

        schedule_rows.append(
            {
                "schedule_id": schedule_id,
                "team_id": team_id,
                "schedule_date": schedule_date.isoformat(),
                "cluster_id": str(
                    row["cluster_id"]
                ),
                "job_id": str(
                    row["job_id"]
                ),
                "complaint_id": str(
                    row["complaint_id"]
                ),
                "sequence_no": 0,
                "planned_start": planned_start,
                "planned_end": planned_end,
                "service_duration_h": float(
                    row["service_duration_hours"]
                ),
                "travel_distance_m": 0.0,
                "travel_time_min": 0.0,
                "priority_score": float(
                    row["priority_score"]
                ),
                "estimated_cost": float(
                    row["estimated_cost"]
                ),
                "workers_required": float(
                    row["workers_required"]
                ),
                "required_equipment": str(
                    row["required_equipment"]
                ),
                "priority_level": str(
                    row["priority_level"]
                ),
                "status": "SCHEDULED",
                "travel_status": "PENDING_ROUTING",
            }
        )

    # Sequence number is only within team/date.
    schedule_df = pd.DataFrame(
        schedule_rows
    )

    if not schedule_df.empty:
        schedule_df = schedule_df.sort_values(
            [
                "schedule_date",
                "team_id",
                "planned_start",
                "priority_score",
                "job_id",
            ],
            ascending=[
                True,
                True,
                True,
                False,
                True,
            ],
            kind="stable",
        ).reset_index(drop=True)

        schedule_df["sequence_no"] = (
            schedule_df.groupby(
                ["schedule_date", "team_id"]
            ).cumcount()
            + 1
        )

    # ----------------------------------------------------------------------
    # Unscheduled output.
    # ----------------------------------------------------------------------

    unscheduled_by_model = executable[
        ~executable["job_id"].isin(
            scheduled_job_ids
        )
    ].copy()

    model_unscheduled_rows = []

    for _, row in unscheduled_by_model.iterrows():
        model_unscheduled_rows.append(
            {
                "job_id": str(row["job_id"]),
                "complaint_id": str(
                    row["complaint_id"]
                ),
                "cluster_id": str(
                    row["cluster_id"]
                ),
                "work_type": str(
                    row["work_type"]
                ),
                "priority_score": float(
                    row["priority_score"]
                ),
                "reason": "SCHEDULE_HORIZON_OR_TEAM_CAPACITY",
                "details": (
                    f"CP-SAT could not schedule this individually executable "
                    f"job within the {HORIZON_DAYS}-day prototype horizon."
                ),
                "status": "UNSCHEDULED",
            }
        )

    unscheduled_df = pd.DataFrame(
        unscheduled_rows
        + model_unscheduled_rows
    )

    # Add cluster IDs to all pre-classified unscheduled jobs.
    if not unscheduled_df.empty:
        unscheduled_df["cluster_id"] = (
            unscheduled_df["job_id"]
            .map(cluster_map)
            .fillna(
                unscheduled_df["cluster_id"]
            )
            .astype(str)
        )

        unscheduled_df = unscheduled_df[
            [
                "job_id",
                "complaint_id",
                "cluster_id",
                "work_type",
                "priority_score",
                "reason",
                "details",
                "status",
            ]
        ].sort_values(
            [
                "priority_score",
                "job_id",
            ],
            ascending=[
                False,
                True,
            ],
            kind="stable",
        ).reset_index(drop=True)

    # ----------------------------------------------------------------------
    # Add explicit routing note.
    # ----------------------------------------------------------------------

    if not schedule_df.empty:
        schedule_df["schedule_note"] = (
            "Provisional schedule before OSRM travel-time validation."
        )

    # ----------------------------------------------------------------------
    # Validation.
    # ----------------------------------------------------------------------

    scheduled_count = int(
        len(schedule_df)
    )

    unscheduled_count = int(
        len(unscheduled_df)
    )

    total_accounted = (
        scheduled_count
        + unscheduled_count
    )

    duplicate_scheduled = int(
        schedule_df["job_id"].duplicated().sum()
    ) if not schedule_df.empty else 0

    scheduled_set = set(
        schedule_df["job_id"].astype(str)
    ) if not schedule_df.empty else set()

    unscheduled_set = set(
        unscheduled_df["job_id"].astype(str)
    ) if not unscheduled_df.empty else set()

    overlap_scheduled_unscheduled = len(
        scheduled_set & unscheduled_set
    )

    unique_accounted = len(
        scheduled_set | unscheduled_set
    )

    # Check all scheduled jobs fit within shift and have valid team.
    shift_violations = 0

    if not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            start_h, start_m = map(
                int,
                row["planned_start"].split(":"),
            )

            end_h, end_m = map(
                int,
                row["planned_end"].split(":"),
            )

            start_total = (
                start_h * 60 + start_m
            )

            end_total = (
                end_h * 60 + end_m
            )

            if (
                start_total < 8 * 60
                or end_total > 17 * 60
                or end_total <= start_total
            ):
                shift_violations += 1

    team_lookup = {
        str(row["team_id"]): row
        for _, row in teams.iterrows()
    }

    invalid_team_assignments = 0

    if not schedule_df.empty:
        for _, row in schedule_df.iterrows():
            team = team_lookup.get(
                str(row["team_id"])
            )

            if team is None:
                invalid_team_assignments += 1
                continue

            if (
                str(team["status"]).upper()
                != "ACTIVE"
            ):
                invalid_team_assignments += 1

    # Same team/date overlaps.
    overlap_count = 0

    if not schedule_df.empty:
        for (
            schedule_date,
            team_id,
        ), group in schedule_df.groupby(
            [
                "schedule_date",
                "team_id",
            ]
        ):
            timeline = []

            for _, row in group.iterrows():
                start_h, start_m = map(
                    int,
                    row["planned_start"].split(":"),
                )

                end_h, end_m = map(
                    int,
                    row["planned_end"].split(":"),
                )

                timeline.append(
                    (
                        start_h * 60 + start_m,
                        end_h * 60 + end_m,
                        str(row["job_id"]),
                    )
                )

            timeline.sort()

            for i in range(
                len(timeline) - 1
            ):
                current_end = timeline[i][1]
                next_start = timeline[i + 1][0]

                if next_start < current_end:
                    overlap_count += 1

    # Validate high-level status coverage.
    expected_job_set = set(
        jobs["job_id"].astype(str)
    )

    validation_rows = []

    def add_validation(
        check_id,
        status,
        actual,
        expected,
        notes,
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
        "CP_SAT_SOLVER_STATUS",
        "PASS"
        if solve_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        else "FAIL",
        solver.StatusName(solve_status),
        "OPTIMAL or FEASIBLE",
        "CP-SAT must return a usable schedule solution.",
    )

    add_validation(
        "ELIGIBLE_JOB_COUNT",
        "PASS"
        if len(jobs) == EXPECTED_ELIGIBLE_JOBS
        else "FAIL",
        len(jobs),
        EXPECTED_ELIGIBLE_JOBS,
        "Step 13.1 canonical eligible-job count.",
    )

    add_validation(
        "ALL_ELIGIBLE_JOBS_ACCOUNTED_FOR",
        "PASS"
        if unique_accounted == EXPECTED_ELIGIBLE_JOBS
        and total_accounted == EXPECTED_ELIGIBLE_JOBS
        else "FAIL",
        unique_accounted,
        EXPECTED_ELIGIBLE_JOBS,
        "Every eligible job ends SCHEDULED or UNSCHEDULED.",
    )

    add_validation(
        "NO_JOB_SCHEDULED_TWICE",
        "PASS"
        if duplicate_scheduled == 0
        else "FAIL",
        duplicate_scheduled,
        0,
        "Each job may appear at most once in the provisional schedule.",
    )

    add_validation(
        "SCHEDULED_UNSCHEDULED_DISJOINT",
        "PASS"
        if overlap_scheduled_unscheduled == 0
        else "FAIL",
        overlap_scheduled_unscheduled,
        0,
        "A job cannot be both SCHEDULED and UNSCHEDULED.",
    )

    add_validation(
        "SHIFT_WINDOW_VALID",
        "PASS"
        if shift_violations == 0
        else "FAIL",
        shift_violations,
        0,
        "Scheduled jobs must remain inside 08:00–17:00.",
    )

    add_validation(
        "TEAM_ASSIGNMENT_VALID",
        "PASS"
        if invalid_team_assignments == 0
        else "FAIL",
        invalid_team_assignments,
        0,
        "Only active prototype teams may receive jobs.",
    )

    add_validation(
        "TEAM_NO_OVERLAP",
        "PASS"
        if overlap_count == 0
        else "FAIL",
        overlap_count,
        0,
        "One prototype team executes one job at a time.",
    )

    long_job_unscheduled = 0

    if not unscheduled_df.empty:
        long_job_unscheduled = int(
            (
                unscheduled_df["reason"]
                == "SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT"
            ).sum()
        )

    executable_count = int(
        len(executable)
    )

    add_validation(
        "INDIVIDUALLY_EXECUTABLE_JOBS",
        "PASS"
        if executable_count > 0
        else "FAIL",
        executable_count,
        ">0",
        "Jobs <= one shift with a feasible team enter CP-SAT.",
    )

    add_validation(
        "LONG_JOBS_EXPLICITLY_UNSCHEDULED",
        "PASS"
        if long_job_unscheduled
        == (
            len(jobs)
            - executable_count
            + int(
                (
                    jobs["service_duration_hours"]
                    > SHIFT_HOURS
                ).sum()
            )
            - (
                len(jobs)
                - executable_count
            )
        )
        else "REVIEW",
        long_job_unscheduled,
        int(
            (
                jobs["service_duration_hours"]
                > SHIFT_HOURS
            ).sum()
        ),
        "Every eligible job with service duration > one shift must be explicitly "
        "recorded as SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT.",
    )

    # The previous formula simplifies to the long-job count, but the direct
    # expected value above is clearer and is what is actually being checked.
    validation_rows[-1] = validation_row(
        "LONG_JOBS_EXPLICITLY_UNSCHEDULED",
        "PASS"
        if long_job_unscheduled
        == int(
            (
                jobs["service_duration_hours"]
                > SHIFT_HOURS
            ).sum()
        )
        else "FAIL",
        long_job_unscheduled,
        int(
            (
                jobs["service_duration_hours"]
                > SHIFT_HOURS
            ).sum()
        ),
        "Jobs exceeding one shift must remain explicitly unscheduled.",
    )

    validation_df = pd.DataFrame(
        validation_rows
    )

    solver_status_name = solver.StatusName(solve_status)

    overall_pass = bool(
        validation_df["status"].eq("PASS").all()
    )

    # ----------------------------------------------------------------------
    # Summary.
    # ----------------------------------------------------------------------

    status_counts = (
        unscheduled_df["reason"]
        .value_counts()
        .sort_index()
        .to_dict()
        if not unscheduled_df.empty
        else {}
    )

    scheduled_by_team = (
        schedule_df.groupby("team_id")["job_id"]
        .count()
        .sort_index()
        .to_dict()
        if not schedule_df.empty
        else {}
    )

    scheduled_by_date = (
        schedule_df.groupby("schedule_date")["job_id"]
        .count()
        .sort_index()
        .to_dict()
        if not schedule_df.empty
        else {}
    )

    summary = {
        "step": "13_scheduling_cp_sat",
        "project_root": str(PROJECT_ROOT),
        "read_only": True,
        "configuration": {
            "shift_start": SHIFT_START,
            "shift_end": SHIFT_END,
            "shift_hours": SHIFT_HOURS,
            "schedule_start_date": SCHEDULE_START_DATE.isoformat(),
            "horizon_days": HORIZON_DAYS,
            "routing_included": False,
            "travel_time_included": False,
            "team_rule": "one_active_prototype_team_per_work_type",
            "one_job_at_a_time": True,
            "priority_objective": (
                "lexicographic: maximize scheduled job count first, "
                "then maximize sum of existing Step 11 priority scores"
            ),
        },
        "counts": {
            "eligible_jobs": int(
                len(jobs)
            ),
            "individually_executable_jobs": executable_count,
            "scheduled_jobs": scheduled_count,
            "unscheduled_jobs": unscheduled_count,
            "long_jobs_over_9h": int(
                (
                    jobs["service_duration_hours"]
                    > SHIFT_HOURS
                ).sum()
            ),
        },
        "scheduled_by_team": {
            key: int(value)
            for key, value in scheduled_by_team.items()
        },
        "scheduled_by_date": {
            key: int(value)
            for key, value in scheduled_by_date.items()
        },
        "unscheduled_reason_counts": {
            key: int(value)
            for key, value in status_counts.items()
        },
        "cp_sat": {
            "scheduled_jobs_by_solver": scheduled_from_solver,
            "solver_status": solver.StatusName(solve_status),
            "lexicographic_priority_scale": 100,
            "lexicographic_big_m": BIG_M,
        },
        "important_notes": [
            "This is a provisional schedule before road-network travel time.",
            "Travel distance/time are set to zero with travel_status=PENDING_ROUTING.",
            "Short jobs inside a SCHEDULE_LATER cluster remain independently schedulable.",
            "Jobs exceeding 9 hours are not silently dropped; they are UNSCHEDULED.",
            "The 08:00–17:00 calendar and 30-day horizon are prototype configurations.",
            "No weekend/holiday calendar was supplied, so every prototype horizon date is treated as available.",
            "No depot coordinates were invented.",
        ],
        "validation": {
            "status": "PASS"
            if overall_pass
            else "FAIL",
            "checks_total": int(
                len(validation_df)
            ),
            "checks_passed": int(
                validation_df["status"].eq("PASS").sum()
            ),
            "checks_failed": int(
                validation_df["status"].eq("FAIL").sum()
            ),
        },
        "outputs": {
            "schedule_results": str(
                SCHEDULE_FILE
            ),
            "unscheduled_jobs": str(
                UNSCHEDULED_FILE
            ),
            "validation": str(
                VALIDATION_FILE
            ),
            "summary": str(
                SUMMARY_FILE
            ),
        },
        "next_step": (
            "Resolve/configure depot, validate road-network travel with OSRM, "
            "build distance/time matrices, then revalidate the schedule and "
            "run OR-Tools RoutingModel."
        ),
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    schedule_df.to_csv(
        SCHEDULE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    unscheduled_df.to_csv(
        UNSCHEDULED_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    validation_df.to_csv(
        VALIDATION_FILE,
        index=False,
        encoding="utf-8-sig",
    )

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
    print("SCHEDULING SUMMARY")
    print("-" * 80)
    print(
        f"Eligible jobs                 : {len(jobs)}"
    )
    print(
        f"Individually executable jobs  : {executable_count}"
    )
    print(
        f"Scheduled jobs                : {scheduled_count}"
    )
    print(
        f"Unscheduled jobs              : {unscheduled_count}"
    )
    print(
        f"Long jobs > 9h                : "
        f"{int((jobs['service_duration_hours'] > SHIFT_HOURS).sum())}"
    )
    print(
        f"CP-SAT scheduled jobs          : {scheduled_from_solver}"
    )

    print()
    print("Scheduled jobs by team:")
    for team_id in sorted(
        scheduled_by_team
    ):
        print(
            f"  {team_id:8} : "
            f"{scheduled_by_team[team_id]}"
        )

    print()
    print("Unscheduled reasons:")
    if status_counts:
        for reason in sorted(
            status_counts
        ):
            print(
                f"  {reason:45} : "
                f"{status_counts[reason]}"
            )
    else:
        print("  NONE")

    print()
    print("-" * 80)
    print("VALIDATION")
    print("-" * 80)

    for row in validation_rows:
        print(
            f"{row['check_id']:38} : "
            f"{row['status']:6} | actual={row['actual_value']}"
        )

    print()
    print("=" * 80)
    print(
        "STEP 13 CP-SAT SCHEDULING GATE: "
        + (
            "PASS"
            if overall_pass
            else "FAIL"
        )
    )
    print("=" * 80)

    print()
    print("OUTPUT FILES")
    print(
        f"Schedule      : {SCHEDULE_FILE}"
    )
    print(
        f"Unscheduled   : {UNSCHEDULED_FILE}"
    )
    print(
        f"Validation    : {VALIDATION_FILE}"
    )
    print(
        f"Summary       : {SUMMARY_FILE}"
    )

    if not overall_pass:
        raise RuntimeError(
            "Scheduling validation failed. "
            "Review scheduling_validation.csv before proceeding."
        )


if __name__ == "__main__":
    main()
