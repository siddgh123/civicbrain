import csv
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(".")

ROUTE_FILE = ROOT / "data/optimization/routing/route_results.csv"

OUT_DIR = ROOT / "data/optimization/routing"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_FILE = OUT_DIR / "final_schedule_route_audit.csv"
SUMMARY_FILE = OUT_DIR / "final_schedule_route_audit_summary.json"

SHIFT_START = datetime.strptime("08:00", "%H:%M")
SHIFT_HOURS = 9.0

# ------------------------------------------------------------
# Load route results
# ------------------------------------------------------------

with open(ROUTE_FILE, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise RuntimeError("route_results.csv is empty")

required_columns = {
    "group_index",
    "team_id",
    "schedule_date",
    "route_sequence",
    "node_type",
    "job_id",
    "travel_time_s",
    "service_duration_h",
}

missing_columns = required_columns - set(rows[0].keys())

if missing_columns:
    raise RuntimeError(
        f"Missing required columns: {sorted(missing_columns)}"
    )

# ------------------------------------------------------------
# Group routes
# ------------------------------------------------------------

groups = defaultdict(list)

for row in rows:
    groups[row["group_index"]].append(row)

# ------------------------------------------------------------
# Audit
# ------------------------------------------------------------

audit_rows = []
failed_groups = []

total_jobs = 0
total_service_h = 0.0
total_travel_h = 0.0

for group_index, group_rows in sorted(
    groups.items(),
    key=lambda x: int(x[0])
):
    group_rows = sorted(
        group_rows,
        key=lambda x: int(x["route_sequence"])
    )

    team_id = group_rows[0]["team_id"]
    schedule_date = group_rows[0]["schedule_date"]

    # --------------------------------------------------------
    # Route structure
    # --------------------------------------------------------

    first_is_depot = group_rows[0]["node_type"] == "DEPOT"
    last_is_depot = group_rows[-1]["node_type"] == "DEPOT"

    job_rows = [
        r for r in group_rows
        if r["node_type"] == "JOB"
    ]

    job_ids = [r["job_id"] for r in job_rows]

    no_duplicate_jobs = (
        len(job_ids) == len(set(job_ids))
    )

    # --------------------------------------------------------
    # Time calculations
    # --------------------------------------------------------

    service_h = sum(
        float(r["service_duration_h"])
        for r in job_rows
    )

    travel_h = sum(
        float(r["travel_time_s"]) / 3600.0
        for r in group_rows
    )

    total_h = service_h + travel_h

    finish_time = SHIFT_START + timedelta(
        hours=total_h
    )

    shift_feasible = total_h <= SHIFT_HOURS

    route_valid = (
        first_is_depot
        and last_is_depot
        and no_duplicate_jobs
    )

    status = (
        "PASS"
        if route_valid and shift_feasible
        else "TRAVEL_TIME_VIOLATION"
        if route_valid and not shift_feasible
        else "ROUTE_STRUCTURE_ERROR"
    )

    audit_rows.append(
        {
            "group_index": group_index,
            "team_id": team_id,
            "schedule_date": schedule_date,
            "job_count": len(job_rows),
            "service_duration_h": round(service_h, 3),
            "travel_time_h": round(travel_h, 3),
            "total_route_time_h": round(total_h, 3),
            "shift_limit_h": SHIFT_HOURS,
            "calculated_finish_time": finish_time.strftime("%H:%M"),
            "start_at_depot": first_is_depot,
            "end_at_depot": last_is_depot,
            "no_duplicate_job": no_duplicate_jobs,
            "status": status,
        }
    )

    if status != "PASS":
        failed_groups.append(
            {
                "group_index": group_index,
                "team_id": team_id,
                "schedule_date": schedule_date,
                "job_count": len(job_rows),
                "service_duration_h": round(service_h, 3),
                "travel_time_h": round(travel_h, 3),
                "total_route_time_h": round(total_h, 3),
                "calculated_finish_time": finish_time.strftime("%H:%M"),
                "status": status,
            }
        )

    total_jobs += len(job_rows)
    total_service_h += service_h
    total_travel_h += travel_h

# ------------------------------------------------------------
# Save audit CSV
# ------------------------------------------------------------

with open(
    AUDIT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = [
        "group_index",
        "team_id",
        "schedule_date",
        "job_count",
        "service_duration_h",
        "travel_time_h",
        "total_route_time_h",
        "shift_limit_h",
        "calculated_finish_time",
        "start_at_depot",
        "end_at_depot",
        "no_duplicate_job",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(audit_rows)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

passed_groups = sum(
    1
    for r in audit_rows
    if r["status"] == "PASS"
)

travel_violations = sum(
    1
    for r in audit_rows
    if r["status"] == "TRAVEL_TIME_VIOLATION"
)

route_errors = sum(
    1
    for r in audit_rows
    if r["status"] == "ROUTE_STRUCTURE_ERROR"
)

max_route = max(
    audit_rows,
    key=lambda r: float(r["total_route_time_h"])
)

summary = {
    "step": "13_final_route_shift_audit",
    "groups_total": len(audit_rows),
    "groups_passed": passed_groups,
    "travel_time_violations": travel_violations,
    "route_structure_errors": route_errors,
    "jobs_audited": total_jobs,
    "total_service_h": round(total_service_h, 3),
    "total_travel_h": round(total_travel_h, 3),
    "max_route_group": {
        "group_index": max_route["group_index"],
        "team_id": max_route["team_id"],
        "schedule_date": max_route["schedule_date"],
        "job_count": max_route["job_count"],
        "total_route_time_h": max_route["total_route_time_h"],
        "finish_time": max_route["calculated_finish_time"],
    },
    "overall_status":
        "PASS"
        if len(failed_groups) == 0
        else "REVIEW_REQUIRED",
    "outputs": {
        "audit_csv": str(AUDIT_FILE),
        "summary_json": str(SUMMARY_FILE),
    },
}

with open(
    SUMMARY_FILE,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        summary,
        f,
        indent=2
    )

# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("=" * 80)
print("CIVICBRAIN STEP 13 — FINAL ROUTE / SHIFT AUDIT")
print("=" * 80)

print("Groups total          :", len(audit_rows))
print("Groups passed         :", passed_groups)
print("Travel violations    :", travel_violations)
print("Route errors          :", route_errors)
print("Jobs audited          :", total_jobs)
print()

print("TOTAL SERVICE HOURS   :", round(total_service_h, 3))
print("TOTAL TRAVEL HOURS    :", round(total_travel_h, 3))
print()

print("MAX ROUTE")
print("-" * 80)
print("Group                 :", max_route["group_index"])
print("Team                  :", max_route["team_id"])
print("Date                  :", max_route["schedule_date"])
print("Jobs                  :", max_route["job_count"])
print("Total route hours     :", max_route["total_route_time_h"])
print("Calculated finish     :", max_route["calculated_finish_time"])

print()
print("FAILED / REVIEW GROUPS")
print("-" * 80)

if failed_groups:
    for r in sorted(
        failed_groups,
        key=lambda x: x["total_route_time_h"],
        reverse=True
    ):
        print(
            r["group_index"],
            r["team_id"],
            r["schedule_date"],
            "jobs=", r["job_count"],
            "service_h=", r["service_duration_h"],
            "travel_h=", r["travel_time_h"],
            "total_h=", r["total_route_time_h"],
            "finish=", r["calculated_finish_time"],
            "status=", r["status"],
        )
else:
    print("None")

print()
print("=" * 80)
print(
    "FINAL ROUTE / SHIFT AUDIT:",
    "PASS" if not failed_groups else "REVIEW_REQUIRED"
)
print("=" * 80)

print("Audit CSV :", AUDIT_FILE)
print("Summary   :", SUMMARY_FILE)
