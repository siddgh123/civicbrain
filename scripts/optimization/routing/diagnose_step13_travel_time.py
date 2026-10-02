import csv
import itertools
from collections import defaultdict
from pathlib import Path

ROOT = Path(".")

ROUTE_FILE = ROOT / "data/optimization/routing/route_results.csv"
NODE_FILE = ROOT / "data/optimization/routing/route_group_nodes.csv"
TIME_FILE = ROOT / "data/optimization/routing/route_time_matrix.csv"

OUT_FILE = ROOT / "data/optimization/routing/travel_time_route_diagnostic.csv"

SHIFT_HOURS = 9.0

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

with open(ROUTE_FILE, encoding="utf-8-sig") as f:
    route_rows = list(csv.DictReader(f))

with open(NODE_FILE, encoding="utf-8-sig") as f:
    node_rows = list(csv.DictReader(f))

with open(TIME_FILE, encoding="utf-8-sig") as f:
    time_rows = list(csv.DictReader(f))

# ------------------------------------------------------------
# Group nodes
# ------------------------------------------------------------

nodes_by_group = defaultdict(list)

for r in node_rows:
    nodes_by_group[r["group_index"]].append(r)

# ------------------------------------------------------------
# Build OSRM time lookup
# ------------------------------------------------------------

time_lookup = {}

for r in time_rows:
    key = (
        r["group_index"],
        int(r["from_node_index"]),
        int(r["to_node_index"]),
    )
    time_lookup[key] = float(r["travel_time_s"])

# ------------------------------------------------------------
# Current route information
# ------------------------------------------------------------

route_by_group = defaultdict(list)

for r in route_rows:
    route_by_group[r["group_index"]].append(r)

results = []

# ------------------------------------------------------------
# Analyze every group
# ------------------------------------------------------------

for group_index, rows in sorted(
    nodes_by_group.items(),
    key=lambda x: int(x[0])
):

    rows = sorted(
        rows,
        key=lambda x: int(x["node_index"])
    )

    job_nodes = [
        int(r["node_index"])
        for r in rows
        if r["node_type"] == "JOB"
    ]

    service_hours = sum(
        float(r["service_duration_h"])
        for r in route_by_group[group_index]
        if r["node_type"] == "JOB"
    )

    # Current route travel time
    current_travel_seconds = sum(
        float(r["travel_time_s"])
        for r in route_by_group[group_index]
    )

    current_travel_hours = current_travel_seconds / 3600.0

    current_total_hours = (
        service_hours +
        current_travel_hours
    )

    # --------------------------------------------------------
    # Find exact minimum travel-time route
    # --------------------------------------------------------

    best_order = None
    best_travel_seconds = None

    for permutation in itertools.permutations(job_nodes):

        route = [0] + list(permutation) + [0]

        travel_seconds = 0.0

        for i in range(len(route) - 1):

            frm = route[i]
            to = route[i + 1]

            key = (
                group_index,
                frm,
                to
            )

            if key not in time_lookup:
                raise RuntimeError(
                    f"Missing time matrix value "
                    f"for group={group_index}, "
                    f"{frm}->{to}"
                )

            travel_seconds += time_lookup[key]

        if (
            best_travel_seconds is None
            or travel_seconds < best_travel_seconds
        ):
            best_travel_seconds = travel_seconds
            best_order = permutation

    best_travel_hours = (
        best_travel_seconds / 3600.0
    )

    best_total_hours = (
        service_hours +
        best_travel_hours
    )

    current_violation = (
        current_total_hours > SHIFT_HOURS
    )

    best_feasible = (
        best_total_hours <= SHIFT_HOURS
    )

    if not current_violation:
        action = "ALREADY_FEASIBLE"

    elif best_feasible:
        action = "ROUTE_REORDER_CAN_FIX"

    else:
        action = "SPLIT_OR_RESCHEDULE_REQUIRED"

    team_id = rows[0]["team_id"]
    schedule_date = rows[0]["schedule_date"]

    results.append(
        {
            "group_index": group_index,
            "team_id": team_id,
            "schedule_date": schedule_date,
            "job_count": len(job_nodes),
            "service_duration_h": round(
                service_hours, 3
            ),
            "current_travel_h": round(
                current_travel_hours, 3
            ),
            "current_total_h": round(
                current_total_hours, 3
            ),
            "best_travel_h": round(
                best_travel_hours, 3
            ),
            "best_total_h": round(
                best_total_hours, 3
            ),
            "current_violation": current_violation,
            "best_route_feasible": best_feasible,
            "current_finish_h": round(
                current_total_hours, 3
            ),
            "best_finish_h": round(
                best_total_hours, 3
            ),
            "best_job_order": "->".join(
                str(x) for x in best_order
            ),
            "action": action,
        }
    )

# ------------------------------------------------------------
# Write diagnostic
# ------------------------------------------------------------

with open(
    OUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = list(results[0].keys())

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(results)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

violations = [
    r for r in results
    if r["current_violation"]
]

already_feasible = [
    r for r in results
    if r["action"] == "ALREADY_FEASIBLE"
]

reorder_fix = [
    r for r in results
    if r["action"] == "ROUTE_REORDER_CAN_FIX"
]

reschedule_required = [
    r for r in results
    if r["action"] == "SPLIT_OR_RESCHEDULE_REQUIRED"
]

service_exact_9 = [
    r for r in violations
    if abs(r["service_duration_h"] - 9.0) < 0.0001
]

print("=" * 80)
print("CIVICBRAIN STEP 13 — TRAVEL-TIME ROUTE DIAGNOSTIC")
print("=" * 80)

print("Groups total                 :", len(results))
print("Already feasible             :", len(already_feasible))
print("Current violations           :", len(violations))
print("Service exactly 9h           :", len(service_exact_9))
print("Can fix by route reorder     :", len(reorder_fix))
print("Require split/reschedule     :", len(reschedule_required))

print()
print("VIOLATING GROUP ANALYSIS")
print("-" * 80)

for r in sorted(
    violations,
    key=lambda x: x["best_total_h"],
    reverse=True
):
    print(
        f'Group {r["group_index"]:>3} | '
        f'{r["team_id"]} | '
        f'{r["schedule_date"]} | '
        f'jobs={r["job_count"]} | '
        f'service={r["service_duration_h"]:.3f}h | '
        f'current={r["current_total_h"]:.3f}h | '
        f'best={r["best_total_h"]:.3f}h | '
        f'{r["action"]}'
    )

print()
print("=" * 80)
print("TRAVEL-TIME ROUTE DIAGNOSTIC COMPLETE")
print("=" * 80)

print("Output :", OUT_FILE)
