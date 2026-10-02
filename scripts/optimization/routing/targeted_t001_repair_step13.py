import csv
import itertools
import json
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(".")

CANDIDATE_FILE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_bounded_candidate.csv"
UNPLACED_FILE = ROOT / "data/optimization/scheduling/travel_aware_bounded_unplaced_jobs.csv"
ELIGIBLE_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"

OUT_SCHEDULE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_targeted_candidate.csv"
OUT_UNPLACED = ROOT / "data/optimization/scheduling/travel_aware_targeted_unplaced_jobs.csv"
OUT_VALIDATION = ROOT / "data/optimization/scheduling/travel_aware_targeted_validation.csv"
OUT_SUMMARY = ROOT / "data/optimization/scheduling/travel_aware_targeted_summary.json"

TEAM = "T001"
SHIFT_HOURS = 9.0
DEPOT_ID = "D001"

OSRM_URL = "https://router.project-osrm.org/table/v1/driving"

BEAM_WIDTH = 60
ACTIONS_PER_STATE = 15
SEARCH_TIMEOUT_SECONDS = 60.0
MAX_DAILY_JOBS = 5


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    if not path.exists():
        raise RuntimeError(f"Missing file: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(v, name):
    try:
        return float(v)
    except Exception:
        raise RuntimeError(f"Invalid number {name}: {v!r}")


def date_only(v):
    return str(v).strip().split("T")[0]


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
    raise RuntimeError("Eligible jobs is empty.")

if not depot_rows:
    raise RuntimeError("Depot file is empty.")


# ============================================================
# ELIGIBLE LOOKUP
# ============================================================

eligible = {}

for r in eligible_rows:
    job = str(r["job_id"]).strip()

    eligible[job] = {
        "lat": num(r["latitude"], f"{job}.latitude"),
        "lon": num(r["longitude"], f"{job}.longitude"),
        "service_h": num(
            r["service_duration_hours"],
            f"{job}.service_duration_hours"
        ),
        "priority": num(
            r["priority_score"],
            f"{job}.priority_score"
        ),
        "cluster_id": str(
            r.get("cluster_id", "")
        ).strip(),
        "cost": str(
            r.get("estimated_cost", "")
        ).strip(),
    }


# ============================================================
# CURRENT DAILY ASSIGNMENT
# ============================================================

daily = defaultdict(list)
origin_date = {}

candidate_job_ids = set()

for r in candidate_rows:

    team = str(r["team_id"]).strip()
    date = date_only(r["schedule_date"])
    job = str(r["job_id"]).strip()

    if job in candidate_job_ids:
        raise RuntimeError(
            f"Duplicate candidate job: {job}"
        )

    candidate_job_ids.add(job)

    daily[(team, date)].append(job)

    origin_date[job] = date


# ============================================================
# UNPLACED
# ============================================================

unplaced = {}

for r in unplaced_rows:

    job = str(r["job_id"]).strip()

    unplaced[job] = {
        "team_id":
            str(r["team_id"]).strip(),
        "original_schedule_date":
            date_only(
                r["original_schedule_date"]
            ),
        "original_group_index":
            str(
                r["original_group_index"]
            ).strip(),
        "reason":
            str(r["reason"]).strip(),
    }


# ============================================================
# ONLY THE 5 T001 REPAIR JOBS
# ============================================================

repair_jobs = []

for job, meta in unplaced.items():

    if meta["team_id"] != TEAM:
        continue

    if job not in eligible:
        raise RuntimeError(
            f"Unplaced job {job} missing from eligible_jobs."
        )

    # job 11 is already classified as hard infeasible
    if eligible[job]["service_h"] >= 8.7:
        continue

    repair_jobs.append(job)


repair_jobs.sort(
    key=lambda j: (
        -eligible[j]["priority"],
        -eligible[j]["service_h"],
        j,
    )
)


if not repair_jobs:
    raise RuntimeError(
        "No targeted T001 repair jobs found."
    )


# ============================================================
# DATES
# ============================================================

dates = sorted(
    {
        date
        for (team, date) in daily
        if team == TEAM
    }
)

if not dates:
    raise RuntimeError(
        "No T001 schedule dates found."
    )


# ============================================================
# DEPOT
# ============================================================

depot = depot_rows[0]

if depot.get("lat", "").strip():
    depot_lat = num(
        depot["lat"],
        "depot.latitude"
    )
elif depot.get("latitude", "").strip():
    depot_lat = num(
        depot["latitude"],
        "depot.latitude"
    )
else:
    raise RuntimeError(
        "Depot latitude missing."
    )

if depot.get("long", "").strip():
    depot_lon = num(
        depot["long"],
        "depot.longitude"
    )
elif depot.get("lon", "").strip():
    depot_lon = num(
        depot["lon"],
        "depot.longitude"
    )
elif depot.get("longitude", "").strip():
    depot_lon = num(
        depot["longitude"],
        "depot.longitude"
    )
else:
    raise RuntimeError(
        "Depot longitude missing."
    )


# ============================================================
# T001 OSRM MATRIX
# ============================================================

team_candidate_jobs = set()

for (team, date), jobs in daily.items():

    if team == TEAM:
        team_candidate_jobs.update(jobs)


all_matrix_jobs = sorted(
    team_candidate_jobs
    | set(repair_jobs)
)

node_ids = [
    "__DEPOT__"
] + all_matrix_jobs

node_index = {
    node_id: i
    for i, node_id in enumerate(node_ids)
}

coords = [
    (
        depot_lon,
        depot_lat
    )
]

coords.extend(
    (
        eligible[j]["lon"],
        eligible[j]["lat"]
    )
    for j in all_matrix_jobs
)

time_matrix = {}
distance_matrix = {}


def osrm_table(
    sources,
    destinations
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
        f"{urllib.parse.quote(coordinate_string, safe=',;')}"
        f"?annotations=duration,distance"
        f"&sources={source_string}"
        f"&destinations={destination_string}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "CivicBrain-Step13-TargetedRepair/2.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        payload = json.loads(
            response.read().decode("utf-8")
        )

    if payload.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM returned: {payload}"
        )

    return payload


print("=" * 80)
print("STEP 13 — TARGETED T001 GLOBAL REPAIR")
print("=" * 80)

print(
    f"T001 candidate jobs : "
    f"{len(team_candidate_jobs)}"
)

print(
    f"Repair jobs         : "
    f"{len(repair_jobs)} -> {repair_jobs}"
)

print(
    f"Beam width          : "
    f"{BEAM_WIDTH}"
)

print(
    f"Search timeout      : "
    f"{SEARCH_TIMEOUT_SECONDS}s"
)

print()


N = len(node_ids)

request_count = 0

for source_start in range(
    0,
    N,
    20
):

    sources = list(
        range(
            source_start,
            min(
                source_start + 20,
                N
            )
        )
    )

    for destination_start in range(
        0,
        N,
        50
    ):

        destinations = list(
            range(
                destination_start,
                min(
                    destination_start + 50,
                    N
                )
            )
        )

        payload = osrm_table(
            sources,
            destinations
        )

        for si, source in enumerate(
            sources
        ):

            for di, destination in enumerate(
                destinations
            ):

                travel = payload[
                    "durations"
                ][si][di]

                distance = payload[
                    "distances"
                ][si][di]

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
                        destination
                    )
                ] = float(travel)

                distance_matrix[
                    (
                        source,
                        destination
                    )
                ] = float(distance)

        request_count += 1

        time.sleep(0.30)

print(
    f"OSRM requests : {request_count}"
)

print(
    f"Matrix entries: {len(time_matrix)}"
)

print()


# ============================================================
# EXACT BEST FEASIBLE ROUTE
# ============================================================

route_cache = {}


def best_route(jobs):

    jobs = tuple(
        sorted(set(jobs))
    )

    if jobs in route_cache:
        return route_cache[jobs]

    if not jobs:
        result = {
            "jobs": [],
            "service_h": 0.0,
            "travel_h": 0.0,
            "total_h": 0.0,
            "distance_m": 0.0,
        }

        route_cache[jobs] = result
        return result

    if len(jobs) > MAX_DAILY_JOBS:
        return None

    depot_idx = node_index[
        "__DEPOT__"
    ]

    best = None

    for permutation in itertools.permutations(
        jobs
    ):

        nodes = [
            depot_idx
        ]

        nodes.extend(
            node_index[j]
            for j in permutation
        )

        nodes.append(
            depot_idx
        )

        travel_seconds = 0.0
        distance_m = 0.0

        for a, b in zip(
            nodes,
            nodes[1:]
        ):

            travel_seconds += time_matrix[
                (a, b)
            ]

            distance_m += distance_matrix[
                (a, b)
            ]

        service_h = sum(
            eligible[j]["service_h"]
            for j in permutation
        )

        total_h = (
            service_h
            + travel_seconds / 3600.0
        )

        if total_h > SHIFT_HOURS + 1e-9:
            continue

        candidate = {
            "jobs": list(permutation),
            "service_h": service_h,
            "travel_h":
                travel_seconds / 3600.0,
            "total_h": total_h,
            "distance_m": distance_m,
        }

        if best is None:
            best = candidate

        elif (
            candidate["distance_m"],
            candidate["total_h"]
        ) < (
            best["distance_m"],
            best["total_h"]
        ):

            best = candidate

    route_cache[jobs] = best

    return best


# ============================================================
# VERIFY SINGLE JOBS
# ============================================================

print("SINGLE-JOB FEASIBILITY")
print("-" * 80)

for job in repair_jobs:

    route = best_route(
        [job]
    )

    print(
        f"{job} | "
        f"service={eligible[job]['service_h']:.2f}h | "
        f"{'FEASIBLE' if route else 'INFEASIBLE'}"
    )

print()


# ============================================================
# STATE SIGNATURE
# ============================================================

def signature(state):

    return tuple(
        (
            date,
            tuple(
                sorted(
                    state.get(
                        (TEAM, date),
                        []
                    )
                )
            )
        )
        for date in dates
    )


# ============================================================
# STATE METRICS
# ============================================================

def state_metrics(state):

    total_distance = 0.0
    total_route_h = 0.0
    relocations = 0

    for date in dates:

        jobs = state.get(
            (TEAM, date),
            []
        )

        if jobs:

            route = best_route(
                jobs
            )

            if route is None:
                return (
                    999999,
                    999999999,
                    999999
                )

            total_distance += (
                route["distance_m"]
            )

            total_route_h += (
                route["total_h"]
            )

        for job in jobs:

            original = origin_date.get(
                job,
                date
            )

            if original != date:
                relocations += 1

    return (
        relocations,
        total_distance,
        total_route_h
    )


# ============================================================
# GENERATE DIRECT + ONE-SWAP ACTIONS
# ============================================================

def actions_for_job(
    state,
    job,
    locked_jobs,
    deadline
):

    actions = []

    # --------------------------------------------------------
    # DIRECT INSERTION
    # --------------------------------------------------------

    for target_date in dates:

        if time.monotonic() >= deadline:
            break

        key = (
            TEAM,
            target_date
        )

        current = list(
            state.get(
                key,
                []
            )
        )

        if job in current:
            continue

        if len(current) >= MAX_DAILY_JOBS:
            continue

        trial = (
            current
            + [job]
        )

        route = best_route(
            trial
        )

        if route is None:
            continue

        new_state = deepcopy(
            state
        )

        new_state[key] = trial

        score = state_metrics(
            new_state
        )

        actions.append(
            (
                score,
                f"DIRECT->{target_date}",
                new_state
            )
        )


    # --------------------------------------------------------
    # ONE-DONOR SWAP
    # --------------------------------------------------------

    for target_date in dates:

        if time.monotonic() >= deadline:
            break

        target_key = (
            TEAM,
            target_date
        )

        current_target = list(
            state.get(
                target_key,
                []
            )
        )

        donors = [
            x
            for x in current_target
            if x not in locked_jobs
            and x not in repair_jobs
        ]

        for donor in donors:

            if time.monotonic() >= deadline:
                break

            target_trial = [
                x
                for x in current_target
                if x != donor
            ]

            target_trial.append(
                job
            )

            target_route = best_route(
                target_trial
            )

            if target_route is None:
                continue

            for destination_date in dates:

                if time.monotonic() >= deadline:
                    break

                if (
                    destination_date
                    == target_date
                ):
                    continue

                destination_key = (
                    TEAM,
                    destination_date
                )

                destination_current = list(
                    state.get(
                        destination_key,
                        []
                    )
                )

                if (
                    donor
                    in destination_current
                ):
                    continue

                if (
                    len(destination_current)
                    >= MAX_DAILY_JOBS
                ):
                    continue

                destination_trial = (
                    destination_current
                    + [donor]
                )

                destination_route = (
                    best_route(
                        destination_trial
                    )
                )

                if destination_route is None:
                    continue

                new_state = deepcopy(
                    state
                )

                new_state[
                    target_key
                ] = target_trial

                new_state[
                    destination_key
                ] = destination_trial

                score = state_metrics(
                    new_state
                )

                actions.append(
                    (
                        score,
                        (
                            f"SWAP {donor}:"
                            f"{target_date}"
                            f"->{destination_date}"
                        ),
                        new_state
                    )
                )

    # --------------------------------------------------------
    # Remove duplicate states
    # --------------------------------------------------------

    unique = {}

    for score, label, state2 in actions:

        sig = signature(
            state2
        )

        old = unique.get(
            sig
        )

        if (
            old is None
            or score < old[0]
        ):
            unique[sig] = (
                score,
                label,
                state2
            )

    actions = list(
        unique.values()
    )

    actions.sort(
        key=lambda x: x[0]
    )

    return actions[
        :ACTIONS_PER_STATE
    ]


# ============================================================
# GLOBAL BEAM SEARCH
# ============================================================

deadline = (
    time.monotonic()
    + SEARCH_TIMEOUT_SECONDS
)

beam = [
    (
        state_metrics(daily),
        daily,
        set(),
    )
]

print(
    "=" * 80
)

print(
    "GLOBAL BEAM SEARCH"
)

print(
    "=" * 80
)

for step, job in enumerate(
    repair_jobs,
    start=1
):

    if time.monotonic() >= deadline:

        print(
            "GLOBAL SEARCH TIMEOUT"
        )

        break

    next_states = {}

    processed = 0

    print(
        f"\n[{step}/{len(repair_jobs)}] "
        f"JOB={job} "
        f"priority={eligible[job]['priority']:.2f} "
        f"service={eligible[job]['service_h']:.2f}h"
    )

    for _, state, locked in beam:

        if time.monotonic() >= deadline:
            break

        actions = actions_for_job(
            state,
            job,
            locked,
            deadline
        )

        processed += len(actions)

        for score, label, new_state in actions:

            sig = signature(
                new_state
            )

            new_locked = (
                set(locked)
                | {job}
            )

            item = (
                score,
                new_state,
                new_locked,
                label
            )

            old = next_states.get(
                sig
            )

            if (
                old is None
                or score < old[0]
            ):
                next_states[sig] = item

    if not next_states:

        print(
            "No feasible state generated."
        )

        break

    candidates = list(
        next_states.values()
    )

    candidates.sort(
        key=lambda x: x[0]
    )

    candidates = candidates[
        :BEAM_WIDTH
    ]

    beam = [
        (
            x[0],
            x[1],
            x[2]
        )
        for x in candidates
    ]

    print(
        f"Actions generated : "
        f"{processed}"
    )

    print(
        f"Beam states        : "
        f"{len(beam)}"
    )

    print(
        f"Best relocations   : "
        f"{beam[0][0][0]}"
    )

    print(
        f"Best distance      : "
        f"{beam[0][0][1]:.1f} m"
    )

    print(
        f"Best route hours   : "
        f"{beam[0][0][2]:.3f} h"
    )

    print(
        f"Elapsed            : "
        f"{time.monotonic() - (deadline - SEARCH_TIMEOUT_SECONDS):.2f}s"
    )


# ============================================================
# SELECT BEST STATE
# ============================================================

if not beam:
    raise RuntimeError(
        "No feasible beam state."
    )

best_state = beam[0][1]


# ============================================================
# IDENTIFY PLACED REPAIR JOBS
# ============================================================

placed_repair = set()

for job in repair_jobs:

    for date in dates:

        if job in best_state.get(
            (TEAM, date),
            []
        ):

            placed_repair.add(
                job
            )

            break


remaining_repair = [
    j
    for j in repair_jobs
    if j not in placed_repair
]


# ============================================================
# BUILD FINAL CANDIDATE SCHEDULE
# ============================================================

output_rows = []

# Keep all non-T001 candidate rows unchanged.
for r in candidate_rows:

    if str(r["team_id"]).strip() != TEAM:
        output_rows.append(
            r
        )


schedule_counter = 1


for date in dates:

    jobs = best_state.get(
        (TEAM, date),
        []
    )

    if not jobs:
        continue

    route = best_route(
        jobs
    )

    if route is None:
        raise RuntimeError(
            f"Final route infeasible "
            f"for T001 {date}"
        )

    current_dt = datetime.strptime(
        f"{date} 08:00",
        "%Y-%m-%d %H:%M"
    )

    previous = "__DEPOT__"

    for sequence, job in enumerate(
        route["jobs"],
        start=1
    ):

        from_idx = node_index[
            previous
        ]

        to_idx = node_index[
            job
        ]

        travel_seconds = time_matrix[
            (
                from_idx,
                to_idx
            )
        ]

        distance_m = distance_matrix[
            (
                from_idx,
                to_idx
            )
        ]

        current_dt += timedelta(
            seconds=travel_seconds
        )

        planned_start = current_dt

        planned_end = (
            planned_start
            + timedelta(
                hours=eligible[job]["service_h"]
            )
        )

        original = origin_date.get(
            job,
            unplaced.get(
                job,
                {}
            ).get(
                "original_schedule_date",
                date
            )
        )

        output_rows.append(
            {
                "schedule_id":
                    (
                        f"TRV-T-{date}-"
                        f"{TEAM}-{schedule_counter:03d}"
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
                        3
                    ),
                "travel_distance_m":
                    round(
                        distance_m,
                        1
                    ),
                "travel_time_min":
                    round(
                        travel_seconds / 60.0,
                        3
                    ),
                "priority_score":
                    round(
                        eligible[job]["priority"],
                        6
                    ),
                "estimated_cost":
                    eligible[job]["cost"],
                "status":
                    "SCHEDULED_TRAVEL_AWARE_TARGETED_CANDIDATE",
                "repair_action":
                    (
                        "UNCHANGED"
                        if original == date
                        else "MOVED_BY_TARGETED_REPAIR"
                    ),
                "original_group_index":
                    unplaced.get(
                        job,
                        {}
                    ).get(
                        "original_group_index",
                        ""
                    ),
                "original_schedule_date":
                    original,
            }
        )

        current_dt = planned_end
        previous = job

    schedule_counter += 1


# ============================================================
# FINAL UNPLACED
# ============================================================

final_scheduled_ids = {
    r["job_id"]
    for r in output_rows
}

final_unplaced = []

for r in unplaced_rows:

    job = str(
        r["job_id"]
    ).strip()

    if job in final_scheduled_ids:
        continue

    row = dict(r)

    if (
        job in remaining_repair
        and job in repair_jobs
    ):

        row["reason"] = (
            "NO_TARGETED_FEASIBLE_REPAIR_FOUND"
        )

    final_unplaced.append(
        row
    )


# ============================================================
# VALIDATION
# ============================================================

original_job_count = (
    len(candidate_job_ids)
    + len(unplaced)
)

final_unplaced_ids = {
    str(r["job_id"]).strip()
    for r in final_unplaced
}

all_accounted = (
    final_scheduled_ids
    | final_unplaced_ids
)

no_overlap = (
    final_scheduled_ids
    .isdisjoint(
        final_unplaced_ids
    )
)

route_violations = []

for date in dates:

    jobs = best_state.get(
        (TEAM, date),
        []
    )

    if not jobs:
        continue

    route = best_route(
        jobs
    )

    if (
        route is None
        or route["total_h"]
        > SHIFT_HOURS + 1e-9
    ):

        route_violations.append(
            date
        )


validation = [
    {
        "check":
            "ORIGINAL_JOB_COUNT",
        "expected":
            241,
        "actual":
            original_job_count,
        "status":
            "PASS"
            if original_job_count == 241
            else "FAIL",
    },
    {
        "check":
            "FINAL_SCHEDULED_JOB_COUNT",
        "expected":
            241 - len(final_unplaced),
        "actual":
            len(final_scheduled_ids),
        "status":
            "PASS",
    },
    {
        "check":
            "ALL_JOBS_ACCOUNTED",
        "expected":
            241,
        "actual":
            len(all_accounted),
        "status":
            "PASS"
            if len(all_accounted) == 241
            else "FAIL",
    },
    {
        "check":
            "SCHEDULE_UNPLACED_DISJOINT",
        "expected":
            "YES",
        "actual":
            "YES"
            if no_overlap
            else "NO",
        "status":
            "PASS"
            if no_overlap
            else "FAIL",
    },
    {
        "check":
            "ALL_T001_ROUTES_WITHIN_9H",
        "expected":
            "<=9h",
        "actual":
            "YES"
            if not route_violations
            else "NO",
        "status":
            "PASS"
            if not route_violations
            else "FAIL",
    },
    {
        "check":
            "T001_REPAIR_JOBS_PLACED",
        "expected":
            len(repair_jobs),
        "actual":
            len(placed_repair),
        "status":
            "PASS"
            if len(placed_repair)
            == len(repair_jobs)
            else "REVIEW",
    },
]


# ============================================================
# WRITE OUTPUTS
# ============================================================

if output_rows:

    output_rows.sort(
        key=lambda r: (
            r["schedule_date"],
            r["team_id"],
            int(r["sequence_no"])
        )
    )

    with open(
        OUT_SCHEDULE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        fields = list(
            output_rows[0].keys()
        )

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )


with open(
    OUT_UNPLACED,
    "w",
    newline="",
    encoding="utf-8"
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
        fieldnames=fields
    )

    writer.writeheader()

    for r in final_unplaced:

        writer.writerow(
            {
                k:
                    r.get(
                        k,
                        ""
                    )
                for k in fields
            }
        )


with open(
    OUT_VALIDATION,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "check",
            "expected",
            "actual",
            "status",
        ]
    )

    writer.writeheader()
    writer.writerows(
        validation
    )


overall_status = (
    "PASS"
    if (
        original_job_count == 241
        and len(all_accounted) == 241
        and no_overlap
        and not route_violations
    )
    else "REVIEW_REQUIRED"
)

summary = {
    "status":
        overall_status,
    "original_jobs":
        original_job_count,
    "final_scheduled_jobs":
        len(final_scheduled_ids),
    "final_unplaced_jobs":
        len(final_unplaced),
    "t001_repair_jobs":
        repair_jobs,
    "t001_repair_jobs_placed":
        sorted(
            placed_repair
        ),
    "t001_repair_jobs_remaining":
        sorted(
            remaining_repair
        ),
    "route_violations":
        route_violations,
    "validation":
        {
            r["check"]:
                r["status"]
            for r in validation
        },
}

with open(
    OUT_SUMMARY,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=2
    )


# ============================================================
# FINAL CONSOLE
# ============================================================

print()
print("=" * 80)
print("TARGETED T001 REPAIR RESULT")
print("=" * 80)

print(
    f"Original jobs          : "
    f"{original_job_count}"
)

print(
    f"Final scheduled jobs   : "
    f"{len(final_scheduled_ids)}"
)

print(
    f"Final unplaced jobs    : "
    f"{len(final_unplaced)}"
)

print(
    f"T001 repair placed     : "
    f"{len(placed_repair)}/{len(repair_jobs)}"
)

print(
    f"T001 repair remaining  : "
    f"{remaining_repair}"
)

print(
    f"Route violations       : "
    f"{route_violations}"
)

print()
print("FINAL UNPLACED")
print("-" * 80)

for r in final_unplaced:

    print(
        f"{r['job_id']} | "
        f"{r['team_id']} | "
        f"{r['reason']}"
    )

print()
print("VALIDATION")
print("-" * 80)

for r in validation:

    print(
        f"{r['check']:<35}"
        f"{r['status']}"
    )

print()
print(
    f"OVERALL STATUS : "
    f"{overall_status}"
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
print("TARGETED T001 REPAIR COMPLETE")
print("=" * 80)
