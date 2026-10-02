from pathlib import Path
from datetime import datetime, date, time, timedelta
import csv
import json

ROOT = Path(".")
JOBS_PATH = ROOT / "data" / "optimization" / "jobs" / "eligible_jobs.csv"
FA_PATH = ROOT / "data" / "optimization" / "teams" / "feasible_team_assignments.csv"
OUT_DIR = ROOT / "data" / "optimization" / "evaluation"

OUT_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_SCHEDULE = OUT_DIR / "baseline_schedule.csv"
BASELINE_UNSCHEDULED = OUT_DIR / "baseline_unscheduled_jobs.csv"
BASELINE_VALIDATION = OUT_DIR / "baseline_validation.csv"
BASELINE_SUMMARY = OUT_DIR / "baseline_summary.json"

START_DATE = date(2026, 9, 28)
HORIZON_DAYS = 30
END_DATE = START_DATE + timedelta(days=HORIZON_DAYS - 1)

SHIFT_START_MIN = 8 * 60
SHIFT_END_MIN = 17 * 60
SHIFT_MIN = SHIFT_END_MIN - SHIFT_START_MIN


def parse_datetime(value, field_name, job_id):
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(
            f"Missing {field_name} for job_id={job_id}"
        )

    text = text.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(text)
    except Exception as exc:
        raise RuntimeError(
            f"Invalid {field_name} for job_id={job_id}: {value}"
        ) from exc


def parse_float(value, field_name, job_id):
    try:
        return float(str(value).strip())
    except Exception as exc:
        raise RuntimeError(
            f"Invalid {field_name} for job_id={job_id}: {value}"
        ) from exc


def minutes_to_text(total_minutes):
    hh = total_minutes // 60
    mm = total_minutes % 60
    return f"{hh:02d}:{mm:02d}"


# ------------------------------------------------------------------
# LOAD INPUTS
# ------------------------------------------------------------------
with JOBS_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    jobs = list(csv.DictReader(f))

with FA_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    assignments = list(csv.DictReader(f))

if not jobs:
    raise RuntimeError("eligible_jobs.csv is empty.")

if not assignments:
    raise RuntimeError("feasible_team_assignments.csv is empty.")

job_by_id = {
    str(row["job_id"]).strip(): row
    for row in jobs
}

eligible_job_ids = set(job_by_id.keys())

# ------------------------------------------------------------------
# BUILD UNIQUE FEASIBLE TEAM MAP
# ------------------------------------------------------------------
feasible_rows = [
    row for row in assignments
    if str(row.get("overall_feasible", "")).strip().lower() == "true"
]

team_candidates = {}

for row in feasible_rows:
    job_id = str(row.get("job_id", "")).strip()
    team_id = str(row.get("team_id", "")).strip()

    if not job_id or not team_id:
        raise RuntimeError("Feasible assignment contains blank job_id/team_id.")

    team_candidates.setdefault(job_id, []).append(team_id)

multiple_team_jobs = {
    job_id: teams
    for job_id, teams in team_candidates.items()
    if len(set(teams)) > 1
}

if multiple_team_jobs:
    raise RuntimeError(
        "Baseline expected unique feasible team per job, but multiple "
        f"teams found for {len(multiple_team_jobs)} jobs."
    )

# Verify the current source state.
if len(feasible_rows) != 321:
    raise RuntimeError(
        f"Expected 321 feasible rows from validated source, got {len(feasible_rows)}."
    )

if len(team_candidates) != 321:
    raise RuntimeError(
        f"Expected 321 unique feasible jobs, got {len(team_candidates)}."
    )

# ------------------------------------------------------------------
# ORDER JOBS
# ------------------------------------------------------------------
feasible_jobs = []

for job_id, job in job_by_id.items():
    if job_id not in team_candidates:
        continue

    parse_datetime(job.get("submitted_at"), "submitted_at", job_id)

    service_h = parse_float(
        job.get("service_duration_hours"),
        "service_duration_hours",
        job_id
    )

    if service_h <= 0:
        raise RuntimeError(
            f"Non-positive service duration for job_id={job_id}: {service_h}"
        )

    feasible_jobs.append(job)

# Deterministic FIFO order.
feasible_jobs.sort(
    key=lambda r: (
        parse_datetime(r["submitted_at"], "submitted_at", r["job_id"]),
        int(r["job_id"]) if str(r["job_id"]).isdigit() else str(r["job_id"]),
    )
)

# ------------------------------------------------------------------
# GREEDY FIFO SCHEDULING
# ------------------------------------------------------------------
team_state = {}

for team_id in sorted(set(team_candidates.values().__iter__().__next__() if False else [])):
    team_state[team_id] = {}

# Build team list from actual feasible assignments.
team_ids = sorted(
    {
        teams[0]
        for teams in team_candidates.values()
    }
)

for team_id in team_ids:
    team_state[team_id] = {
        "current_date": START_DATE,
        "current_minute": SHIFT_START_MIN,
        "date_sequence": {},
    }

schedule_rows = []
unscheduled_rows = []

for job in feasible_jobs:
    job_id = str(job["job_id"]).strip()
    team_id = team_candidates[job_id][0]

    service_h = parse_float(
        job["service_duration_hours"],
        "service_duration_hours",
        job_id
    )

    service_minutes = int(round(service_h * 60))

    state = team_state[team_id]

    if service_minutes > SHIFT_MIN:
        raise RuntimeError(
            f"Feasible assignment contains >9h job_id={job_id}: {service_h}h"
        )

    placed = False

    while state["current_date"] <= END_DATE:
        available = SHIFT_END_MIN - state["current_minute"]

        if service_minutes <= available:
            start_minute = state["current_minute"]
            end_minute = start_minute + service_minutes

            day_key = state["current_date"].isoformat()
            sequence_no = state["date_sequence"].get(day_key, 0) + 1
            state["date_sequence"][day_key] = sequence_no

            schedule_rows.append({
                "schedule_id": (
                    f"BASE-{team_id}-"
                    f"{state['current_date'].isoformat()}-"
                    f"{sequence_no:03d}"
                ),
                "team_id": team_id,
                "schedule_date": state["current_date"].isoformat(),
                "job_id": job_id,
                "sequence_no": sequence_no,
                "planned_start": (
                    f"{state['current_date'].isoformat()} "
                    f"{minutes_to_text(start_minute)}"
                ),
                "planned_end": (
                    f"{state['current_date'].isoformat()} "
                    f"{minutes_to_text(end_minute)}"
                ),
                "service_duration_h": f"{service_h:.2f}",
                "travel_distance_m": "0",
                "travel_time_min": "0",
                "priority_score": job.get("priority_score", ""),
                "estimated_cost": job.get("estimated_cost", ""),
                "travel_status": "PENDING_ROUTING",
                "status": "SCHEDULED_BASELINE",
            })

            state["current_minute"] = end_minute
            placed = True
            break

        # Move to next day.
        state["current_date"] += timedelta(days=1)
        state["current_minute"] = SHIFT_START_MIN

    if not placed:
        unscheduled_rows.append({
            "job_id": job_id,
            "complaint_id": job.get("complaint_id", ""),
            "work_type": job.get("work_type", ""),
            "priority_score": job.get("priority_score", ""),
            "reason": "SCHEDULE_HORIZON_OR_TEAM_CAPACITY",
            "details": (
                "FIFO baseline could not place the job within the "
                "configured 30-day team schedule horizon."
            ),
            "status": "UNSCHEDULED_BASELINE",
        })

# ------------------------------------------------------------------
# ADD ALL 120 INDIVIDUALLY INFEASIBLE JOBS
# ------------------------------------------------------------------
for job in jobs:
    job_id = str(job["job_id"]).strip()

    if job_id in team_candidates:
        continue

    service_h = parse_float(
        job["service_duration_hours"],
        "service_duration_hours",
        job_id
    )

    unscheduled_rows.append({
        "job_id": job_id,
        "complaint_id": job.get("complaint_id", ""),
        "work_type": job.get("work_type", ""),
        "priority_score": job.get("priority_score", ""),
        "reason": "SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT",
        "details": (
            f"Service duration {service_h:.2f}h exceeds the "
            "9-hour prototype shift."
        ),
        "status": "UNSCHEDULED_BASELINE",
    })

# ------------------------------------------------------------------
# SORT OUTPUTS DETERMINISTICALLY
# ------------------------------------------------------------------
schedule_rows.sort(
    key=lambda r: (
        r["schedule_date"],
        r["team_id"],
        int(r["sequence_no"]),
        int(r["job_id"]) if str(r["job_id"]).isdigit() else str(r["job_id"]),
    )
)

unscheduled_rows.sort(
    key=lambda r: (
        r["reason"],
        int(r["job_id"]) if str(r["job_id"]).isdigit() else str(r["job_id"]),
    )
)

# ------------------------------------------------------------------
# VALIDATION
# ------------------------------------------------------------------
checks = []

scheduled_ids = [r["job_id"] for r in schedule_rows]
unscheduled_ids = [r["job_id"] for r in unscheduled_rows]

def add_check(name, passed, details):
    checks.append({
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
    })


add_check(
    "ELIGIBLE_JOB_COUNT",
    len(jobs) == 441,
    f"eligible={len(jobs)}"
)

add_check(
    "FEASIBLE_JOB_COUNT",
    len(feasible_jobs) == 321,
    f"feasible={len(feasible_jobs)}"
)

add_check(
    "SCHEDULED_UNIQUE",
    len(scheduled_ids) == len(set(scheduled_ids)),
    f"scheduled={len(scheduled_ids)}"
)

add_check(
    "UNSCHEDULED_UNIQUE",
    len(unscheduled_ids) == len(set(unscheduled_ids)),
    f"unscheduled={len(unscheduled_ids)}"
)

all_accounted = (
    len(scheduled_ids) + len(unscheduled_ids) == len(jobs)
    and set(scheduled_ids).isdisjoint(set(unscheduled_ids))
    and set(scheduled_ids) | set(unscheduled_ids) == eligible_job_ids
)

add_check(
    "ALL_ELIGIBLE_JOBS_ACCOUNTED_FOR",
    all_accounted,
    f"scheduled={len(scheduled_ids)}, unscheduled={len(unscheduled_ids)}, eligible={len(jobs)}"
)

valid_team_ids = set(team_ids)

add_check(
    "TEAM_IDS_VALID",
    all(r["team_id"] in valid_team_ids for r in schedule_rows),
    f"teams={','.join(team_ids)}"
)

within_shift = True

for r in schedule_rows:
    start = datetime.strptime(r["planned_start"], "%Y-%m-%d %H:%M")
    end = datetime.strptime(r["planned_end"], "%Y-%m-%d %H:%M")

    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute

    if not (
        SHIFT_START_MIN <= start_minutes
        and end_minutes <= SHIFT_END_MIN
        and end > start
    ):
        within_shift = False
        break

add_check(
    "WORKING_HOURS",
    within_shift,
    "All baseline service-only jobs are inside 08:00-17:00."
)

# Check overlaps per team/date.
no_overlap = True

for team_id in team_ids:
    team_days = {}

    for r in schedule_rows:
        if r["team_id"] != team_id:
            continue

        team_days.setdefault(r["schedule_date"], []).append(r)

    for day, rows in team_days.items():
        rows.sort(key=lambda x: x["planned_start"])

        previous_end = None

        for r in rows:
            start = datetime.strptime(r["planned_start"], "%Y-%m-%d %H:%M")
            end = datetime.strptime(r["planned_end"], "%Y-%m-%d %H:%M")

            if previous_end is not None and start < previous_end:
                no_overlap = False
                break

            previous_end = end

        if not no_overlap:
            break

    if not no_overlap:
        break

add_check(
    "NO_TEAM_OVERLAP",
    no_overlap,
    "No overlapping jobs within the same team/date."
)

# Verify all 120 source-infeasible jobs have the correct reason.
source_infeasible = {
    str(r["job_id"]).strip()
    for r in assignments
    if str(r.get("overall_feasible", "")).strip().lower() != "true"
}

wrong_long_reason = [
    r for r in unscheduled_rows
    if r["job_id"] in source_infeasible
    and r["reason"] != "SERVICE_DURATION_EXCEEDS_SINGLE_SHIFT"
]

add_check(
    "INFEASIBLE_JOB_REASON",
    len(source_infeasible) == 120 and not wrong_long_reason,
    f"source_infeasible={len(source_infeasible)}"
)

overall_pass = all(c["status"] == "PASS" for c in checks)

# ------------------------------------------------------------------
# WRITE FILES
# ------------------------------------------------------------------
schedule_fields = [
    "schedule_id",
    "team_id",
    "schedule_date",
    "job_id",
    "sequence_no",
    "planned_start",
    "planned_end",
    "service_duration_h",
    "travel_distance_m",
    "travel_time_min",
    "priority_score",
    "estimated_cost",
    "travel_status",
    "status",
]

unscheduled_fields = [
    "job_id",
    "complaint_id",
    "work_type",
    "priority_score",
    "reason",
    "details",
    "status",
]

with BASELINE_SCHEDULE.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=schedule_fields)
    writer.writeheader()
    writer.writerows(schedule_rows)

with BASELINE_UNSCHEDULED.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=unscheduled_fields)
    writer.writeheader()
    writer.writerows(unscheduled_rows)

with BASELINE_VALIDATION.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["check", "status", "details"])
    writer.writeheader()
    writer.writerows(checks)

team_counts = {}
for row in schedule_rows:
    team_counts[row["team_id"]] = team_counts.get(row["team_id"], 0) + 1

date_counts = {}
for row in schedule_rows:
    date_counts[row["schedule_date"]] = date_counts.get(row["schedule_date"], 0) + 1

summary = {
    "baseline_name": "FIFO Greedy Baseline",
    "input": "data\\optimization\\jobs\\eligible_jobs.csv",
    "eligible_jobs": len(jobs),
    "feasible_jobs": len(feasible_jobs),
    "scheduled_jobs": len(schedule_rows),
    "unscheduled_jobs": len(unscheduled_rows),
    "unscheduled_reason_counts": {},
    "evaluation_start_date": START_DATE.isoformat(),
    "evaluation_end_date": END_DATE.isoformat(),
    "shift_start": "08:00",
    "shift_end": "17:00",
    "shift_hours": 9,
    "routing_status": "PENDING_ROUTING",
    "team_job_counts": team_counts,
    "jobs_per_date": date_counts,
    "validation_status": "PASS" if overall_pass else "FAIL",
    "validation_checks": len(checks),
    "validation_failed": sum(1 for c in checks if c["status"] == "FAIL"),
}

for row in unscheduled_rows:
    reason = row["reason"]
    summary["unscheduled_reason_counts"][reason] = (
        summary["unscheduled_reason_counts"].get(reason, 0) + 1
    )

with BASELINE_SUMMARY.open("w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

# ------------------------------------------------------------------
# CONSOLE REPORT
# ------------------------------------------------------------------
print("=" * 80)
print("CIVICBRAIN STEP 13 - FIFO GREEDY BASELINE")
print("=" * 80)
print(f"Eligible jobs         : {len(jobs)}")
print(f"Feasible jobs         : {len(feasible_jobs)}")
print(f"Scheduled jobs        : {len(schedule_rows)}")
print(f"Unscheduled jobs      : {len(unscheduled_rows)}")
print()

print("UNSCHEDULED REASONS")
print("-" * 80)
for reason, count in summary["unscheduled_reason_counts"].items():
    print(f"{reason:45s}: {count}")

print()
print("TEAM COUNTS")
print("-" * 80)
for team_id in sorted(team_counts):
    print(f"{team_id:10s}: {team_counts[team_id]}")

print()
print("VALIDATION")
print("-" * 80)
for check in checks:
    print(f"{check['check']:35s} {check['status']}")

print()
print("OVERALL STATUS :", "PASS" if overall_pass else "FAIL")

print()
print("OUTPUTS")
print("-" * 80)
print(f"Schedule      : {BASELINE_SCHEDULE}")
print(f"Unscheduled   : {BASELINE_UNSCHEDULED}")
print(f"Validation    : {BASELINE_VALIDATION}")
print(f"Summary       : {BASELINE_SUMMARY}")
print("=" * 80)

if not overall_pass:
    raise RuntimeError("FIFO baseline validation failed.")
