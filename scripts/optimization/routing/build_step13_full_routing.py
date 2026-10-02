import csv
import json
from pathlib import Path
from collections import defaultdict

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

ROOT = Path(".")

NODE_FILE = ROOT / "data/optimization/routing/route_group_nodes.csv"
DIST_FILE = ROOT / "data/optimization/routing/route_distance_matrix.csv"
TIME_FILE = ROOT / "data/optimization/routing/route_time_matrix.csv"
JOBS_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"

OUT_DIR = ROOT / "data/optimization/routing"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ROUTE_FILE = OUT_DIR / "route_results.csv"
VALIDATION_FILE = OUT_DIR / "routing_validation.csv"
SUMMARY_FILE = OUT_DIR / "routing_summary.json"

# ------------------------------------------------------------
# Load inputs
# ------------------------------------------------------------

with open(NODE_FILE, encoding="utf-8-sig") as f:
    node_rows = list(csv.DictReader(f))

with open(DIST_FILE, encoding="utf-8-sig") as f:
    distance_rows = list(csv.DictReader(f))

with open(TIME_FILE, encoding="utf-8-sig") as f:
    time_rows = list(csv.DictReader(f))

with open(JOBS_FILE, encoding="utf-8-sig") as f:
    jobs = {r["job_id"]: r for r in csv.DictReader(f)}

# ------------------------------------------------------------
# Group nodes
# ------------------------------------------------------------

groups = defaultdict(list)

for r in node_rows:
    groups[r["group_index"]].append(r)

groups = dict(sorted(groups.items(), key=lambda x: int(x[0])))

if len(groups) != 105:
    raise RuntimeError(
        f"Expected 105 routing groups, found {len(groups)}"
    )

# ------------------------------------------------------------
# Build matrix lookup
# ------------------------------------------------------------

distance_lookup = {}

for r in distance_rows:
    key = (
        r["group_index"],
        int(r["from_node_index"]),
        int(r["to_node_index"]),
    )
    distance_lookup[key] = float(r["distance_m"])

time_lookup = {}

for r in time_rows:
    key = (
        r["group_index"],
        int(r["from_node_index"]),
        int(r["to_node_index"]),
    )
    time_lookup[key] = float(r["travel_time_s"])

# ------------------------------------------------------------
# Outputs
# ------------------------------------------------------------

route_results = []
validation_results = []

total_jobs_routed = 0
total_distance_m = 0.0
total_travel_time_s = 0.0
successful_groups = 0

# ------------------------------------------------------------
# Route every team/date group independently
# ------------------------------------------------------------

for group_index, nodes in groups.items():

    nodes.sort(key=lambda x: int(x["node_index"]))

    n = len(nodes)

    # node 0 must be depot
    if nodes[0]["node_type"] != "DEPOT":
        raise RuntimeError(
            f"Group {group_index}: node 0 is not depot"
        )

    node_indices = [int(x["node_index"]) for x in nodes]

    if node_indices != list(range(n)):
        raise RuntimeError(
            f"Group {group_index}: invalid node indices {node_indices}"
        )

    # --------------------------------------------------------
    # Construct matrix
    # --------------------------------------------------------

    matrix = [[0] * n for _ in range(n)]

    time_matrix = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):

            dkey = (group_index, i, j)
            tkey = (group_index, i, j)

            if dkey not in distance_lookup:
                raise RuntimeError(
                    f"Group {group_index}: missing distance [{i}][{j}]"
                )

            if tkey not in time_lookup:
                raise RuntimeError(
                    f"Group {group_index}: missing time [{i}][{j}]"
                )

            matrix[i][j] = int(
                round(distance_lookup[dkey])
            )

            time_matrix[i][j] = time_lookup[tkey]

    # --------------------------------------------------------
    # RoutingModel
    # --------------------------------------------------------

    manager = pywrapcp.RoutingIndexManager(
        n,
        1,
        0
    )

    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return matrix[from_node][to_node]

    transit_callback = routing.RegisterTransitCallback(
        distance_callback
    )

    routing.SetArcCostEvaluatorOfAllVehicles(
        transit_callback
    )

    params = pywrapcp.DefaultRoutingSearchParameters()

    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )

    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)

    if solution is None:
        raise RuntimeError(
            f"Group {group_index}: RoutingModel found no solution"
        )

    # --------------------------------------------------------
    # Extract route
    # --------------------------------------------------------

    index = routing.Start(0)

    route_nodes = []

    route_distance = 0.0
    route_travel_time = 0.0

    while not routing.IsEnd(index):

        current_node = manager.IndexToNode(index)

        next_index = solution.Value(
            routing.NextVar(index)
        )

        next_node = manager.IndexToNode(next_index)

        route_nodes.append(current_node)

        route_distance += matrix[current_node][next_node]

        route_travel_time += time_matrix[
            current_node
        ][next_node]

        index = next_index

    # Add final depot
    route_nodes.append(
        manager.IndexToNode(index)
    )

    # --------------------------------------------------------
    # Validate route structure
    # --------------------------------------------------------

    expected_job_nodes = {
        int(x["node_index"])
        for x in nodes
        if x["node_type"] == "JOB"
    }

    actual_job_nodes = {
        x for x in route_nodes
        if x != 0
    }

    validation = {
        "group_index": group_index,
        "team_id": nodes[0]["team_id"],
        "schedule_date": nodes[0]["schedule_date"],
        "start_depot": route_nodes[0] == 0,
        "end_depot": route_nodes[-1] == 0,
        "all_jobs_visited":
            actual_job_nodes == expected_job_nodes,
        "job_visit_count":
            len([x for x in route_nodes if x != 0]),
        "expected_job_count":
            len(expected_job_nodes),
        "no_duplicate_job_visit":
            len(
                [x for x in route_nodes if x != 0]
            ) == len(actual_job_nodes),
        "distance_m": route_distance,
        "travel_time_s": route_travel_time,
    }

    validation["status"] = (
        "PASS"
        if (
            validation["start_depot"]
            and validation["end_depot"]
            and validation["all_jobs_visited"]
            and validation["no_duplicate_job_visit"]
        )
        else "FAIL"
    )

    validation_results.append(validation)

    if validation["status"] != "PASS":
        raise RuntimeError(
            f"Group {group_index}: route validation failed"
        )

    # --------------------------------------------------------
    # Write route legs / nodes
    # --------------------------------------------------------

    for route_position, node_index in enumerate(
        route_nodes,
        start=1
    ):

        node = nodes[node_index]

        distance_from_previous = 0.0
        time_from_previous = 0.0

        if route_position > 1:

            previous_node_index = route_nodes[
                route_position - 2
            ]

            distance_from_previous = matrix[
                previous_node_index
            ][node_index]

            time_from_previous = time_matrix[
                previous_node_index
            ][node_index]

        service_duration_h = 0.0

        if node["node_type"] == "JOB":
            job_id = node["job_id"]

            if job_id not in jobs:
                raise RuntimeError(
                    f"Job {job_id} missing from eligible_jobs"
                )

            service_duration_h = float(
                jobs[job_id]["service_duration_hours"]
            )

        route_results.append(
            {
                "group_index": group_index,
                "team_id": node["team_id"],
                "schedule_date": node["schedule_date"],
                "route_sequence": route_position,
                "node_index": node_index,
                "node_type": node["node_type"],
                "job_id": node["job_id"],
                "latitude": node["latitude"],
                "longitude": node["longitude"],
                "travel_distance_m":
                    distance_from_previous,
                "travel_time_s":
                    time_from_previous,
                "service_duration_h":
                    service_duration_h,
            }
        )

    total_jobs_routed += len(expected_job_nodes)
    total_distance_m += route_distance
    total_travel_time_s += route_travel_time
    successful_groups += 1

# ------------------------------------------------------------
# Write route results
# ------------------------------------------------------------

with open(
    ROUTE_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = [
        "group_index",
        "team_id",
        "schedule_date",
        "route_sequence",
        "node_index",
        "node_type",
        "job_id",
        "latitude",
        "longitude",
        "travel_distance_m",
        "travel_time_s",
        "service_duration_h",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(route_results)

# ------------------------------------------------------------
# Write validation
# ------------------------------------------------------------

with open(
    VALIDATION_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    fieldnames = list(
        validation_results[0].keys()
    )

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(validation_results)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

summary = {
    "step": "13_routing_model",
    "routing_method": "OR-Tools RoutingModel",
    "objective": "minimize total road distance",
    "routing_groups": len(groups),
    "successful_groups": successful_groups,
    "scheduled_jobs_routed": total_jobs_routed,
    "total_distance_m": total_distance_m,
    "total_distance_km": total_distance_m / 1000.0,
    "total_travel_time_s": total_travel_time_s,
    "total_travel_time_min": total_travel_time_s / 60.0,
    "validation_status":
        "PASS"
        if all(
            x["status"] == "PASS"
            for x in validation_results
        )
        else "FAIL",
    "outputs": {
        "route_results": str(ROUTE_FILE),
        "routing_validation": str(VALIDATION_FILE),
        "routing_summary": str(SUMMARY_FILE),
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
# Console summary
# ------------------------------------------------------------

print("=" * 80)
print("CIVICBRAIN STEP 13 — FULL OR-TOOLS ROUTING")
print("=" * 80)

print("Routing groups       :", len(groups))
print("Successful groups    :", successful_groups)
print("Jobs routed          :", total_jobs_routed)
print(
    "Total distance       :",
    round(total_distance_m, 2),
    "m"
)
print(
    "Total distance       :",
    round(total_distance_m / 1000, 3),
    "km"
)
print(
    "Total travel time    :",
    round(total_travel_time_s / 60.0, 2),
    "minutes"
)

print()
print("VALIDATION")
print("-" * 80)

failed = [
    x for x in validation_results
    if x["status"] != "PASS"
]

print(
    "Groups validated     :",
    len(validation_results)
)
print(
    "Groups passed        :",
    len(validation_results) - len(failed)
)
print(
    "Groups failed        :",
    len(failed)
)

print()
print(
    "OR-TOOLS ROUTING GATE:",
    "PASS" if not failed else "FAIL"
)

print()
print("Route results        :", ROUTE_FILE)
print("Validation           :", VALIDATION_FILE)
print("Summary              :", SUMMARY_FILE)
