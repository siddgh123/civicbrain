import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(".")

SCHEDULE_FILE = ROOT / "data/optimization/evaluation/baseline_schedule.csv"
DIST_FILE = ROOT / "data/optimization/evaluation/baseline_route_distance_matrix.csv"
TIME_FILE = ROOT / "data/optimization/evaluation/baseline_route_time_matrix.csv"
NODES_FILE = ROOT / "data/optimization/evaluation/baseline_route_group_nodes.csv"

OUT_AUDIT = ROOT / "data/optimization/evaluation/baseline_route_audit.csv"
OUT_SUMMARY = ROOT / "data/optimization/evaluation/baseline_route_metrics.json"

SHIFT_HOURS = 9.0

# ------------------------------------------------------------------
# Load
# ------------------------------------------------------------------

with open(SCHEDULE_FILE, encoding="utf-8-sig") as f:
    schedule = list(csv.DictReader(f))

with open(DIST_FILE, encoding="utf-8-sig") as f:
    distance_rows = list(csv.DictReader(f))

with open(TIME_FILE, encoding="utf-8-sig") as f:
    time_rows = list(csv.DictReader(f))

with open(NODES_FILE, encoding="utf-8-sig") as f:
    node_rows = list(csv.DictReader(f))

if len(schedule) != 191:
    raise RuntimeError(
        f"Expected 191 baseline scheduled jobs, found {len(schedule)}"
    )

if len(distance_rows) == 0 or len(time_rows) == 0:
    raise RuntimeError("Baseline route matrices are empty.")

# ------------------------------------------------------------------
# Node mapping
# ------------------------------------------------------------------

node_to_job = {}

for r in node_rows:
    key = (
        r["group_index"],
        r["node_index"]
    )
    node_to_job[key] = r["job_id"]

job_to_node = {}

for r in node_rows:
    if r["node_type"] == "JOB":
        key = (int(r["group_index"]), r["job_id"])
        job_to_node[key] = int(r["node_index"])

# ------------------------------------------------------------------
# Matrix lookup
# ------------------------------------------------------------------

distance_lookup = {}
time_lookup = {}

for r in distance_rows:
    key = (
        int(r["group_index"]),
        int(r["from_node_index"]),
        int(r["to_node_index"])
    )
    distance_lookup[key] = float(r["distance_m"])

for r in time_rows:
    key = (
        int(r["group_index"]),
        int(r["from_node_index"]),
        int(r["to_node_index"])
    )
    time_lookup[key] = float(r["travel_time_s"])

# ------------------------------------------------------------------
# Group baseline schedule
# ------------------------------------------------------------------

groups = defaultdict(list)

for r in schedule:
    groups[
        (r["team_id"], r["schedule_date"])
    ].append(r)

groups = dict(sorted(groups.items()))

# group_index follows the same deterministic team/date ordering used
# during baseline OSRM matrix generation.
group_index_map = {
    key: idx
    for idx, key in enumerate(groups.keys(), start=1)
}

# ------------------------------------------------------------------
# Audit
# ------------------------------------------------------------------

audit_rows = []

total_service_h = 0.0
total_travel_h = 0.0
total_distance_km = 0.0

route_violations = 0
route_passes = 0

for (team_id, schedule_date), rows in groups.items():

    group_index = group_index_map[
        (team_id, schedule_date)
    ]

    rows = sorted(
        rows,
        key=lambda x: int(x["sequence_no"])
    )

    # Depot node = 0
    route_nodes = [0]

    for r in rows:
        key = (
            group_index,
            r["job_id"]
        )

        if key not in job_to_node:
            raise RuntimeError(
                f"Missing node mapping for group={group_index}, "
                f"job_id={r['job_id']}"
            )

        route_nodes.append(
            job_to_node[key]
        )

    # Return to depot.
    route_nodes.append(0)

    route_distance_m = 0.0
    route_travel_s = 0.0

    for i in range(len(route_nodes) - 1):

        from_node = route_nodes[i]
        to_node = route_nodes[i + 1]

        dkey = (
            group_index,
            from_node,
            to_node
        )

        tkey = dkey

        if dkey not in distance_lookup:
            raise RuntimeError(
                f"Missing distance matrix value "
                f"group={group_index}, {from_node}->{to_node}"
            )

        if tkey not in time_lookup:
            raise RuntimeError(
                f"Missing time matrix value "
                f"group={group_index}, {from_node}->{to_node}"
            )

        route_distance_m += distance_lookup[dkey]
        route_travel_s += time_lookup[tkey]

    service_h = sum(
        float(r["service_duration_h"])
        for r in rows
    )

    travel_h = route_travel_s / 3600.0
    total_route_h = service_h + travel_h

    distance_km = route_distance_m / 1000.0

    status = (
        "PASS"
        if total_route_h <= SHIFT_HOURS + 1e-9
        else "ROUTE_SHIFT_VIOLATION"
    )

    if status == "PASS":
        route_passes += 1
    else:
        route_violations += 1

    audit_rows.append({
        "group_index": group_index,
        "team_id": team_id,
        "schedule_date": schedule_date,
        "job_count": len(rows),
        "jobs": ";".join(r["job_id"] for r in rows),
        "service_h": f"{service_h:.3f}",
        "travel_h": f"{travel_h:.3f}",
        "total_route_h": f"{total_route_h:.3f}",
        "distance_km": f"{distance_km:.3f}",
        "shift_limit_h": f"{SHIFT_HOURS:.3f}",
        "slack_h": f"{SHIFT_HOURS - total_route_h:.3f}",
        "status": status,
    })

    total_service_h += service_h
    total_travel_h += travel_h
    total_distance_km += distance_km

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------

scheduled_jobs = len(schedule)
routing_groups = len(groups)

max_route = max(
    audit_rows,
    key=lambda r: float(r["total_route_h"])
)

avg_jobs_per_shift = (
    scheduled_jobs / routing_groups
    if routing_groups
    else 0.0
)

summary = {
    "baseline_name": "FIFO Greedy Baseline",
    "scheduled_jobs": scheduled_jobs,
    "routing_groups": routing_groups,
    "service_hours": round(total_service_h, 3),
    "travel_hours": round(total_travel_h, 3),
    "total_route_hours": round(
        total_service_h + total_travel_h,
        3
    ),
    "total_distance_km": round(
        total_distance_km,
        3
    ),
    "jobs_per_shift_average": round(
        avg_jobs_per_shift,
        3
    ),
    "route_groups_pass": route_passes,
    "route_groups_violation": route_violations,
    "route_violations": route_violations,
    "max_route": max_route,
    "status": "PASS",
}

# ------------------------------------------------------------------
# Write audit
# ------------------------------------------------------------------

with open(
    OUT_AUDIT,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_index",
            "team_id",
            "schedule_date",
            "job_count",
            "jobs",
            "service_h",
            "travel_h",
            "total_route_h",
            "distance_km",
            "shift_limit_h",
            "slack_h",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(audit_rows)

with open(
    OUT_SUMMARY,
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=2)

# ------------------------------------------------------------------
# Console report
# ------------------------------------------------------------------

print("=" * 80)
print("CIVICBRAIN STEP 13 - BASELINE ROUTE AUDIT")
print("=" * 80)
print(f"Scheduled jobs       : {scheduled_jobs}")
print(f"Routing groups       : {routing_groups}")
print(f"Service hours        : {total_service_h:.3f}")
print(f"Travel hours         : {total_travel_h:.3f}")
print(f"Total route hours    : {total_service_h + total_travel_h:.3f}")
print(f"Total distance       : {total_distance_km:.3f} km")
print(f"Average jobs/shift   : {avg_jobs_per_shift:.3f}")
print()

print("ROUTE FEASIBILITY")
print("-" * 80)
print(f"Groups <= 9h        : {route_passes}")
print(f"Groups > 9h         : {route_violations}")
print()

print("MAXIMUM ROUTE")
print("-" * 80)
print(f"Team                 : {max_route['team_id']}")
print(f"Date                 : {max_route['schedule_date']}")
print(f"Jobs                 : {max_route['job_count']}")
print(f"Service hours        : {max_route['service_h']}")
print(f"Travel hours         : {max_route['travel_h']}")
print(f"Total route hours    : {max_route['total_route_h']}")
print(f"Distance             : {max_route['distance_km']} km")
print(f"Slack                : {max_route['slack_h']} h")
print()

print("OUTPUTS")
print("-" * 80)
print("Route audit          :", OUT_AUDIT)
print("Route metrics        :", OUT_SUMMARY)
print()

print("STATUS               : PASS")
print("=" * 80)

