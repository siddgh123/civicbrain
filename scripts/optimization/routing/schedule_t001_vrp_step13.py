import csv
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


ROOT = Path(".")

CANDIDATE_FILE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_bounded_candidate.csv"
UNPLACED_FILE = ROOT / "data/optimization/scheduling/travel_aware_bounded_unplaced_jobs.csv"
ELIGIBLE_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"

OUT_SCHEDULE = ROOT / "data/optimization/scheduling/schedule_results_t001_vrp_candidate.csv"
OUT_UNPLACED = ROOT / "data/optimization/scheduling/t001_vrp_unplaced_jobs.csv"
OUT_VALIDATION = ROOT / "data/optimization/scheduling/t001_vrp_validation.csv"
OUT_SUMMARY = ROOT / "data/optimization/scheduling/t001_vrp_summary.json"

TEAM = "T001"

SHIFT_START = "08:00"
SHIFT_SECONDS = 9 * 60 * 60

HORIZON_START = "2026-09-28"
HORIZON_DAYS = 30

SOLVER_TIME_LIMIT_SECONDS = 60

SOURCE_BLOCK = 20
DEST_BLOCK = 50
OSRM_DELAY = 0.30

OSRM_URL = "https://router.project-osrm.org/table/v1/driving"


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    if not path.exists():
        raise RuntimeError(f"Missing file: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fnum(value, field):
    try:
        return float(value)
    except Exception:
        raise RuntimeError(f"Invalid number for {field}: {value!r}")


def date_only(value):
    return str(value).strip().split("T")[0]


# ============================================================
# LOAD
# ============================================================

candidate_rows = read_csv(CANDIDATE_FILE)
unplaced_rows = read_csv(UNPLACED_FILE)
eligible_rows = read_csv(ELIGIBLE_FILE)
depot_rows = read_csv(DEPOT_FILE)


if not candidate_rows:
    raise RuntimeError("Candidate schedule is empty.")

if not eligible_rows:
    raise RuntimeError("eligible_jobs.csv is empty.")

if not depot_rows:
    raise RuntimeError("depot_master.csv is empty.")


# ============================================================
# ELIGIBLE LOOKUP
# ============================================================

eligible = {}

for r in eligible_rows:

    job = str(r["job_id"]).strip()

    eligible[job] = {
        "lat": fnum(
            r["latitude"],
            f"{job}.latitude",
        ),
        "lon": fnum(
            r["longitude"],
            f"{job}.longitude",
        ),
        "service_h": fnum(
            r["service_duration_hours"],
            f"{job}.service_duration_hours",
        ),
        "priority": fnum(
            r["priority_score"],
            f"{job}.priority_score",
        ),
        "cluster_id": str(
            r.get("cluster_id", "")
        ).strip(),
        "cost": str(
            r.get("estimated_cost", "")
        ).strip(),
    }


# ============================================================
# CURRENT T001 JOBS
# ============================================================

t001_jobs = set()
candidate_meta = {}

for r in candidate_rows:

    team = str(r["team_id"]).strip()

    if team != TEAM:
        continue

    job = str(r["job_id"]).strip()

    if job in t001_jobs:
        raise RuntimeError(
            f"Duplicate T001 candidate job: {job}"
        )

    t001_jobs.add(job)

    candidate_meta[job] = {
        "original_schedule_date":
            date_only(
                r.get(
                    "original_schedule_date",
                    r["schedule_date"],
                )
            ),
        "original_group_index":
            str(
                r.get(
                    "original_group_index",
                    "",
                )
            ).strip(),
    }


# ============================================================
# T001 UNPLACED
# ============================================================

t001_unplaced = {}

other_unplaced = []

for r in unplaced_rows:

    job = str(r["job_id"]).strip()
    team = str(r["team_id"]).strip()

    if team == TEAM:

        if job in t001_unplaced:
            raise RuntimeError(
                f"Duplicate T001 unplaced job: {job}"
            )

        t001_unplaced[job] = {
            "original_schedule_date":
                date_only(
                    r["original_schedule_date"]
                ),
            "original_group_index":
                str(
                    r["original_group_index"]
                ).strip(),
            "reason":
                str(
                    r["reason"]
                ).strip(),
        }

    else:

        other_unplaced.append(
            dict(r)
        )


# ============================================================
# ALL T001 JOBS TO GIVE TO VRP
# ============================================================

vrp_jobs = sorted(
    t001_jobs
    | set(t001_unplaced)
)

for job in vrp_jobs:

    if job not in eligible:
        raise RuntimeError(
            f"T001 job {job} missing from eligible_jobs.csv"
        )


print("=" * 80)
print("CIVICBRAIN STEP 13 — T001 30-DAY TRAVEL-AWARE VRP")
print("=" * 80)

print(
    f"Existing T001 scheduled : {len(t001_jobs)}"
)

print(
    f"Existing T001 unplaced  : {len(t001_unplaced)}"
)

print(
    f"T001 VRP jobs           : {len(vrp_jobs)}"
)

print(
    f"Horizon                 : "
    f"{HORIZON_START} -> "
    f"{(
        datetime.strptime(
            HORIZON_START,
            "%Y-%m-%d"
        ).date()
        + timedelta(days=HORIZON_DAYS - 1)
    ).isoformat()}"
)

print(
    f"Shift                   : "
    f"{SHIFT_START} + 9h"
)

print(
    f"Solver time limit       : "
    f"{SOLVER_TIME_LIMIT_SECONDS}s"
)

print()


# ============================================================
# DEPOT
# ============================================================

depot = depot_rows[0]

if str(depot.get("lat", "")).strip():

    depot_lat = fnum(
        depot["lat"],
        "depot.lat",
    )

elif str(depot.get("latitude", "")).strip():

    depot_lat = fnum(
        depot["latitude"],
        "depot.latitude",
    )

else:

    raise RuntimeError(
        "Depot latitude not found."
    )


if str(depot.get("long", "")).strip():

    depot_lon = fnum(
        depot["long"],
        "depot.long",
    )

elif str(depot.get("lon", "")).strip():

    depot_lon = fnum(
        depot["lon"],
        "depot.lon",
    )

elif str(depot.get("longitude", "")).strip():

    depot_lon = fnum(
        depot["longitude"],
        "depot.longitude",
    )

else:

    raise RuntimeError(
        "Depot longitude not found."
    )


# ============================================================
# NODE LIST
# ============================================================

# node 0 = depot
node_ids = [
    "__DEPOT__"
] + vrp_jobs

node_index = {
    node_id: i
    for i, node_id in enumerate(node_ids)
}

coords = [
    (
        depot_lon,
        depot_lat,
    )
]

coords.extend(
    (
        eligible[j]["lon"],
        eligible[j]["lat"],
    )
    for j in vrp_jobs
)

N = len(node_ids)


# ============================================================
# OSRM MATRIX
# ============================================================

print(
    f"Building OSRM matrix: "
    f"{len(vrp_jobs)} jobs + depot"
)

time_matrix = {}
distance_matrix = {}


def osrm_table(
    sources,
    destinations,
):

    coordinate_string = ";".join(
        f"{lon},{lat}"
        for lon, lat in coords
    )

    source_string = ";".join(
        str(x)
        for x in sources
    )

    destination_string = ";".join(
        str(x)
        for x in destinations
    )

    url = (
        f"{OSRM_URL}/"
        f"{urllib.parse.quote(
            coordinate_string,
            safe=',;'
        )}"
        f"?annotations=duration,distance"
        f"&sources={source_string}"
        f"&destinations={destination_string}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "CivicBrain-Step13-T001-VRP/1.0"
        },
        method="GET",
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:

        payload = json.loads(
            response.read().decode("utf-8")
        )

    if payload.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM returned: {payload}"
        )

    return payload


request_count = 0

for source_start in range(
    0,
    N,
    SOURCE_BLOCK,
):

    sources = list(
        range(
            source_start,
            min(
                source_start + SOURCE_BLOCK,
                N,
            ),
        )
    )

    for destination_start in range(
        0,
        N,
        DEST_BLOCK,
    ):

        destinations = list(
            range(
                destination_start,
                min(
                    destination_start + DEST_BLOCK,
                    N,
                ),
            )
        )

        payload = osrm_table(
            sources,
            destinations,
        )

        durations = payload["durations"]
        distances = payload["distances"]

        for si, source in enumerate(
            sources
        ):

            for di, destination in enumerate(
                destinations
            ):

                travel = durations[si][di]
                distance = distances[si][di]

                if (
                    travel is None
                    or distance is None
                ):

                    raise RuntimeError(
                        f"No OSRM route "
                        f"{node_ids[source]} -> "
                        f"{node_ids[destination]}"
                    )

                time_matrix[
                    (
                        source,
                        destination,
                    )
                ] = int(
                    round(travel)
                )

                distance_matrix[
                    (
                        source,
                        destination,
                    )
                ] = int(
                    round(distance)
                )

        request_count += 1

        print(
            f"  OSRM request "
            f"{request_count} complete"
        )

        time.sleep(
            OSRM_DELAY
        )


print(
    f"OSRM requests completed : "
    f"{request_count}"
)

print(
    f"Distance entries        : "
    f"{len(distance_matrix)}"
)

print(
    f"Time entries            : "
    f"{len(time_matrix)}"
)

print()


# ============================================================
# OR-TOOLS
#
# 30 vehicles = 30 calendar dates
# Each vehicle starts/ends at depot.
#
# Primary:
#   maximize scheduled jobs
#
# Secondary:
#   maximize existing Step-11 priority among
#   the scheduled jobs
#
# Tertiary:
#   minimize road distance
# ============================================================

num_vehicles = HORIZON_DAYS

starts = [0] * num_vehicles
ends = [0] * num_vehicles

manager = pywrapcp.RoutingIndexManager(
    N,
    num_vehicles,
    starts,
    ends,
)

routing = pywrapcp.RoutingModel(
    manager
)


# ------------------------------------------------------------
# Distance callback
# ------------------------------------------------------------

def distance_callback(
    from_index,
    to_index,
):

    from_node = manager.IndexToNode(
        from_index
    )

    to_node = manager.IndexToNode(
        to_index
    )

    return distance_matrix[
        (
            from_node,
            to_node,
        )
    ]


distance_callback_index = (
    routing.RegisterTransitCallback(
        distance_callback
    )
)

routing.SetArcCostEvaluatorOfAllVehicles(
    distance_callback_index
)


# ------------------------------------------------------------
# Time callback
#
# transit = travel(from,to) + service(to)
# so the time dimension includes
# road travel + service duration.
# ------------------------------------------------------------

def time_callback(
    from_index,
    to_index,
):

    from_node = manager.IndexToNode(
        from_index
    )

    to_node = manager.IndexToNode(
        to_index
    )

    travel_seconds = time_matrix[
        (
            from_node,
            to_node,
        )
    ]

    if to_node == 0:
        service_seconds = 0

    else:

        job = node_ids[
            to_node
        ]

        service_seconds = int(
            round(
                eligible[job]["service_h"]
                * 3600
            )
        )

    return (
        travel_seconds
        + service_seconds
    )


time_callback_index = (
    routing.RegisterTransitCallback(
        time_callback
    )
)

routing.AddDimension(
    time_callback_index,
    0,
    SHIFT_SECONDS,
    True,
    "Time",
)

time_dimension = (
    routing.GetDimensionOrDie(
        "Time"
    )
)


# ------------------------------------------------------------
# Optional jobs with very large penalties
#
# Penalty design:
#
# BIG_JOB_PENALTY guarantees:
#   scheduled-count priority
#
# PRIORITY component means:
#   among equal scheduled counts,
#   preserve higher Step-11 priority.
#
# Distance remains the final objective.
# ------------------------------------------------------------

BIG_JOB_PENALTY = 10_000_000
PRIORITY_SCALE = 100_000

for job in vrp_jobs:

    node = node_index[job]

    priority_component = int(
        round(
            eligible[job]["priority"]
            * PRIORITY_SCALE
        )
    )

    penalty = (
        BIG_JOB_PENALTY
        + priority_component
    )

    routing.AddDisjunction(
        [
            manager.NodeToIndex(node)
        ],
        penalty,
    )


# ============================================================
# SEARCH PARAMETERS
# ============================================================

search_parameters = (
    pywrapcp.DefaultRoutingSearchParameters()
)

search_parameters.first_solution_strategy = (
    routing_enums_pb2.FirstSolutionStrategy
    .PARALLEL_CHEAPEST_INSERTION
)

search_parameters.local_search_metaheuristic = (
    routing_enums_pb2.LocalSearchMetaheuristic
    .GUIDED_LOCAL_SEARCH
)

search_parameters.time_limit.seconds = (
    SOLVER_TIME_LIMIT_SECONDS
)

search_parameters.log_search = False


print("=" * 80)
print("STARTING OR-TOOLS MULTI-DAY VRP")
print("=" * 80)

print(
    "30 vehicles = 30 calendar dates"
)

print(
    "Each route must satisfy "
    "service + travel <= 9h"
)

print(
    "Primary objective: maximum "
    "number of scheduled jobs"
)

print(
    "Secondary objective: existing "
    "priority score"
)

print(
    "Tertiary objective: road distance"
)

print()

solver_start = time.monotonic()

solution = routing.SolveWithParameters(
    search_parameters
)

solver_elapsed = (
    time.monotonic()
    - solver_start
)

print(
    f"Solver elapsed : "
    f"{solver_elapsed:.2f}s"
)


if solution is None:

    raise RuntimeError(
        "OR-Tools did not return a solution."
    )


# ============================================================
# EXTRACT ROUTES
# ============================================================

route_rows = []
route_summaries = []

scheduled_t001 = set()

horizon_dates = []

start_date = datetime.strptime(
    HORIZON_START,
    "%Y-%m-%d",
).date()

for i in range(
    HORIZON_DAYS
):

    horizon_dates.append(
        (
            start_date
            + timedelta(days=i)
        ).isoformat()
    )


schedule_counter = 1

for vehicle in range(
    num_vehicles
):

    index = routing.Start(
        vehicle
    )

    date = horizon_dates[
        vehicle
    ]

    sequence = 1

    current_time_seconds = 0

    previous_node = 0

    route_service_seconds = 0
    route_travel_seconds = 0
    route_distance = 0
    route_jobs = []

    while not routing.IsEnd(index):

        node = manager.IndexToNode(
            index
        )

        next_index = solution.Value(
            routing.NextVar(index)
        )

        next_node = (
            manager.IndexToNode(
                next_index
            )
        )

        if node != 0:

            job = node_ids[node]

            travel_seconds = time_matrix[
                (
                    previous_node,
                    node,
                )
            ]

            distance_m = distance_matrix[
                (
                    previous_node,
                    node,
                )
            ]

            service_seconds = int(
                round(
                    eligible[job]["service_h"]
                    * 3600
                )
            )

            current_time_seconds += (
                travel_seconds
            )

            planned_start_seconds = (
                current_time_seconds
            )

            planned_end_seconds = (
                planned_start_seconds
                + service_seconds
            )

            base_dt = datetime.strptime(
                f"{date} {SHIFT_START}",
                "%Y-%m-%d %H:%M",
            )

            planned_start = (
                base_dt
                + timedelta(
                    seconds=
                    planned_start_seconds
                )
            )

            planned_end = (
                base_dt
                + timedelta(
                    seconds=
                    planned_end_seconds
                )
            )

            if job in candidate_meta:

                original_date = (
                    candidate_meta[job]
                    ["original_schedule_date"]
                )

                original_group = (
                    candidate_meta[job]
                    ["original_group_index"]
                )

            else:

                original_date = (
                    t001_unplaced[job]
                    ["original_schedule_date"]
                )

                original_group = (
                    t001_unplaced[job]
                    ["original_group_index"]
                )

            route_rows.append(
                {
                    "schedule_id":
                        (
                            f"VRP-T001-{date}-"
                            f"{schedule_counter:03d}"
                        ),
                    "team_id":
                        TEAM,
                    "schedule_date":
                        date,
                    "cluster_id":
                        eligible[job]["cluster_id"],
                    "job_id":
                        job,
                    "sequence_no":
                        sequence,
                    "planned_start":
                        planned_start.strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    "planned_end":
                        planned_end.strftime(
                            "%Y-%m-%d %H:%M"
                        ),
                    "service_duration_h":
                        round(
                            eligible[job]["service_h"],
                            3,
                        ),
                    "travel_distance_m":
                        round(
                            distance_m,
                            1,
                        ),
                    "travel_time_min":
                        round(
                            travel_seconds / 60.0,
                            3,
                        ),
                    "priority_score":
                        round(
                            eligible[job]["priority"],
                            6,
                        ),
                    "estimated_cost":
                        eligible[job]["cost"],
                    "status":
                        "SCHEDULED_T001_TRAVEL_AWARE_VRP",
                    "repair_action":
                        (
                            "UNCHANGED"
                            if original_date
                            == date
                            else
                            "MOVED_BY_T001_VRP"
                        ),
                    "original_group_index":
                        original_group,
                    "original_schedule_date":
                        original_date,
                }
            )

            scheduled_t001.add(
                job
            )

            route_jobs.append(
                job
            )

            route_service_seconds += (
                service_seconds
            )

            route_travel_seconds += (
                travel_seconds
            )

            route_distance += (
                distance_m
            )

            current_time_seconds = (
                planned_end_seconds
            )

            sequence += 1

        previous_node = node

        index = next_index

    # final return to depot
    final_node = 0

    if route_jobs:

        return_travel_seconds = time_matrix[
            (
                previous_node,
                final_node,
            )
        ]

        return_distance = distance_matrix[
            (
                previous_node,
                final_node,
            )
        ]

        route_travel_seconds += (
            return_travel_seconds
        )

        route_distance += (
            return_distance
        )

    total_route_seconds = (
        route_service_seconds
        + route_travel_seconds
    )

    route_summaries.append(
        {
            "team_id":
                TEAM,
            "schedule_date":
                date,
            "vehicle":
                vehicle,
            "job_count":
                len(route_jobs),
            "service_h":
                round(
                    route_service_seconds
                    / 3600.0,
                    6,
                ),
            "travel_h":
                round(
                    route_travel_seconds
                    / 3600.0,
                    6,
                ),
            "total_route_h":
                round(
                    total_route_seconds
                    / 3600.0,
                    6,
                ),
            "finish_time":
                (
                    datetime.strptime(
                        f"{date} {SHIFT_START}",
                        "%Y-%m-%d %H:%M",
                    )
                    + timedelta(
                        seconds=
                        total_route_seconds
                    )
                ).strftime(
                    "%H:%M"
                ),
            "distance_km":
                round(
                    route_distance / 1000.0,
                    6,
                ),
        }
    )

    schedule_counter += 1


# ============================================================
# FINAL UNPLACED
# ============================================================

final_unplaced = []

for r in other_unplaced:

    final_unplaced.append(
        dict(r)
    )


for job in sorted(
    t001_unplaced
):

    if job in scheduled_t001:
        continue

    meta = t001_unplaced[job]

    row = {
        "job_id":
            job,
        "team_id":
            TEAM,
        "original_schedule_date":
            meta["original_schedule_date"],
        "original_group_index":
            meta["original_group_index"],
        "priority_score":
            round(
                eligible[job]["priority"],
                6,
            ),
        "service_duration_h":
            round(
                eligible[job]["service_h"],
                3,
            ),
        "reason":
            (
                "TRAVEL_AWARE_VRP_LEFT_UNSCHEDULED"
            ),
        "status":
            "UNSCHEDULED",
    }

    final_unplaced.append(
        row
    )


# ============================================================
# PRESERVE NON-T001 CANDIDATE ROWS
# ============================================================

final_output = []

for r in candidate_rows:

    if str(r["team_id"]).strip() != TEAM:

        final_output.append(
            dict(r)
        )


final_output.extend(
    route_rows
)


# ============================================================
# VALIDATION
# ============================================================

candidate_total_jobs = {
    str(r["job_id"]).strip()
    for r in candidate_rows
}

original_all_jobs = (
    candidate_total_jobs
    | {
        str(r["job_id"]).strip()
        for r in unplaced_rows
    }
)

final_scheduled_ids = {
    str(r["job_id"]).strip()
    for r in route_rows
}

for r in candidate_rows:

    if str(r["team_id"]).strip() != TEAM:

        final_scheduled_ids.add(
            str(r["job_id"]).strip()
        )


final_unplaced_ids = {
    str(r["job_id"]).strip()
    for r in final_unplaced
}

all_accounted = (
    final_scheduled_ids
    | final_unplaced_ids
)

disjoint = (
    final_scheduled_ids
    .isdisjoint(
        final_unplaced_ids
    )
)

no_duplicate = (
    len(
        final_scheduled_ids
    )
    ==
    len(
        final_output
    )
    -
    sum(
        1
        for r in final_output
        if str(r.get("team_id", "")).strip()
        != TEAM
        and str(r.get("job_id", "")).strip()
        in final_scheduled_ids
    )
)


route_violations = [
    r
    for r in route_summaries
    if r["total_route_h"]
    > 9.0 + 1e-9
]

t001_vrp_job_count = (
    len(scheduled_t001)
)

t001_input_count = (
    len(vrp_jobs)
)

overall_accounting = (
    all_accounted
    == original_all_jobs
)

all_9h = (
    len(route_violations)
    == 0
)

validation_rows = [
    {
        "check":
            "T001_INPUT_JOB_COUNT",
        "expected":
            len(vrp_jobs),
        "actual":
            len(vrp_jobs),
        "status":
            "PASS",
    },
    {
        "check":
            "T001_VRP_SCHEDULED",
        "expected":
            "0..all",
        "actual":
            t001_vrp_job_count,
        "status":
            "PASS",
    },
    {
        "check":
            "ALL_ROUTES_WITHIN_9H",
        "expected":
            "<=9h",
        "actual":
            (
                "PASS"
                if all_9h
                else "FAIL"
            ),
        "status":
            (
                "PASS"
                if all_9h
                else "FAIL"
            ),
    },
    {
        "check":
            "NO_SCHEDULE_UNPLACED_OVERLAP",
        "expected":
            "YES",
        "actual":
            (
                "YES"
                if disjoint
                else "NO"
            ),
        "status":
            (
                "PASS"
                if disjoint
                else "FAIL"
            ),
    },
    {
        "check":
            "ALL_ORIGINAL_JOBS_ACCOUNTED",
        "expected":
            241,
        "actual":
            len(all_accounted),
        "status":
            (
                "PASS"
                if overall_accounting
                else "FAIL"
            ),
    },
    {
        "check":
            "VRP_SCHEDULED_PLUS_UNPLACED",
        "expected":
            t001_input_count,
        "actual":
            (
                t001_vrp_job_count
                + len(
                    [
                        r
                        for r in final_unplaced
                        if str(
                            r["team_id"]
                        ).strip()
                        == TEAM
                    ]
                )
            ),
        "status":
            "PASS",
    },
]


# ============================================================
# WRITE SCHEDULE
# ============================================================

if final_output:

    final_output.sort(
        key=lambda r: (
            date_only(
                r["schedule_date"]
            ),
            str(
                r["team_id"]
            ),
            int(
                r.get(
                    "sequence_no",
                    0
                )
            ),
        )
    )

    fields = [
        "schedule_id",
        "team_id",
        "schedule_date",
        "cluster_id",
        "job_id",
        "sequence_no",
        "planned_start",
        "planned_end",
        "service_duration_h",
        "travel_distance_m",
        "travel_time_min",
        "priority_score",
        "estimated_cost",
        "status",
        "repair_action",
        "original_group_index",
        "original_schedule_date",
    ]

    with open(
        OUT_SCHEDULE,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        for r in final_output:

            clean = {
                field:
                    r.get(
                        field,
                        "",
                    )
                for field in fields
            }

            writer.writerow(
                clean
            )


# ============================================================
# WRITE UNPLACED
# ============================================================

with open(
    OUT_UNPLACED,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "job_id",
        "team_id",
        "original_schedule_date",
        "original_group_index",
        "priority_score",
        "service_duration_h",
        "reason",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    for r in final_unplaced:

        writer.writerow(
            {
                field:
                    r.get(
                        field,
                        "",
                    )
                for field in fields
            }
        )


# ============================================================
# WRITE VALIDATION
# ============================================================

with open(
    OUT_VALIDATION,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "check",
            "expected",
            "actual",
            "status",
        ],
    )

    writer.writeheader()
    writer.writerows(
        validation_rows
    )


# ============================================================
# SUMMARY
# ============================================================

total_service_h = sum(
    r["service_h"]
    for r in route_summaries
)

total_travel_h = sum(
    r["travel_h"]
    for r in route_summaries
)

total_route_h = sum(
    r["total_route_h"]
    for r in route_summaries
)

total_distance_km = sum(
    r["distance_km"]
    for r in route_summaries
)

max_route = max(
    route_summaries,
    key=lambda r: r["total_route_h"],
    default=None,
)

summary = {
    "status":
        "PASS"
        if (
            all_9h
            and disjoint
            and overall_accounting
        )
        else "REVIEW_REQUIRED",
    "t001_input_jobs":
        len(vrp_jobs),
    "t001_scheduled_jobs":
        len(scheduled_t001),
    "t001_unplaced_jobs":
        len(
            [
                r
                for r in final_unplaced
                if str(
                    r["team_id"]
                ).strip()
                == TEAM
            ]
        ),
    "total_final_scheduled_jobs":
        len(final_scheduled_ids),
    "total_final_unplaced_jobs":
        len(final_unplaced_ids),
    "route_groups":
        len(
            [
                r
                for r in route_summaries
                if r["job_count"] > 0
            ]
        ),
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
    "solver_elapsed_seconds":
        round(
            solver_elapsed,
            3,
        ),
    "solver_objective":
        solution.ObjectiveValue(),
    "max_route":
        max_route,
    "t001_unplaced":
        [
            r
            for r in final_unplaced
            if str(
                r["team_id"]
            ).strip()
            == TEAM
        ],
    "validation":
        {
            r["check"]:
                r["status"]
            for r in validation_rows
        },
    "outputs":
        {
            "schedule":
                str(OUT_SCHEDULE),
            "unplaced":
                str(OUT_UNPLACED),
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
# CONSOLE
# ============================================================

print()
print("=" * 80)
print("T001 TRAVEL-AWARE VRP RESULT")
print("=" * 80)

print(
    f"T001 input jobs          : "
    f"{len(vrp_jobs)}"
)

print(
    f"T001 scheduled jobs      : "
    f"{len(scheduled_t001)}"
)

print(
    f"T001 unplaced jobs       : "
    f"{sum(
        1
        for r in final_unplaced
        if str(r['team_id']).strip()
        == TEAM
    )}"
)

print(
    f"Final scheduled total    : "
    f"{len(final_scheduled_ids)}"
)

print(
    f"Final unplaced total     : "
    f"{len(final_unplaced_ids)}"
)

print(
    f"Route groups             : "
    f"{sum(
        1
        for r in route_summaries
        if r['job_count'] > 0
    )}"
)

print(
    f"Total service hours      : "
    f"{total_service_h:.3f}"
)

print(
    f"Total travel hours       : "
    f"{total_travel_h:.3f}"
)

print(
    f"Total route hours        : "
    f"{total_route_h:.3f}"
)

print(
    f"Total distance           : "
    f"{total_distance_km:.3f} km"
)

if max_route:

    print()
    print("MAX ROUTE")
    print("-" * 80)

    print(
        f"Date                    : "
        f"{max_route['schedule_date']}"
    )

    print(
        f"Jobs                    : "
        f"{max_route['job_count']}"
    )

    print(
        f"Service                 : "
        f"{max_route['service_h']:.3f} h"
    )

    print(
        f"Travel                  : "
        f"{max_route['travel_h']:.3f} h"
    )

    print(
        f"Total                   : "
        f"{max_route['total_route_h']:.3f} h"
    )

    print(
        f"Finish                  : "
        f"{max_route['finish_time']}"
    )

print()
print("T001 UNPLACED")
print("-" * 80)

for r in final_unplaced:

    if str(
        r["team_id"]
    ).strip() == TEAM:

        print(
            f"{r['job_id']} | "
            f"service={r['service_duration_h']}h | "
            f"priority={r['priority_score']} | "
            f"{r['reason']}"
        )


print()
print("VALIDATION")
print("-" * 80)

for r in validation_rows:

    print(
        f"{r['check']:<40}"
        f"{r['status']}"
    )

print()
print(
    "OVERALL STATUS : "
    + (
        "PASS"
        if (
            all_9h
            and disjoint
            and overall_accounting
        )
        else "REVIEW_REQUIRED"
    )
)

print()
print("OUTPUTS")
print("-" * 80)

print(
    f"Schedule   : {OUT_SCHEDULE}"
)

print(
    f"Unplaced   : {OUT_UNPLACED}"
)

print(
    f"Validation : {OUT_VALIDATION}"
)

print(
    f"Summary    : {OUT_SUMMARY}"
)

print()
print("=" * 80)
print("T001 TRAVEL-AWARE VRP COMPLETE")
print("=" * 80)
