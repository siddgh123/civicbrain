import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime

ROOT = Path(".")

SCHEDULE_FILE = ROOT / "data/optimization/scheduling/final_step13_schedule_candidate.csv"
ROUTE_FILE = ROOT / "data/optimization/routing/final_step13_route_audit.csv"
UNSCHEDULED_FILE = ROOT / "data/optimization/scheduling/final_step13_unscheduled_jobs.csv"
TEAM_FILE = ROOT / "data/optimization/teams/team_master.csv"
TEAM_EQUIPMENT_FILE = ROOT / "data/optimization/teams/team_equipment.csv"

OUT_DIR = ROOT / "data/optimization/action_plan"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_ACTION_PLAN = OUT_DIR / "action_plan.csv"
OUT_REPORT = OUT_DIR / "action_plan_report.md"
OUT_VALIDATION = OUT_DIR / "action_plan_validation.csv"
OUT_SUMMARY = OUT_DIR / "action_plan_summary.json"


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    if not path.exists():
        raise RuntimeError(f"Missing required file: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fnum(value, field, default=0.0):
    text = str(value).strip()

    if text == "":
        return default

    try:
        return float(text)
    except Exception:
        raise RuntimeError(
            f"Invalid numeric value for {field}: {value!r}"
        )


def split_equipment(value):
    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    parts = re.split(r"[;,|]", text)

    return [
        p.strip()
        for p in parts
        if p.strip()
    ]


def unique_sorted(items):
    return sorted(
        {
            str(x).strip()
            for x in items
            if str(x).strip()
        }
    )


def date_only(value):
    return str(value).strip().split("T")[0]


# ============================================================
# LOAD
# ============================================================

schedule_rows = read_csv(SCHEDULE_FILE)
route_rows = read_csv(ROUTE_FILE)
unscheduled_rows = read_csv(UNSCHEDULED_FILE)
team_rows = read_csv(TEAM_FILE)
team_equipment_rows = read_csv(TEAM_EQUIPMENT_FILE)


if not schedule_rows:
    raise RuntimeError("Final schedule is empty.")

if not route_rows:
    raise RuntimeError("Final route audit is empty.")


# ============================================================
# BASIC REQUIRED COLUMNS
# ============================================================

required_schedule = [
    "schedule_id",
    "team_id",
    "schedule_date",
    "job_id",
    "sequence_no",
    "planned_start",
    "planned_end",
    "service_duration_h",
    "priority_score",
    "estimated_cost",
]

missing = [
    c for c in required_schedule
    if c not in schedule_rows[0]
]

if missing:
    raise RuntimeError(
        f"Schedule missing columns: {missing}"
    )


required_route = [
    "team_id",
    "schedule_date",
    "job_count",
    "jobs",
    "service_h",
    "travel_h",
    "total_route_h",
    "distance_km",
    "finish_time",
    "status",
]

missing = [
    c for c in required_route
    if c not in route_rows[0]
]

if missing:
    raise RuntimeError(
        f"Route audit missing columns: {missing}"
    )


# ============================================================
# TEAM MASTER
# ============================================================

team_master = {}

for r in team_rows:

    team_id = str(
        r.get("team_id", "")
    ).strip()

    if not team_id:
        continue

    team_master[team_id] = r


# ============================================================
# TEAM EQUIPMENT
# ============================================================

team_equipment = defaultdict(list)

for r in team_equipment_rows:

    team_id = str(
        r.get("team_id", "")
    ).strip()

    equipment = (
        r.get("equipment")
        or r.get("equipment_name")
        or r.get("required_equipment")
        or r.get("item")
        or ""
    )

    for item in split_equipment(equipment):

        if item not in team_equipment[team_id]:
            team_equipment[team_id].append(item)


# ============================================================
# GROUP SCHEDULE ROWS
# ============================================================

schedule_groups = defaultdict(list)
scheduled_job_ids = []

for r in schedule_rows:

    team = str(
        r["team_id"]
    ).strip()

    date = date_only(
        r["schedule_date"]
    )

    schedule_groups[
        (team, date)
    ].append(r)

    scheduled_job_ids.append(
        str(
            r["job_id"]
        ).strip()
    )


# ============================================================
# UNIQUE JOB VALIDATION
# ============================================================

scheduled_job_set = set(
    scheduled_job_ids
)

if len(scheduled_job_ids) != len(
    scheduled_job_set
):

    duplicates = sorted(
        {
            j
            for j in scheduled_job_ids
            if scheduled_job_ids.count(j) > 1
        }
    )

    raise RuntimeError(
        f"Duplicate scheduled jobs found: {duplicates[:20]}"
    )


# ============================================================
# ROUTE AUDIT LOOKUP
# ============================================================

route_lookup = {}

for r in route_rows:

    key = (
        str(
            r["team_id"]
        ).strip(),
        date_only(
            r["schedule_date"]
        ),
    )

    if key in route_lookup:
        raise RuntimeError(
            f"Duplicate route-audit group: {key}"
        )

    route_lookup[key] = r


# ============================================================
# BUILD ACTION PLAN
# ============================================================

action_plans = []

for group_number, key in enumerate(
    sorted(schedule_groups.keys()),
    start=1,
):

    team_id, schedule_date = key

    rows = sorted(
        schedule_groups[key],
        key=lambda r: int(
            r["sequence_no"]
        ),
    )

    route = route_lookup.get(key)

    if route is None:
        raise RuntimeError(
            f"No route audit row for group: {key}"
        )


    # --------------------------------------------------------
    # Jobs in exact route order
    # --------------------------------------------------------

    route_job_ids = [
        str(r["job_id"]).strip()
        for r in rows
    ]

    if (
        str(route["jobs"]).strip()
        != "|".join(route_job_ids)
    ):

        raise RuntimeError(
            f"Route job order mismatch for {key}:\n"
            f"Schedule={route_job_ids}\n"
            f"Audit={route['jobs']}"
        )


    # --------------------------------------------------------
    # Priority summary
    # --------------------------------------------------------

    priorities = [
        fnum(
            r["priority_score"],
            f"{r['job_id']}.priority_score"
        )
        for r in rows
    ]

    priority_sum = sum(priorities)
    priority_avg = (
        priority_sum / len(priorities)
        if priorities
        else 0.0
    )
    priority_max = (
        max(priorities)
        if priorities
        else 0.0
    )
    priority_min = (
        min(priorities)
        if priorities
        else 0.0
    )


    # --------------------------------------------------------
    # Worker requirement
    #
    # Sequential team model:
    # report the maximum simultaneous worker
    # requirement among jobs in the route.
    # --------------------------------------------------------

    worker_values = []

    for r in rows:

        candidate = (
            r.get("workers_required")
            or r.get("required_workers")
            or ""
        )

        if str(candidate).strip():

            worker_values.append(
                fnum(
                    candidate,
                    f"{r['job_id']}.workers_required"
                )
            )

    if worker_values:

        workers_required = max(
            worker_values
        )

    else:

        workers_required = ""


    # --------------------------------------------------------
    # Equipment
    # --------------------------------------------------------

    job_equipment = []

    for r in rows:

        for item in split_equipment(
            r.get(
                "required_equipment",
                ""
            )
        ):

            job_equipment.append(
                item
            )


    job_equipment = unique_sorted(
        job_equipment
    )

    prototype_team_equipment = unique_sorted(
        team_equipment.get(
            team_id,
            []
        )
    )


    # --------------------------------------------------------
    # Cost
    # --------------------------------------------------------

    estimated_cost = 0.0

    for r in rows:

        estimated_cost += fnum(
            r.get(
                "estimated_cost",
                ""
            ),
            f"{r['job_id']}.estimated_cost",
            default=0.0
        )


    # --------------------------------------------------------
    # Schedule times
    # --------------------------------------------------------

    start_times = [
        str(
            r["planned_start"]
        ).strip()
        for r in rows
        if str(
            r["planned_start"]
        ).strip()
    ]

    end_times = [
        str(
            r["planned_end"]
        ).strip()
        for r in rows
        if str(
            r["planned_end"]
        ).strip()
    ]

    start_time = (
        min(start_times)
        if start_times
        else ""
    )

    # Final end comes from route audit because
    # it includes the return-to-depot travel.
    final_end_time = str(
        route["finish_time"]
    ).strip()


    # --------------------------------------------------------
    # Route
    # --------------------------------------------------------

    route_text = (
        "DEPOT"
        + " → "
        + " → ".join(
            route_job_ids
        )
        + " → DEPOT"
    )


    # --------------------------------------------------------
    # Route status
    # --------------------------------------------------------

    route_status = str(
        route["status"]
    ).strip()

    if route_status != "PASS":
        raise RuntimeError(
            f"Non-PASS route in final action plan: "
            f"{team_id} {schedule_date}"
        )


    # --------------------------------------------------------
    # Action plan ID
    # --------------------------------------------------------

    action_plan_id = (
        f"AP-{schedule_date}-"
        f"{team_id}-{group_number:03d}"
    )


    action_plans.append(
        {
            "action_plan_id":
                action_plan_id,
            "schedule_date":
                schedule_date,
            "team_id":
                team_id,
            "job_count":
                len(rows),
            "jobs":
                "|".join(
                    route_job_ids
                ),
            "priority_sum":
                round(
                    priority_sum,
                    6,
                ),
            "priority_avg":
                round(
                    priority_avg,
                    6,
                ),
            "priority_max":
                round(
                    priority_max,
                    6,
                ),
            "priority_min":
                round(
                    priority_min,
                    6,
                ),
            "workers_required":
                (
                    round(
                        workers_required,
                        3,
                    )
                    if workers_required != ""
                    else ""
                ),
            "equipment":
                ";".join(
                    job_equipment
                ),
            "prototype_team_equipment":
                ";".join(
                    prototype_team_equipment
                ),
            "start_time":
                start_time,
            "end_time":
                final_end_time,
            "service_time_h":
                round(
                    fnum(
                        route["service_h"],
                        "route.service_h",
                    ),
                    6,
                ),
            "travel_time_h":
                round(
                    fnum(
                        route["travel_h"],
                        "route.travel_h",
                    ),
                    6,
                ),
            "total_route_time_h":
                round(
                    fnum(
                        route["total_route_h"],
                        "route.total_route_h",
                    ),
                    6,
                ),
            "distance_km":
                round(
                    fnum(
                        route["distance_km"],
                        "route.distance_km",
                    ),
                    6,
                ),
            "estimated_cost":
                round(
                    estimated_cost,
                    2,
                ),
            "route":
                route_text,
            "status":
                "READY_FOR_ACTION_PLAN",
        }
    )


# ============================================================
# ACTION PLAN VALIDATION
# ============================================================

action_plan_job_count = sum(
    r["job_count"]
    for r in action_plans
)

action_plan_group_count = len(
    action_plans
)

route_group_count = len(
    route_lookup
)

scheduled_count = len(
    scheduled_job_set
)

unscheduled_ids = {
    str(
        r["job_id"]
    ).strip()
    for r in unscheduled_rows
}

eligible_total = (
    scheduled_count
    + len(unscheduled_ids)
)

checks = []


def add_check(
    name,
    expected,
    actual,
    passed,
):

    checks.append(
        {
            "check":
                name,
            "expected":
                expected,
            "actual":
                actual,
            "status":
                "PASS"
                if passed
                else "FAIL",
        }
    )


add_check(
    "SCHEDULED_JOB_COUNT",
    238,
    scheduled_count,
    scheduled_count == 238,
)

add_check(
    "ACTION_PLAN_GROUP_COUNT",
    route_group_count,
    action_plan_group_count,
    action_plan_group_count
    == route_group_count,
)

add_check(
    "ACTION_PLAN_JOB_COUNT",
    scheduled_count,
    action_plan_job_count,
    action_plan_job_count
    == scheduled_count,
)

add_check(
    "UNSCHEDULED_JOB_COUNT",
    203,
    len(unscheduled_ids),
    len(unscheduled_ids) == 203,
)

add_check(
    "ELIGIBLE_TOTAL_ACCOUNTED",
    441,
    eligible_total,
    eligible_total == 441,
)

add_check(
    "ROUTE_GROUPS_ALL_PASS",
    0,
    sum(
        1
        for r in action_plans
        if r["status"]
        != "READY_FOR_ACTION_PLAN"
    ),
    all(
        r["status"]
        == "READY_FOR_ACTION_PLAN"
        for r in action_plans
    ),
)

add_check(
    "JOB_UNIQUENESS",
    scheduled_count,
    action_plan_job_count,
    action_plan_job_count
    == scheduled_count,
)

add_check(
    "TEAM_IDS_VALID",
    "KNOWN",
    sorted(
        {
            r["team_id"]
            for r in action_plans
        }
    ),
    all(
        r["team_id"]
        in team_master
        for r in action_plans
    ),
)


overall_pass = all(
    r["status"] == "PASS"
    for r in checks
)


# ============================================================
# WRITE ACTION PLAN CSV
# ============================================================

action_fields = [
    "action_plan_id",
    "schedule_date",
    "team_id",
    "job_count",
    "jobs",
    "priority_sum",
    "priority_avg",
    "priority_max",
    "priority_min",
    "workers_required",
    "equipment",
    "prototype_team_equipment",
    "start_time",
    "end_time",
    "service_time_h",
    "travel_time_h",
    "total_route_time_h",
    "distance_km",
    "estimated_cost",
    "route",
    "status",
]

with open(
    OUT_ACTION_PLAN,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=action_fields,
    )

    writer.writeheader()

    for row in action_plans:
        writer.writerow(row)


# ============================================================
# WRITE VALIDATION
# ============================================================

with open(
    OUT_VALIDATION,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "check",
        "expected",
        "actual",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(
        checks
    )


# ============================================================
# SUMMARY
# ============================================================

total_service_h = sum(
    r["service_time_h"]
    for r in action_plans
)

total_travel_h = sum(
    r["travel_time_h"]
    for r in action_plans
)

total_route_h = sum(
    r["total_route_time_h"]
    for r in action_plans
)

total_distance_km = sum(
    r["distance_km"]
    for r in action_plans
)

total_cost = sum(
    r["estimated_cost"]
    for r in action_plans
)

max_route = max(
    action_plans,
    key=lambda r:
        r["total_route_time_h"],
    default=None,
)


summary = {
    "status":
        "PASS"
        if overall_pass
        else "REVIEW_REQUIRED",
    "scheduled_jobs":
        scheduled_count,
    "unscheduled_jobs":
        len(unscheduled_ids),
    "eligible_jobs_accounted":
        eligible_total,
    "action_plan_groups":
        action_plan_group_count,
    "total_service_hours":
        round(
            total_service_h,
            6,
        ),
    "total_travel_hours":
        round(
            total_travel_h,
            6,
        ),
    "total_route_hours":
        round(
            total_route_h,
            6,
        ),
    "total_distance_km":
        round(
            total_distance_km,
            6,
        ),
    "total_estimated_cost":
        round(
            total_cost,
            2,
        ),
    "max_route":
        max_route,
    "validation":
        {
            r["check"]:
                r["status"]
            for r in checks
        },
    "outputs":
        {
            "action_plan":
                str(OUT_ACTION_PLAN),
            "report":
                str(OUT_REPORT),
            "validation":
                str(OUT_VALIDATION),
            "summary":
                str(OUT_SUMMARY),
        },
}

with open(
    OUT_SUMMARY,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        summary,
        f,
        indent=2,
    )


# ============================================================
# WRITE HUMAN-READABLE REPORT
# ============================================================

lines = []

lines.append(
    "# CivicBrain Step 13 — Action Plan"
)

lines.append("")

lines.append(
    "## Summary"
)

lines.append("")

lines.append(
    f"- Scheduled jobs: **{scheduled_count}**"
)

lines.append(
    f"- Unscheduled jobs: **{len(unscheduled_ids)}**"
)

lines.append(
    f"- Action-plan groups: **{action_plan_group_count}**"
)

lines.append(
    f"- Total service time: **{total_service_h:.3f} h**"
)

lines.append(
    f"- Total travel time: **{total_travel_h:.3f} h**"
)

lines.append(
    f"- Total route time: **{total_route_h:.3f} h**"
)

lines.append(
    f"- Total road distance: **{total_distance_km:.3f} km**"
)

lines.append(
    f"- Total estimated cost: **₹{total_cost:,.2f}**"
)

lines.append("")

lines.append(
    "## Route Action Plans"
)

lines.append("")

lines.append(
    "| Date | Team | Jobs | Start | End | "
    "Service h | Travel h | Total h | "
    "Distance km | Cost ₹ | Status |"
)

lines.append(
    "|---|---|---:|---|---|---:|---:|---:|---:|---:|---|"
)

for r in action_plans:

    lines.append(
        "| "
        + r["schedule_date"]
        + " | "
        + r["team_id"]
        + " | "
        + str(r["job_count"])
        + " | "
        + r["start_time"]
        + " | "
        + r["end_time"]
        + " | "
        + f"{r['service_time_h']:.3f}"
        + " | "
        + f"{r['travel_time_h']:.3f}"
        + " | "
        + f"{r['total_route_time_h']:.3f}"
        + " | "
        + f"{r['distance_km']:.3f}"
        + " | "
        + f"{r['estimated_cost']:.2f}"
        + " | "
        + r["status"]
        + " |"
    )

lines.append("")

lines.append(
    "## Validation"
)

lines.append("")

for r in checks:

    lines.append(
        f"- `{r['check']}`: **{r['status']}** "
        f"(expected={r['expected']}, actual={r['actual']})"
    )

lines.append("")

lines.append(
    f"**Overall status: "
    f"{'PASS' if overall_pass else 'REVIEW_REQUIRED'}**"
)

if max_route:

    lines.append("")

    lines.append(
        "## Maximum Route"
    )

    lines.append("")

    lines.append(
        f"- Team: `{max_route['team_id']}`"
    )

    lines.append(
        f"- Date: `{max_route['schedule_date']}`"
    )

    lines.append(
        f"- Jobs: `{max_route['job_count']}`"
    )

    lines.append(
        f"- Total route time: `{max_route['total_route_time_h']:.3f} h`"
    )

    lines.append(
        f"- Finish: `{max_route['end_time']}`"
    )


with open(
    OUT_REPORT,
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "\n".join(lines)
    )


# ============================================================
# CONSOLE
# ============================================================

print("=" * 80)
print("CIVICBRAIN STEP 13 — ACTION PLAN")
print("=" * 80)

print(
    f"Scheduled jobs       : "
    f"{scheduled_count}"
)

print(
    f"Unscheduled jobs     : "
    f"{len(unscheduled_ids)}"
)

print(
    f"Action-plan groups   : "
    f"{action_plan_group_count}"
)

print(
    f"Service hours        : "
    f"{total_service_h:.3f}"
)

print(
    f"Travel hours         : "
    f"{total_travel_h:.3f}"
)

print(
    f"Total route hours    : "
    f"{total_route_h:.3f}"
)

print(
    f"Total distance       : "
    f"{total_distance_km:.3f} km"
)

print(
    f"Estimated cost       : "
    f"₹{total_cost:,.2f}"
)

if max_route:

    print()
    print("MAXIMUM ROUTE")
    print("-" * 80)

    print(
        f"Team                : "
        f"{max_route['team_id']}"
    )

    print(
        f"Date                : "
        f"{max_route['schedule_date']}"
    )

    print(
        f"Jobs                : "
        f"{max_route['job_count']}"
    )

    print(
        f"Total route hours   : "
        f"{max_route['total_route_time_h']:.3f}"
    )

    print(
        f"Finish              : "
        f"{max_route['end_time']}"
    )


print()
print("VALIDATION")
print("-" * 80)

for r in checks:

    print(
        f"{r['check']:<35}"
        f"{r['status']}"
    )

print()
print(
    "OVERALL STATUS : "
    + (
        "PASS"
        if overall_pass
        else "REVIEW_REQUIRED"
    )
)

print()
print("OUTPUTS")
print("-" * 80)

print(
    f"Action Plan : {OUT_ACTION_PLAN}"
)

print(
    f"Report      : {OUT_REPORT}"
)

print(
    f"Validation  : {OUT_VALIDATION}"
)

print(
    f"Summary     : {OUT_SUMMARY}"
)

print()
print("=" * 80)
print("ACTION PLAN BUILD COMPLETE")
print("=" * 80)
