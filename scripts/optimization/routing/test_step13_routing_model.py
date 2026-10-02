import csv
from pathlib import Path

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

ROOT = Path(".")

DIST_FILE = ROOT / "data/optimization/routing/route_distance_matrix.csv"
NODE_FILE = ROOT / "data/optimization/routing/route_group_nodes.csv"

TEAM_ID = "T001"
SCHEDULE_DATE = "2026-09-28"

# ------------------------------------------------------------
# Load routing nodes
# ------------------------------------------------------------

with open(NODE_FILE, encoding="utf-8-sig") as f:
    all_nodes = list(csv.DictReader(f))

nodes = [
    r for r in all_nodes
    if r["team_id"] == TEAM_ID
    and r["schedule_date"] == SCHEDULE_DATE
]

nodes.sort(key=lambda r: int(r["node_index"]))

if not nodes:
    raise RuntimeError("No routing nodes found")

node_indices = [int(r["node_index"]) for r in nodes]

if node_indices != list(range(len(nodes))):
    raise RuntimeError(
        f"Node indices are not contiguous: {node_indices}"
    )

# ------------------------------------------------------------
# Load distance matrix
# ------------------------------------------------------------

with open(DIST_FILE, encoding="utf-8-sig") as f:
    distance_rows = list(csv.DictReader(f))

group_rows = [
    r for r in distance_rows
    if r["team_id"] == TEAM_ID
    and r["schedule_date"] == SCHEDULE_DATE
]

n = len(nodes)

matrix = [[None] * n for _ in range(n)]

for r in group_rows:
    i = int(r["from_node_index"])
    j = int(r["to_node_index"])
    matrix[i][j] = int(round(float(r["distance_m"])))

for i in range(n):
    for j in range(n):
        if matrix[i][j] is None:
            raise RuntimeError(
                f"Missing distance matrix value [{i}][{j}]"
            )

# ------------------------------------------------------------
# OR-Tools RoutingModel
# ------------------------------------------------------------

manager = pywrapcp.RoutingIndexManager(
    n,
    1,      # one vehicle
    0       # depot node
)

routing = pywrapcp.RoutingModel(manager)

def distance_callback(from_index, to_index):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    return matrix[from_node][to_node]

transit_callback_index = routing.RegisterTransitCallback(
    distance_callback
)

routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

# Every job must be visited exactly once.
# The depot is node 0 and is automatically the start/end.

search_parameters = pywrapcp.DefaultRoutingSearchParameters()

search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
)

search_parameters.local_search_metaheuristic = (
    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
)

search_parameters.time_limit.seconds = 10

solution = routing.SolveWithParameters(search_parameters)

if solution is None:
    raise RuntimeError("RoutingModel could not find a solution")

# ------------------------------------------------------------
# Extract route
# ------------------------------------------------------------

index = routing.Start(0)

route = []
total_distance = 0

while not routing.IsEnd(index):

    node = manager.IndexToNode(index)
    route.append(node)

    next_index = solution.Value(
        routing.NextVar(index)
    )

    total_distance += routing.GetArcCostForVehicle(
        index,
        next_index,
        0
    )

    index = next_index

route.append(
    manager.IndexToNode(index)
)

# ------------------------------------------------------------
# Print result
# ------------------------------------------------------------

print("=" * 80)
print("CIVICBRAIN STEP 13 — ROUTINGMODEL SMOKE TEST")
print("=" * 80)

print("Team            :", TEAM_ID)
print("Schedule date   :", SCHEDULE_DATE)
print("Nodes           :", n)
print()

print("OPTIMIZED ROUTE")
print("-" * 80)

for seq, node_index in enumerate(route, start=1):

    row = nodes[node_index]

    if row["node_type"] == "DEPOT":
        label = f'DEPOT ({row["node_id"]})'
    else:
        label = f'JOB {row["job_id"]}'

    print(f"{seq}. {label}")

print()
print("Total road distance :", total_distance, "m")
print("Total road distance :", round(total_distance / 1000, 3), "km")

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

job_nodes = [
    x for x in route
    if x != 0
]

expected_jobs = set(
    int(r["node_index"])
    for r in nodes
    if r["node_type"] == "JOB"
)

actual_jobs = set(job_nodes)

print()
print("VALIDATION")
print("-" * 80)

checks = {
    "ROUTING_STATUS": True,
    "START_AT_DEPOT": route[0] == 0,
    "END_AT_DEPOT": route[-1] == 0,
    "ALL_JOBS_VISITED": actual_jobs == expected_jobs,
    "NO_JOB_VISITED_TWICE": len(job_nodes) == len(actual_jobs),
    "ROUTE_NODE_COUNT": len(route) == n + 1,
}

for name, passed in checks.items():
    print(
        f"{name:30s}: "
        f"{'PASS' if passed else 'FAIL'}"
    )

if not all(checks.values()):
    raise RuntimeError("RoutingModel smoke-test validation failed")

print()
print("OR-TOOLS ROUTINGMODEL SMOKE TEST: PASS")
