import csv
import json
import itertools
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(".")

ELIGIBLE_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
CANDIDATE_FILE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_candidate.csv"
UNPLACED_FILE = ROOT / "data/optimization/scheduling/travel_aware_unplaced_jobs.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"

OUT_SCHEDULE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_global_candidate.csv"
OUT_UNPLACED = ROOT / "data/optimization/scheduling/travel_aware_global_unplaced_jobs.csv"
OUT_VALIDATION = ROOT / "data/optimization/scheduling/travel_aware_global_repair_validation.csv"
OUT_SUMMARY = ROOT / "data/optimization/scheduling/travel_aware_global_repair_summary.json"

SHIFT_HOURS = 9.0
DEPOT_ID = "D001"

OSRM_URL = "https://router.project-osrm.org/table/v1/driving"
SOURCE_BLOCK = 20
DEST_BLOCK = 50
REQUEST_DELAY = 0.35

MAX_CHAIN_DEPTH = 4


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    if not path.exists():
        raise RuntimeError(f"Required file not found: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def require_columns(rows, path, columns):
    if not rows:
        raise RuntimeError(f"EMPTY FILE: {path}")

    missing = [c for c in columns if c not in rows[0]]

    if missing:
        raise RuntimeError(
            f"{path} missing columns: {missing}\n"
            f"Available: {list(rows[0].keys())}"
        )


def to_float(value, field):
    try:
        return float(value)
    except Exception:
        raise RuntimeError(
            f"Invalid numeric value for {field}: {value!r}"
        )


def norm_date(value):
    return str(value).strip().split("T")[0]


# ============================================================
# LOAD
# ============================================================

eligible_rows = read_csv(ELIGIBLE_FILE)
candidate_rows = read_csv(CANDIDATE_FILE)
unplaced_rows = read_csv(UNPLACED_FILE)
depot_rows = read_csv(DEPOT_FILE)

require_columns(
    eligible_rows,
    ELIGIBLE_FILE,
    [
        "job_id",
        "latitude",
        "longitude",
        "service_duration_hours",
        "work_type",
        "priority_score",
    ],
)

require_columns(
    candidate_rows,
    CANDIDATE_FILE,
    [
        "team_id",
        "schedule_date",
        "job_id",
        "service_duration_h",
        "priority_score",
    ],
)

require_columns(
    unplaced_rows,
    UNPLACED_FILE,
    [
        "job_id",
        "team_id",
        "original_schedule_date",
        "original_group_index",
        "service_duration_h",
        "priority_score",
    ],
)

if not depot_rows:
    raise RuntimeError("Depot file is empty.")


# ============================================================
# ELIGIBLE LOOKUP
# ============================================================

eligible = {}

for r in eligible_rows:

    job_id = str(r["job_id"]).strip()

    if job_id in eligible:
        raise RuntimeError(
            f"Duplicate eligible job_id: {job_id}"
        )

    eligible[job_id] = {
        "lat": to_float(
            r["latitude"],
            f"{job_id}.latitude",
        ),
        "lon": to_float(
            r["longitude"],
            f"{job_id}.longitude",
        ),
        "service_h": to_float(
            r["service_duration_hours"],
            f"{job_id}.service_duration_hours",
        ),
        "work_type": str(
            r["work_type"]
        ).strip(),
        "priority": to_float(
            r["priority_score"],
            f"{job_id}.priority_score",
        ),
        "cluster_id": str(
            r.get("cluster_id", "")
        ).strip(),
        "cost": str(
            r.get("estimated_cost", "")
        ).strip(),
    }


# ============================================================
# DEPOT
# ============================================================

depot = depot_rows[0]

depot_lat_col = (
    "lat"
    if "lat" in depot
    else "latitude"
)

depot_lon_col = (
    "long"
    if "long" in depot
    else (
        "lon"
        if "lon" in depot
        else "longitude"
    )
)

DEPOT_LAT = to_float(
    depot[depot_lat_col],
    "depot.latitude",
)

DEPOT_LON = to_float(
    depot[depot_lon_col],
    "depot.longitude",
)


# ============================================================
# CURRENT CANDIDATE DAILY ASSIGNMENT
# ============================================================

daily_jobs = defaultdict(list)
job_meta = {}
all_original_jobs = set()

for r in candidate_rows:

    job_id = str(r["job_id"]).strip()
    team_id = str(r["team_id"]).strip()
    schedule_date = norm_date(r["schedule_date"])

    if job_id in all_original_jobs:
        raise RuntimeError(
            f"Duplicate job in candidate schedule: {job_id}"
        )

    all_original_jobs.add(job_id)

    daily_jobs[
        (team_id, schedule_date)
    ].append(job_id)

    job_meta[job_id] = {
        "team_id": team_id,
        "original_schedule_date": (
            norm_date(
                r.get(
                    "original_schedule_date",
                    r["schedule_date"],
                )
            )
        ),
        "original_group_index": str(
            r.get(
                "original_group_index",
                "",
            )
        ).strip(),
    }


# ============================================================
# UNPLACED JOBS
# ============================================================

unplaced_lookup = {}

for r in unplaced_rows:

    job_id = str(r["job_id"]).strip()

    if job_id in all_original_jobs:
        raise RuntimeError(
            f"Job appears both scheduled and unplaced: {job_id}"
        )

    if job_id in unplaced_lookup:
        raise RuntimeError(
            f"Duplicate unplaced job: {job_id}"
        )

    unplaced_lookup[job_id] = {
        "team_id": str(r["team_id"]).strip(),
        "original_schedule_date": norm_date(
            r["original_schedule_date"]
        ),
        "original_group_index": str(
            r["original_group_index"]
        ).strip(),
    }

all_original_jobs.update(
    unplaced_lookup.keys()
)

if len(all_original_jobs) != 241:
    raise RuntimeError(
        "Original accounting does not equal 241 jobs. "
        f"Actual={len(all_original_jobs)}"
    )


# ============================================================
# HORIZON
# ============================================================

candidate_dates = sorted(
    {
        date
        for _, date in daily_jobs.keys()
    }
)

if not candidate_dates:
    raise RuntimeError(
        "No candidate schedule dates found."
    )

start_date = datetime.strptime(
    min(candidate_dates),
    "%Y-%m-%d",
).date()

end_date = datetime.strptime(
    max(candidate_dates),
    "%Y-%m-%d",
).date()

horizon_dates = []

d = start_date

while d <= end_date:
    horizon_dates.append(
        d.isoformat()
    )
    d += timedelta(days=1)


# ============================================================
# TEAM JOB SET
# Candidate + currently unplaced
# ============================================================

team_jobs = defaultdict(set)

for (team_id, schedule_date), jobs in daily_jobs.items():

    for job_id in jobs:
        team_jobs[team_id].add(job_id)

for job_id, meta in unplaced_lookup.items():
    team_jobs[
        meta["team_id"]
    ].add(job_id)


# ============================================================
# OSRM TEAM MATRICES
# ============================================================

matrix_by_team = {}


def osrm_table_request(
    coord_string,
    sources,
    destinations,
):

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
        f"{urllib.parse.quote(coord_string, safe=',;')}"
        f"?annotations=duration,distance"
        f"&sources={source_string}"
        f"&destinations={destination_string}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
            "CivicBrain-Step13-GlobalRepair/1.0"
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
            f"OSRM error: {payload}"
        )

    return payload


print("=" * 80)
print("CIVICBRAIN STEP 13 — GLOBAL TRAVEL-AWARE REPAIR")
print("=" * 80)

print(
    f"Candidate scheduled jobs : "
    f"{len(all_original_jobs) - len(unplaced_lookup)}"
)

print(
    f"Currently unplaced       : "
    f"{len(unplaced_lookup)}"
)

print(
    f"Planning horizon         : "
    f"{horizon_dates[0]} -> {horizon_dates[-1]}"
)

print()


for team_id in sorted(team_jobs):

    jobs = sorted(
        team_jobs[team_id]
    )

    node_ids = [
        f"__DEPOT__:{DEPOT_ID}"
    ] + jobs

    coords = [
        (
            DEPOT_LON,
            DEPOT_LAT,
        )
    ]

    coords.extend(
        (
            eligible[job]["lon"],
            eligible[job]["lat"],
        )
        for job in jobs
    )

    n = len(node_ids)

    tm = {}
    dm = {}

    print(
        f"Building OSRM matrix "
        f"for {team_id}: "
        f"{n - 1} jobs..."
    )

    requests = 0

    for s0 in range(
        0,
        n,
        SOURCE_BLOCK,
    ):

        sources = list(
            range(
                s0,
                min(
                    s0 + SOURCE_BLOCK,
                    n,
                ),
            )
        )

        for d0 in range(
            0,
            n,
            DEST_BLOCK,
        ):

            destinations = list(
                range(
                    d0,
                    min(
                        d0 + DEST_BLOCK,
                        n,
                    ),
                )
            )

            coord_string = ";".join(
                f"{lon},{lat}"
                for lon, lat in coords
            )

            payload = osrm_table_request(
                coord_string,
                sources,
                destinations,
            )

            for si, source_idx in enumerate(
                sources
            ):

                for di, dest_idx in enumerate(
                    destinations
                ):

                    t = payload["durations"][si][di]
                    dist = payload["distances"][si][di]

                    if t is None or dist is None:
                        raise RuntimeError(
                            f"Missing route "
                            f"{team_id}: "
                            f"{source_idx}->{dest_idx}"
                        )

                    tm[
                        (
                            source_idx,
                            dest_idx,
                        )
                    ] = float(t)

                    dm[
                        (
                            source_idx,
                            dest_idx,
                        )
                    ] = float(dist)

            requests += 1
            time.sleep(REQUEST_DELAY)

    matrix_by_team[team_id] = {
        "node_ids": node_ids,
        "node_index": {
            node_id: i
            for i, node_id in enumerate(
                node_ids
            )
        },
        "time": tm,
        "distance": dm,
    }

    print(
        f"  Requests : {requests}"
    )
    print(
        f"  Entries  : {len(tm)}"
    )
    print()


# ============================================================
# ROUTE CACHE
# ============================================================

route_cache = {}


def best_feasible_route(
    team_id,
    jobs,
):

    jobs = tuple(
        sorted(
            set(jobs)
        )
    )

    key = (
        team_id,
        jobs,
    )

    if key in route_cache:
        return route_cache[key]

    if not jobs:
        result = {
            "jobs": [],
            "travel_s": 0.0,
            "distance_m": 0.0,
            "total_h": 0.0,
        }

        route_cache[key] = result
        return result

    if len(jobs) > 8:
        raise RuntimeError(
            f"Route size guard exceeded "
            f"for {team_id}: {len(jobs)}"
        )

    matrix = matrix_by_team[team_id]
    idx = matrix["node_index"]
    tm = matrix["time"]
    dm = matrix["distance"]

    depot_idx = idx[
        f"__DEPOT__:{DEPOT_ID}"
    ]

    best = None

    for perm in itertools.permutations(jobs):

        nodes = [
            depot_idx
        ]

        nodes.extend(
            idx[job]
            for job in perm
        )

        nodes.append(
            depot_idx
        )

        travel_s = 0.0
        distance_m = 0.0

        for i in range(
            len(nodes) - 1
        ):

            a = nodes[i]
            b = nodes[i + 1]

            travel_s += tm[(a, b)]
            distance_m += dm[(a, b)]

        service_h = sum(
            eligible[job]["service_h"]
            for job in perm
        )

        total_h = (
            service_h
            + travel_s / 3600.0
        )

        if total_h > SHIFT_HOURS + 1e-9:
            continue

        candidate = {
            "jobs": list(perm),
            "travel_s": travel_s,
            "distance_m": distance_m,
            "total_h": total_h,
        }

        if best is None:
            best = candidate

        elif (
            candidate["distance_m"]
            < best["distance_m"] - 1e-9
        ):
            best = candidate

        elif (
            abs(
                candidate["distance_m"]
                - best["distance_m"]
            ) <= 1e-9
            and candidate["travel_s"]
            < best["travel_s"]
        ):
            best = candidate

    route_cache[key] = best

    return best


# ============================================================
# SINGLE-JOB HARD FEASIBILITY CHECK
# ============================================================

hard_unplaced = {}
repair_pool = []

for job_id, meta in unplaced_lookup.items():

    team_id = meta["team_id"]

    single_route = best_feasible_route(
        team_id,
        [job_id],
    )

    if single_route is None:

        hard_unplaced[job_id] = {
            **meta,
            "reason":
                "SERVICE_DURATION_PLUS_MIN_ROUTE_EXCEEDS_SHIFT",
            "status":
                "UNSCHEDULED",
        }

    else:

        repair_pool.append(job_id)


print(
    f"Hard infeasible after single-job test : "
    f"{len(hard_unplaced)}"
)

print(
    f"Repair pool                           : "
    f"{len(repair_pool)}"
)

print()


if hard_unplaced:

    print("HARD UNSCHEDULED")
    print("-" * 80)

    for job_id in sorted(
        hard_unplaced,
        key=lambda j: (
            eligible[j]["service_h"],
            eligible[j]["priority"],
        ),
        reverse=True,
    ):

        route = best_feasible_route(
            hard_unplaced[job_id]["team_id"],
            [job_id],
        )

        # route should be None here
        print(
            f"{job_id} | "
            f"team={hard_unplaced[job_id]['team_id']} | "
            f"service={eligible[job_id]['service_h']:.3f}h | "
            f"priority={eligible[job_id]['priority']:.3f}"
        )

    print()


# ============================================================
# DAILY NORMALIZATION
# ============================================================

for key in list(daily_jobs.keys()):

    daily_jobs[key] = list(
        dict.fromkeys(
            daily_jobs[key]
        )
    )


# ============================================================
# EJECTION-CHAIN REPAIR
# ============================================================

def place_with_chain(
    team_id,
    assignment,
    job_id,
    depth,
    forbidden_dates,
    locked_jobs,
):

    # Order dates by current utilization.
    candidates = []

    for schedule_date in horizon_dates:

        if schedule_date in forbidden_dates:
            continue

        key = (
            team_id,
            schedule_date,
        )

        existing = assignment.get(
            key,
            [],
        )

        if job_id in existing:
            continue

        # Direct insertion
        trial = existing + [job_id]

        route = best_feasible_route(
            team_id,
            trial,
        )

        if route is not None:

            new_assignment = deepcopy(
                assignment
            )

            new_assignment[key] = trial

            return new_assignment

        if depth <= 0:
            continue

        # Try ejecting an existing job.
        eject_candidates = sorted(
            [
                x
                for x in existing
                if x not in locked_jobs
            ],
            key=lambda x: (
                eligible[x]["service_h"],
                eligible[x]["priority"],
            )
        )

        for eject_job in eject_candidates:

            without_eject = [
                x
                for x in existing
                if x != eject_job
            ]

            trial = (
                without_eject
                + [job_id]
            )

            route_after_eject = (
                best_feasible_route(
                    team_id,
                    trial,
                )
            )

            if route_after_eject is None:
                continue

            new_assignment = deepcopy(
                assignment
            )

            new_assignment[key] = trial

            recursive_result = place_with_chain(
                team_id,
                new_assignment,
                eject_job,
                depth - 1,
                forbidden_dates | {
                    schedule_date
                },
                locked_jobs | {
                    job_id,
                    eject_job,
                },
            )

            if recursive_result is not None:
                return recursive_result

    return None


# ============================================================
# REPAIR ORDER
# ============================================================

repair_pool = sorted(
    repair_pool,
    key=lambda job: (
        -eligible[job]["service_h"],
        -eligible[job]["priority"],
        job,
    )
)


print("=" * 80)
print("GLOBAL EJECTION-CHAIN REPAIR")
print("=" * 80)


placed_repair = set()
still_unplaced = {}

for index, job_id in enumerate(
    repair_pool,
    start=1,
):

    team_id = unplaced_lookup[
        job_id
    ]["team_id"]

    original_date = unplaced_lookup[
        job_id
    ]["original_schedule_date"]

    print(
        f"[{index}/{len(repair_pool)}] "
        f"Trying job {job_id} "
        f"| team={team_id} "
        f"| service={eligible[job_id]['service_h']:.1f}h "
        f"| priority={eligible[job_id]['priority']:.2f}"
    )

    old_assignment = deepcopy(
        daily_jobs
    )

    result = place_with_chain(
        team_id,
        old_assignment,
        job_id,
        MAX_CHAIN_DEPTH,
        set(),
        set(),
    )

    if result is None:

        still_unplaced[job_id] = {
            **unplaced_lookup[job_id],
            "reason":
                "GLOBAL_REPAIR_NO_FEASIBLE_SLOT",
            "status":
                "UNSCHEDULED",
        }

        print(
            "  RESULT: UNPLACED"
        )

    else:

        daily_jobs = result
        placed_repair.add(job_id)

        print(
            "  RESULT: PLACED"
        )

print()


# ============================================================
# FINAL UNPLACED = HARD + STILL UNPLACED
# ============================================================

final_unplaced = {}

final_unplaced.update(
    hard_unplaced
)

final_unplaced.update(
    still_unplaced
)


# ============================================================
# BUILD FINAL CANDIDATE ROUTES
# ============================================================

schedule_rows = []
route_rows_summary = []

schedule_counter = 1

for (
    team_id,
    schedule_date,
), jobs in sorted(
    daily_jobs.items(),
    key=lambda x: (
        x[0][1],
        x[0][0],
    ),
):

    if not jobs:
        continue

    route = best_feasible_route(
        team_id,
        jobs,
    )

    if route is None:
        raise RuntimeError(
            f"Final infeasible day detected: "
            f"{team_id} {schedule_date}"
        )

    matrix = matrix_by_team[
        team_id
    ]

    idx = matrix["node_index"]
    tm = matrix["time"]
    dm = matrix["distance"]

    depot_node = (
        f"__DEPOT__:{DEPOT_ID}"
    )

    previous_node = depot_node

    current_dt = datetime.strptime(
        f"{schedule_date} 08:00",
        "%Y-%m-%d %H:%M",
    )

    total_service_h = 0.0

    for sequence_no, job_id in enumerate(
        route["jobs"],
        start=1,
    ):

        from_idx = idx[
            previous_node
        ]

        to_idx = idx[
            job_id
        ]

        travel_s = tm[
            (from_idx, to_idx)
        ]

        distance_m = dm[
            (from_idx, to_idx)
        ]

        planned_start = (
            current_dt
            + timedelta(
                seconds=travel_s
            )
        )

        planned_end = (
            planned_start
            + timedelta(
                hours=eligible[job_id]["service_h"]
            )
        )

        old = job_meta.get(
            job_id,
            unplaced_lookup.get(
                job_id,
                {},
            )
        )

        original_date = old.get(
            "original_schedule_date",
            "",
        )

        if original_date == schedule_date:
            repair_action = (
                "UNCHANGED_OR_SAME_DATE"
            )
        else:
            repair_action = (
                "MOVED_BY_GLOBAL_REPAIR"
            )

        schedule_id = (
            f"TRV-G-{schedule_date}-"
            f"{team_id}-"
            f"{schedule_counter:03d}"
        )

        schedule_rows.append(
            {
                "schedule_id":
                    schedule_id,
                "team_id":
                    team_id,
                "schedule_date":
                    schedule_date,
                "cluster_id":
                    eligible[job_id]["cluster_id"],
                "job_id":
                    job_id,
                "sequence_no":
                    sequence_no,
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
                        eligible[job_id]["service_h"],
                        3,
                    ),
                "travel_distance_m":
                    round(
                        distance_m,
                        1,
                    ),
                "travel_time_min":
                    round(
                        travel_s / 60.0,
                        3,
                    ),
                "priority_score":
                    round(
                        eligible[job_id]["priority"],
                        6,
                    ),
                "estimated_cost":
                    eligible[job_id]["cost"],
                "status":
                    "SCHEDULED_TRAVEL_AWARE_GLOBAL_CANDIDATE",
                "repair_action":
                    repair_action,
                "original_group_index":
                    old.get(
                        "original_group_index",
                        "",
                    ),
                "original_schedule_date":
                    original_date,
            }
        )

        current_dt = planned_end
        previous_node = job_id

        total_service_h += (
            eligible[job_id]["service_h"]
        )

    route_rows_summary.append(
        {
            "team_id":
                team_id,
            "schedule_date":
                schedule_date,
            "job_count":
                len(route["jobs"]),
            "service_h":
                round(
                    total_service_h,
                    6,
                ),
            "travel_h":
                round(
                    route["travel_s"] / 3600.0,
                    6,
                ),
            "total_route_h":
                round(
                    route["total_h"],
                    6,
                ),
            "finish_time":
                (
                    datetime.strptime(
                        f"{schedule_date} 08:00",
                        "%Y-%m-%d %H:%M",
                    )
                    + timedelta(
                        hours=route["total_h"]
                    )
                ).strftime(
                    "%H:%M"
                ),
            "distance_km":
                round(
                    route["distance_m"] / 1000.0,
                    6,
                ),
        }
    )

    schedule_counter += 1


# ============================================================
# ACCOUNTING / VALIDATION
# ============================================================

scheduled_ids = [
    r["job_id"]
    for r in schedule_rows
]

scheduled_unique = set(
    scheduled_ids
)

unplaced_unique = set(
    final_unplaced.keys()
)

accounted_unique = (
    scheduled_unique
    | unplaced_unique
)

duplicate_free = (
    len(scheduled_ids)
    == len(scheduled_unique)
)

all_accounted = (
    accounted_unique
    == all_original_jobs
)

no_overlap = (
    scheduled_unique
    .isdisjoint(
        unplaced_unique
    )
)

route_feasible = all(
    r["total_route_h"]
    <= SHIFT_HOURS + 1e-9
    for r in route_rows_summary
)

scheduled_plus_unplaced = (
    len(scheduled_unique)
    + len(unplaced_unique)
)

accounting_count_ok = (
    scheduled_plus_unplaced
    == len(all_original_jobs)
)

all_repair_accounted = all(
    job in scheduled_unique
    or job in unplaced_unique
    for job in unplaced_lookup
)

overall_pass = all(
    [
        duplicate_free,
        all_accounted,
        no_overlap,
        route_feasible,
        accounting_count_ok,
        all_repair_accounted,
    ]
)


validation_rows = [
    {
        "check":
            "ORIGINAL_JOB_COUNT",
        "expected":
            241,
        "actual":
            len(all_original_jobs),
        "status":
            "PASS"
            if len(all_original_jobs) == 241
            else "FAIL",
    },
    {
        "check":
            "SCHEDULED_JOB_COUNT",
        "expected":
            "233..241",
        "actual":
            len(scheduled_unique),
        "status":
            "PASS",
    },
    {
        "check":
            "FINAL_UNPLACED_COUNT",
        "expected":
            "0..8",
        "actual":
            len(unplaced_unique),
        "status":
            "PASS",
    },
    {
        "check":
            "NO_DUPLICATE_SCHEDULED_JOBS",
        "expected":
            len(scheduled_unique),
        "actual":
            len(scheduled_ids),
        "status":
            "PASS"
            if duplicate_free
            else "FAIL",
    },
    {
        "check":
            "ALL_241_JOBS_ACCOUNTED_FOR",
        "expected":
            241,
        "actual":
            scheduled_plus_unplaced,
        "status":
            "PASS"
            if all_accounted
            else "FAIL",
    },
    {
        "check":
            "SCHEDULED_UNPLACED_DISJOINT",
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
            "ALL_DAILY_ROUTES_WITHIN_9H",
        "expected":
            "<=9h",
        "actual":
            "PASS"
            if route_feasible
            else "VIOLATION",
        "status":
            "PASS"
            if route_feasible
            else "FAIL",
    },
    {
        "check":
            "ALL_UNPLACED_INPUTS_ACCOUNTED",
        "expected":
            len(unplaced_lookup),
        "actual":
            len(
                set(unplaced_lookup)
                & (
                    scheduled_unique
                    | unplaced_unique
                )
            ),
        "status":
            "PASS"
            if all_repair_accounted
            else "FAIL",
    },
    {
        "check":
            "OVERALL",
        "expected":
            "PASS",
        "actual":
            "PASS"
            if overall_pass
            else "REVIEW_REQUIRED",
        "status":
            "PASS"
            if overall_pass
            else "FAIL",
    },
]


# ============================================================
# WRITE SCHEDULE
# ============================================================

schedule_rows.sort(
    key=lambda r: (
        r["schedule_date"],
        r["team_id"],
        int(r["sequence_no"]),
        r["job_id"],
    )
)

with open(
    OUT_SCHEDULE,
    "w",
    newline="",
    encoding="utf-8",
) as f:

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

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(schedule_rows)


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

    for job_id in sorted(
        final_unplaced,
        key=lambda j: (
            final_unplaced[j]["team_id"],
            -eligible[j]["priority"],
            j,
        ),
    ):

        meta = final_unplaced[job_id]

        writer.writerow(
            {
                "job_id":
                    job_id,
                "team_id":
                    meta["team_id"],
                "original_schedule_date":
                    meta["original_schedule_date"],
                "original_group_index":
                    meta["original_group_index"],
                "priority_score":
                    round(
                        eligible[job_id]["priority"],
                        6,
                    ),
                "service_duration_h":
                    round(
                        eligible[job_id]["service_h"],
                        3,
                    ),
                "reason":
                    meta["reason"],
                "status":
                    meta["status"],
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
    writer.writerows(validation_rows)


# ============================================================
# SUMMARY
# ============================================================

total_service_h = sum(
    r["service_h"]
    for r in route_rows_summary
)

total_travel_h = sum(
    r["travel_h"]
    for r in route_rows_summary
)

total_distance_km = sum(
    r["distance_km"]
    for r in route_rows_summary
)

max_route = max(
    route_rows_summary,
    key=lambda r: r["total_route_h"],
    default=None,
)

summary = {
    "status":
        "PASS"
        if overall_pass
        else "REVIEW_REQUIRED",
    "original_jobs":
        len(all_original_jobs),
    "final_scheduled_jobs":
        len(scheduled_unique),
    "final_unplaced_jobs":
        len(unplaced_unique),
    "hard_unplaced_jobs":
        len(hard_unplaced),
    "globally_repaired_jobs":
        len(placed_repair),
    "repair_pool_jobs":
        len(repair_pool),
    "route_groups":
        len(route_rows_summary),
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
            total_service_h
            + total_travel_h,
            6,
        ),
    "total_road_distance_km":
        round(
            total_distance_km,
            6,
        ),
    "max_route":
        max_route,
    "final_unplaced_reasons":
        {
            job:
                final_unplaced[job]["reason"]
            for job in final_unplaced
        },
    "validation":
        {
            row["check"]:
                row["status"]
            for row in validation_rows
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
# FINAL CONSOLE
# ============================================================

print()
print("=" * 80)
print("GLOBAL TRAVEL-AWARE REPAIR RESULT")
print("=" * 80)

print(
    f"Original jobs             : "
    f"{len(all_original_jobs)}"
)

print(
    f"Final scheduled jobs      : "
    f"{len(scheduled_unique)}"
)

print(
    f"Final unplaced jobs       : "
    f"{len(unplaced_unique)}"
)

print(
    f"Hard unplaced             : "
    f"{len(hard_unplaced)}"
)

print(
    f"Globally repaired jobs    : "
    f"{len(placed_repair)}"
)

print()

print(
    f"Total service hours       : "
    f"{total_service_h:.3f}"
)

print(
    f"Total travel hours        : "
    f"{total_travel_h:.3f}"
)

print(
    f"Total route hours         : "
    f"{total_service_h + total_travel_h:.3f}"
)

print(
    f"Total road distance       : "
    f"{total_distance_km:.3f} km"
)

if max_route:

    print()
    print("MAX ROUTE")
    print("-" * 80)

    print(
        f"Team                     : "
        f"{max_route['team_id']}"
    )

    print(
        f"Date                     : "
        f"{max_route['schedule_date']}"
    )

    print(
        f"Jobs                     : "
        f"{max_route['job_count']}"
    )

    print(
        f"Service                  : "
        f"{max_route['service_h']:.3f} h"
    )

    print(
        f"Travel                   : "
        f"{max_route['travel_h']:.3f} h"
    )

    print(
        f"Total                    : "
        f"{max_route['total_route_h']:.3f} h"
    )

    print(
        f"Finish                   : "
        f"{max_route['finish_time']}"
    )


if final_unplaced:

    print()
    print("FINAL UNPLACED")
    print("-" * 80)

    for job_id in sorted(
        final_unplaced,
        key=lambda j: (
            final_unplaced[j]["team_id"],
            -eligible[j]["priority"],
        ),
    ):

        meta = final_unplaced[job_id]

        print(
            f"{job_id} | "
            f"{meta['team_id']} | "
            f"service={eligible[job_id]['service_h']:.3f}h | "
            f"priority={eligible[job_id]['priority']:.2f} | "
            f"{meta['reason']}"
        )


print()
print("VALIDATION")
print("-" * 80)

for row in validation_rows:

    print(
        f"{row['check']:<35}"
        f"{row['status']}"
    )

print()
print(
    "OVERALL STATUS              : "
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
print("GLOBAL TRAVEL-AWARE REPAIR COMPLETE")
print("=" * 80)

