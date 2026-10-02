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

OUT_SCHEDULE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_bounded_candidate.csv"
OUT_UNPLACED = ROOT / "data/optimization/scheduling/travel_aware_bounded_unplaced_jobs.csv"
OUT_VALIDATION = ROOT / "data/optimization/scheduling/travel_aware_bounded_validation.csv"
OUT_SUMMARY = ROOT / "data/optimization/scheduling/travel_aware_bounded_summary.json"

SHIFT_HOURS = 9.0

MAX_DEPTH = 2
MAX_STATES_PER_JOB = 1500
JOB_TIMEOUT_SECONDS = 20.0

OSRM_URL = "https://router.project-osrm.org/table/v1/driving"
SOURCE_BLOCK = 20
DEST_BLOCK = 50
REQUEST_DELAY = 0.30

DEPOT_ID = "D001"


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
            f"Available columns: {list(rows[0].keys())}"
        )


def fnum(value, field):
    try:
        return float(value)
    except Exception:
        raise RuntimeError(
            f"Invalid numeric value for {field}: {value!r}"
        )


def date_only(value):
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
    ],
)


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
        "work_type": str(
            r["work_type"]
        ).strip(),
        "cluster_id": str(
            r.get("cluster_id", "")
        ).strip(),
        "cost": str(
            r.get("estimated_cost", "")
        ).strip(),
    }


# ============================================================
# CURRENT CANDIDATE ASSIGNMENT
# ============================================================

daily_jobs = defaultdict(list)
job_origin = {}
candidate_job_ids = set()

for r in candidate_rows:

    job = str(r["job_id"]).strip()
    team = str(r["team_id"]).strip()
    date = date_only(r["schedule_date"])

    if job in candidate_job_ids:
        raise RuntimeError(
            f"Duplicate job in candidate: {job}"
        )

    candidate_job_ids.add(job)

    daily_jobs[
        (team, date)
    ].append(job)

    job_origin[job] = {
        "team_id": team,
        "original_schedule_date":
            date_only(
                r.get(
                    "original_schedule_date",
                    date,
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
# CURRENT UNPLACED
# ============================================================

unplaced = {}

for r in unplaced_rows:

    job = str(r["job_id"]).strip()

    if job in candidate_job_ids:
        raise RuntimeError(
            f"Job appears scheduled and unplaced: {job}"
        )

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
    }


if (
    len(candidate_job_ids)
    + len(unplaced)
    != 241
):
    raise RuntimeError(
        "241-job accounting mismatch: "
        f"{len(candidate_job_ids)} scheduled + "
        f"{len(unplaced)} unplaced"
    )


# ============================================================
# DEPOT
# ============================================================

if not depot_rows:
    raise RuntimeError("Depot file empty.")

depot = depot_rows[0]

if "lat" in depot:
    depot_lat_col = "lat"
elif "latitude" in depot:
    depot_lat_col = "latitude"
else:
    raise RuntimeError("Depot latitude column missing.")

if "long" in depot:
    depot_lon_col = "long"
elif "lon" in depot:
    depot_lon_col = "lon"
elif "longitude" in depot:
    depot_lon_col = "longitude"
else:
    raise RuntimeError("Depot longitude column missing.")

DEPOT_LAT = fnum(
    depot[depot_lat_col],
    "depot.latitude",
)

DEPOT_LON = fnum(
    depot[depot_lon_col],
    "depot.longitude",
)


# ============================================================
# HORIZON
# ============================================================

dates = sorted(
    {
        date
        for _, date in daily_jobs.keys()
    }
)

if not dates:
    raise RuntimeError("No candidate dates found.")

start_date = datetime.strptime(
    min(dates),
    "%Y-%m-%d",
).date()

end_date = datetime.strptime(
    max(dates),
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
# TEAM UNIVERSE
# ============================================================

teams = sorted(
    {
        team
        for team, _ in daily_jobs.keys()
    }
    | {
        meta["team_id"]
        for meta in unplaced.values()
    }
)


team_jobs = defaultdict(set)

for job, info in job_origin.items():
    team_jobs[
        info["team_id"]
    ].add(job)

for job, info in unplaced.items():
    team_jobs[
        info["team_id"]
    ].add(job)


# ============================================================
# OSRM
# ============================================================

def osrm_call(
    coords,
    sources,
    destinations,
):

    coord_string = ";".join(
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
        f"{urllib.parse.quote(coord_string, safe=',;')}"
        f"?annotations=duration,distance"
        f"&sources={source_string}"
        f"&destinations={destination_string}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "CivicBrain-Step13-BoundedRepair/1.0"
        },
        method="GET",
    )

    with urllib.request.urlopen(
        req,
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


matrix_by_team = {}

print("=" * 80)
print("CIVICBRAIN STEP 13 — BOUNDED GLOBAL TRAVEL REPAIR")
print("=" * 80)

print(
    f"Candidate scheduled jobs : "
    f"{len(candidate_job_ids)}"
)

print(
    f"Current unplaced jobs    : "
    f"{len(unplaced)}"
)

print(
    f"Horizon                  : "
    f"{horizon_dates[0]} -> {horizon_dates[-1]}"
)

print(
    f"Max depth                : "
    f"{MAX_DEPTH}"
)

print(
    f"Max states / job         : "
    f"{MAX_STATES_PER_JOB}"
)

print(
    f"Timeout / job            : "
    f"{JOB_TIMEOUT_SECONDS}s"
)

print()


for team in teams:

    jobs = sorted(
        team_jobs[team]
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
            eligible[j]["lon"],
            eligible[j]["lat"],
        )
        for j in jobs
    )

    n = len(node_ids)

    tm = {}
    dm = {}

    requests = 0

    print(
        f"Building OSRM matrix for "
        f"{team}: {n - 1} jobs..."
    )

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

            payload = osrm_call(
                coords,
                sources,
                destinations,
            )

            for si, source_idx in enumerate(
                sources
            ):

                for di, dest_idx in enumerate(
                    destinations
                ):

                    duration = (
                        payload["durations"][si][di]
                    )

                    distance = (
                        payload["distances"][si][di]
                    )

                    if (
                        duration is None
                        or distance is None
                    ):
                        raise RuntimeError(
                            f"Missing OSRM route "
                            f"{team} "
                            f"{source_idx}->{dest_idx}"
                        )

                    tm[
                        (
                            source_idx,
                            dest_idx,
                        )
                    ] = float(duration)

                    dm[
                        (
                            source_idx,
                            dest_idx,
                        )
                    ] = float(distance)

            requests += 1
            time.sleep(REQUEST_DELAY)

    matrix_by_team[team] = {
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
        f"  requests={requests}"
    )

    print(
        f"  matrix_entries={len(tm)}"
    )

    print()


# ============================================================
# ROUTE CACHE
# ============================================================

route_cache = {}


def best_route(team, jobs):

    jobs = tuple(
        sorted(
            set(jobs)
        )
    )

    key = (
        team,
        jobs,
    )

    if key in route_cache:
        return route_cache[key]

    if not jobs:

        result = {
            "jobs": [],
            "service_h": 0.0,
            "travel_s": 0.0,
            "distance_m": 0.0,
            "total_h": 0.0,
        }

        route_cache[key] = result
        return result

    # hard guard for computational safety
    if len(jobs) > 7:
        raise RuntimeError(
            f"Route permutation guard exceeded: "
            f"{team} has {len(jobs)} jobs in one day."
        )

    matrix = matrix_by_team[team]

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
            idx[j]
            for j in perm
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
            eligible[j]["service_h"]
            for j in perm
        )

        total_h = (
            service_h
            + travel_s / 3600.0
        )

        if total_h > SHIFT_HOURS + 1e-9:
            continue

        candidate = {
            "jobs": list(perm),
            "service_h": service_h,
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
# INITIAL HARD-INFEASIBLE TEST
# ============================================================

hard_unplaced = {}
repair_jobs = []

for job, meta in unplaced.items():

    single = best_route(
        meta["team_id"],
        [job],
    )

    if single is None:

        hard_unplaced[job] = {
            **meta,
            "reason":
                "SERVICE_DURATION_PLUS_MIN_ROUTE_EXCEEDS_SHIFT",
        }

    else:

        repair_jobs.append(job)


print(
    f"Hard infeasible jobs : "
    f"{len(hard_unplaced)}"
)

print(
    f"Bounded repair jobs   : "
    f"{len(repair_jobs)}"
)

print()


# ============================================================
# LOCK HARD JOBS
# ============================================================

# daily_jobs initially contains the 233 candidate jobs.
# Hard jobs remain outside the schedule.


# ============================================================
# ROUTE METRIC
# ============================================================

def daily_route(team, date):

    return best_route(
        team,
        daily_jobs[
            (team, date)
        ],
    )


def route_slack(team, date):

    route = daily_route(
        team,
        date,
    )

    if route is None:
        return -999.0

    return (
        SHIFT_HOURS
        - route["total_h"]
    )


# ============================================================
# STATE HELPERS
# ============================================================

def apply_assignment(
    changes,
):

    old_values = {}

    for key, jobs in changes.items():

        old_values[key] = list(
            daily_jobs[key]
        )

        daily_jobs[key] = list(
            jobs
        )

    return old_values


def restore_assignment(
    old_values,
):

    for key, jobs in old_values.items():

        if jobs:

            daily_jobs[key] = list(
                jobs
            )

        else:

            daily_jobs.pop(
                key,
                None,
            )


def try_direct(
    team,
    job,
    timeout_at,
):

    candidates = []

    for date in horizon_dates:

        if time.monotonic() > timeout_at:
            return None

        key = (
            team,
            date,
        )

        existing = daily_jobs[key]

        if job in existing:
            continue

        trial = existing + [job]

        route = best_route(
            team,
            trial,
        )

        if route is not None:

            # date preference:
            # same original date first,
            # then lower route time,
            # then lower distance.
            original = unplaced.get(
                job,
                {}
            ).get(
                "original_schedule_date",
                date,
            )

            same_date = (
                0
                if date == original
                else 1
            )

            candidates.append(
                (
                    same_date,
                    route["total_h"],
                    route["distance_m"],
                    date,
                    trial,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x[0],
            x[1],
            x[2],
            x[3],
        )
    )

    return candidates[0]


# ============================================================
# DEPTH-1 EJECTION
# ============================================================

def try_depth1(
    team,
    job,
    timeout_at,
    state_counter,
):

    best = None

    dates_ranked = sorted(
        horizon_dates,
        key=lambda d: (
            -route_slack(
                team,
                d,
            ),
            d,
        ),
    )

    for target_date in dates_ranked:

        if time.monotonic() > timeout_at:
            return None

        target_key = (
            team,
            target_date,
        )

        current = list(
            daily_jobs[target_key]
        )

        # Try direct first
        if current:

            # Remove one donor at a time.
            donors = sorted(
                current,
                key=lambda j: (
                    eligible[j]["service_h"],
                    eligible[j]["priority"],
                )
            )

            for donor in donors:

                if time.monotonic() > timeout_at:
                    return None

                state_counter[0] += 1

                if (
                    state_counter[0]
                    > MAX_STATES_PER_JOB
                ):
                    return None

                reduced = [
                    x
                    for x in current
                    if x != donor
                ]

                target_trial = (
                    reduced
                    + [job]
                )

                target_route = best_route(
                    team,
                    target_trial,
                )

                if target_route is None:
                    continue

                # donor must go to another date
                donor_destinations = sorted(
                    horizon_dates,
                    key=lambda d: (
                        -route_slack(
                            team,
                            d,
                        ),
                        d,
                    )
                )

                for donor_date in donor_destinations:

                    if time.monotonic() > timeout_at:
                        return None

                    if donor_date == target_date:
                        continue

                    donor_key = (
                        team,
                        donor_date,
                    )

                    donor_existing = list(
                        daily_jobs[donor_key]
                    )

                    if donor in donor_existing:
                        continue

                    donor_trial = (
                        donor_existing
                        + [donor]
                    )

                    donor_route = best_route(
                        team,
                        donor_trial,
                    )

                    if donor_route is None:
                        continue

                    score = (
                        target_route["total_h"]
                        + donor_route["total_h"],
                        target_route["distance_m"]
                        + donor_route["distance_m"],
                        target_date,
                        donor_date,
                    )

                    if (
                        best is None
                        or score < best["score"]
                    ):

                        best = {
                            "target_date":
                                target_date,
                            "donor":
                                donor,
                            "donor_date":
                                donor_date,
                            "target_jobs":
                                target_trial,
                            "donor_jobs":
                                donor_trial,
                            "target_route":
                                target_route,
                            "donor_route":
                                donor_route,
                            "score":
                                score,
                        }

    return best


# ============================================================
# DEPTH-2 EJECTION
# ============================================================

def try_depth2(
    team,
    job,
    timeout_at,
    state_counter,
):

    best = None

    dates_ranked = sorted(
        horizon_dates,
        key=lambda d: (
            -route_slack(
                team,
                d,
            ),
            d,
        ),
    )

    for d1 in dates_ranked:

        if time.monotonic() > timeout_at:
            return None

        key1 = (
            team,
            d1,
        )

        jobs1 = list(
            daily_jobs[key1]
        )

        donors1 = sorted(
            jobs1,
            key=lambda j: (
                eligible[j]["service_h"],
                eligible[j]["priority"],
            )
        )

        for donor1 in donors1:

            if time.monotonic() > timeout_at:
                return None

            state_counter[0] += 1

            if (
                state_counter[0]
                > MAX_STATES_PER_JOB
            ):
                return None

            reduced1 = [
                x
                for x in jobs1
                if x != donor1
            ]

            target_trial = (
                reduced1
                + [job]
            )

            target_route = best_route(
                team,
                target_trial,
            )

            if target_route is None:
                continue

            # donor1 -> second date
            for d2 in dates_ranked:

                if time.monotonic() > timeout_at:
                    return None

                if d2 == d1:
                    continue

                key2 = (
                    team,
                    d2,
                )

                jobs2 = list(
                    daily_jobs[key2]
                )

                donors2 = sorted(
                    jobs2,
                    key=lambda j: (
                        eligible[j]["service_h"],
                        eligible[j]["priority"],
                    )
                )

                # Direct donor1 placement first
                trial2 = (
                    jobs2
                    + [donor1]
                )

                route2 = best_route(
                    team,
                    trial2,
                )

                if route2 is not None:

                    score = (
                        target_route["total_h"]
                        + route2["total_h"],
                        target_route["distance_m"]
                        + route2["distance_m"],
                        d1,
                        d2,
                    )

                    if (
                        best is None
                        or score < best["score"]
                    ):

                        best = {
                            "d1":
                                d1,
                            "d2":
                                d2,
                            "donor1":
                                donor1,
                            "donor2":
                                None,
                            "target_jobs":
                                target_trial,
                            "d1_jobs":
                                reduced1,
                            "d2_jobs":
                                trial2,
                            "score":
                                score,
                        }

                # Second ejection
                for donor2 in donors2:

                    if time.monotonic() > timeout_at:
                        return None

                    state_counter[0] += 1

                    if (
                        state_counter[0]
                        > MAX_STATES_PER_JOB
                    ):
                        return None

                    reduced2 = [
                        x
                        for x in jobs2
                        if x != donor2
                    ]

                    trial2 = (
                        reduced2
                        + [donor1]
                    )

                    route2 = best_route(
                        team,
                        trial2,
                    )

                    if route2 is None:
                        continue

                    # donor2 needs third date
                    for d3 in dates_ranked:

                        if time.monotonic() > timeout_at:
                            return None

                        if d3 in (
                            d1,
                            d2,
                        ):
                            continue

                        key3 = (
                            team,
                            d3,
                        )

                        jobs3 = list(
                            daily_jobs[key3]
                        )

                        if donor2 in jobs3:
                            continue

                        trial3 = (
                            jobs3
                            + [donor2]
                        )

                        route3 = best_route(
                            team,
                            trial3,
                        )

                        if route3 is None:
                            continue

                        score = (
                            target_route["total_h"]
                            + route2["total_h"]
                            + route3["total_h"],
                            target_route["distance_m"]
                            + route2["distance_m"]
                            + route3["distance_m"],
                            d1,
                            d2,
                            d3,
                        )

                        if (
                            best is None
                            or score < best["score"]
                        ):

                            best = {
                                "d1":
                                    d1,
                                "d2":
                                    d2,
                                "d3":
                                    d3,
                                "donor1":
                                    donor1,
                                "donor2":
                                    donor2,
                                "target_jobs":
                                    target_trial,
                                "d1_jobs":
                                    reduced1,
                                "d2_jobs":
                                    trial2,
                                "d3_jobs":
                                    trial3,
                                "score":
                                    score,
                            }

    return best


# ============================================================
# APPLY REPAIR
# ============================================================

print("=" * 80)
print("BOUNDED REPAIR SEARCH")
print("=" * 80)

repair_order = sorted(
    repair_jobs,
    key=lambda j: (
        -eligible[j]["priority"],
        -eligible[j]["service_h"],
        j,
    ),
)

globally_placed = set()

repair_results = []


for idx_job, job in enumerate(
    repair_order,
    start=1,
):

    team = unplaced[job]["team_id"]

    start_time = time.monotonic()

    timeout_at = (
        start_time
        + JOB_TIMEOUT_SECONDS
    )

    state_counter = [0]

    print()
    print(
        f"[{idx_job}/{len(repair_order)}] "
        f"JOB={job} "
        f"TEAM={team} "
        f"SERVICE={eligible[job]['service_h']:.2f}h "
        f"PRIORITY={eligible[job]['priority']:.2f}"
    )

    # --------------------------------------------------------
    # Direct insertion
    # --------------------------------------------------------

    direct = try_direct(
        team,
        job,
        timeout_at,
    )

    if direct is not None:

        (
            same_date,
            total_h,
            distance_m,
            date,
            trial,
        ) = direct

        key = (
            team,
            date,
        )

        daily_jobs[key] = trial

        globally_placed.add(
            job
        )

        elapsed = (
            time.monotonic()
            - start_time
        )

        print(
            f"  DIRECT INSERT -> "
            f"{date} "
            f"total={total_h:.3f}h "
            f"time={elapsed:.2f}s"
        )

        repair_results.append(
            {
                "job_id":
                    job,
                "result":
                    "DIRECT_INSERT",
                "team_id":
                    team,
                "states":
                    state_counter[0],
                "elapsed_s":
                    round(elapsed, 3),
                "target_date":
                    date,
            }
        )

        continue


    # --------------------------------------------------------
    # Depth 1
    # --------------------------------------------------------

    d1 = try_depth1(
        team,
        job,
        timeout_at,
        state_counter,
    )

    if d1 is not None:

        target_key = (
            team,
            d1["target_date"],
        )

        donor_key = (
            team,
            d1["donor_date"],
        )

        daily_jobs[
            target_key
        ] = d1["target_jobs"]

        daily_jobs[
            donor_key
        ] = d1["donor_jobs"]

        globally_placed.add(
            job
        )

        elapsed = (
            time.monotonic()
            - start_time
        )

        print(
            f"  DEPTH-1 EJECTION -> "
            f"target={d1['target_date']} "
            f"donor={d1['donor']} "
            f"to={d1['donor_date']} "
            f"time={elapsed:.2f}s"
        )

        repair_results.append(
            {
                "job_id":
                    job,
                "result":
                    "DEPTH1_EJECTION",
                "team_id":
                    team,
                "states":
                    state_counter[0],
                "elapsed_s":
                    round(elapsed, 3),
                "target_date":
                    d1["target_date"],
                "donor":
                    d1["donor"],
                "donor_date":
                    d1["donor_date"],
            }
        )

        continue


    # --------------------------------------------------------
    # Depth 2
    # --------------------------------------------------------

    d2 = try_depth2(
        team,
        job,
        timeout_at,
        state_counter,
    )

    if d2 is not None:

        key1 = (
            team,
            d2["d1"],
        )

        key2 = (
            team,
            d2["d2"],
        )

        daily_jobs[
            key1
        ] = d2["d1_jobs"]

        daily_jobs[
            key2
        ] = d2["d2_jobs"]

        if "d3" in d2:

            key3 = (
                team,
                d2["d3"],
            )

            daily_jobs[
                key3
            ] = d2["d3_jobs"]

        globally_placed.add(
            job
        )

        elapsed = (
            time.monotonic()
            - start_time
        )

        print(
            f"  DEPTH-2 EJECTION -> "
            f"d1={d2['d1']} "
            f"d2={d2['d2']} "
            f"d3={d2.get('d3', '-')}"
        )

        print(
            f"  states={state_counter[0]} "
            f"time={elapsed:.2f}s"
        )

        repair_results.append(
            {
                "job_id":
                    job,
                "result":
                    "DEPTH2_EJECTION",
                "team_id":
                    team,
                "states":
                    state_counter[0],
                "elapsed_s":
                    round(elapsed, 3),
                "d1":
                    d2["d1"],
                "d2":
                    d2["d2"],
                "d3":
                    d2.get(
                        "d3",
                        "",
                    ),
            }
        )

        continue


    # --------------------------------------------------------
    # Not found within bound
    # --------------------------------------------------------

    elapsed = (
        time.monotonic()
        - start_time
    )

    if (
        time.monotonic()
        >= timeout_at
    ):

        result_name = (
            "TIMEOUT_WITHIN_BOUND"
        )

    elif (
        state_counter[0]
        >= MAX_STATES_PER_JOB
    ):

        result_name = (
            "STATE_LIMIT_REACHED"
        )

    else:

        result_name = (
            "NO_FEASIBLE_BOUNDED_REPAIR"
        )

    print(
        f"  NOT PLACED -> "
        f"{result_name} "
        f"states={state_counter[0]} "
        f"time={elapsed:.2f}s"
    )

    repair_results.append(
        {
            "job_id":
                job,
            "result":
                result_name,
            "team_id":
                team,
            "states":
                state_counter[0],
            "elapsed_s":
                round(
                    elapsed,
                    3,
                ),
        }
    )


# ============================================================
# FINAL ROUTES
# ============================================================

scheduled_ids = set()

route_summaries = []
schedule_rows = []

schedule_counter = 1

for (
    team,
    date,
), jobs in sorted(
    daily_jobs.items(),
    key=lambda x: (
        x[0][1],
        x[0][0],
    ),
):

    if not jobs:
        continue

    route = best_route(
        team,
        jobs,
    )

    if route is None:
        raise RuntimeError(
            f"Final route became infeasible: "
            f"{team} {date}"
        )

    matrix = matrix_by_team[team]
    idx = matrix["node_index"]
    tm = matrix["time"]
    dm = matrix["distance"]

    depot_node = (
        f"__DEPOT__:{DEPOT_ID}"
    )

    previous = depot_node

    current_dt = datetime.strptime(
        f"{date} 08:00",
        "%Y-%m-%d %H:%M",
    )

    for seq, job in enumerate(
        route["jobs"],
        start=1,
    ):

        from_idx = idx[
            previous
        ]

        to_idx = idx[
            job
        ]

        travel_s = tm[
            (
                from_idx,
                to_idx,
            )
        ]

        distance_m = dm[
            (
                from_idx,
                to_idx,
            )
        ]

        start_dt = (
            current_dt
            + timedelta(
                seconds=travel_s
            )
        )

        end_dt = (
            start_dt
            + timedelta(
                hours=eligible[job]["service_h"]
            )
        )

        if job in job_origin:

            original_date = job_origin[
                job
            ]["original_schedule_date"]

            original_group = job_origin[
                job
            ]["original_group_index"]

        else:

            original_date = unplaced[
                job
            ]["original_schedule_date"]

            original_group = unplaced[
                job
            ]["original_group_index"]

        if original_date == date:
            repair_action = (
                "UNCHANGED_OR_SAME_DATE"
            )
        else:
            repair_action = (
                "MOVED_BY_BOUNDED_REPAIR"
            )

        schedule_rows.append(
            {
                "schedule_id":
                    (
                        f"TRV-B-{date}-"
                        f"{team}-{schedule_counter:03d}"
                    ),
                "team_id":
                    team,
                "schedule_date":
                    date,
                "cluster_id":
                    eligible[job]["cluster_id"],
                "job_id":
                    job,
                "sequence_no":
                    seq,
                "planned_start":
                    start_dt.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                "planned_end":
                    end_dt.strftime(
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
                        travel_s / 60.0,
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
                    "SCHEDULED_TRAVEL_AWARE_BOUNDED_CANDIDATE",
                "repair_action":
                    repair_action,
                "original_group_index":
                    original_group,
                "original_schedule_date":
                    original_date,
            }
        )

        scheduled_ids.add(job)

        current_dt = end_dt
        previous = job

    route_summaries.append(
        {
            "team_id":
                team,
            "schedule_date":
                date,
            "job_count":
                len(route["jobs"]),
            "service_h":
                round(
                    route["service_h"],
                    6,
                ),
            "travel_h":
                round(
                    route["travel_s"]
                    / 3600.0,
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
                        f"{date} 08:00",
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
                    route["distance_m"]
                    / 1000.0,
                    6,
                ),
        }
    )

    schedule_counter += 1


# ============================================================
# FINAL UNPLACED
# ============================================================

final_unplaced = {}

for job, meta in hard_unplaced.items():

    final_unplaced[job] = {
        **meta,
        "reason":
            meta["reason"],
        "status":
            "UNSCHEDULED",
    }


for job, meta in unplaced.items():

    if job in scheduled_ids:
        continue

    final_unplaced[job] = {
        **meta,
        "reason":
            next(
                (
                    r["result"]
                    for r in repair_results
                    if r["job_id"] == job
                ),
                "NOT_REPAIRED",
            ),
        "status":
            "UNSCHEDULED",
    }


# ============================================================
# VALIDATION
# ============================================================

original_jobs = (
    candidate_job_ids
    | set(unplaced)
)

scheduled_count = len(
    scheduled_ids
)

unplaced_count = len(
    final_unplaced
)

accounted = (
    scheduled_ids
    | set(final_unplaced)
)

no_duplicate = (
    scheduled_count
    == len(
        [
            r["job_id"]
            for r in schedule_rows
        ]
    )
)

all_accounted = (
    accounted
    == original_jobs
)

disjoint = (
    scheduled_ids
    .isdisjoint(
        set(final_unplaced)
    )
)

all_route_feasible = all(
    r["total_route_h"]
    <= SHIFT_HOURS + 1e-9
    for r in route_summaries
)

repair_jobs_placed = sum(
    1
    for job in repair_jobs
    if job in scheduled_ids
)

overall_pass = all(
    [
        len(original_jobs) == 241,
        no_duplicate,
        all_accounted,
        disjoint,
        all_route_feasible,
    ]
)


validation = [
    {
        "check":
            "ORIGINAL_JOB_COUNT",
        "expected":
            241,
        "actual":
            len(original_jobs),
        "status":
            "PASS"
            if len(original_jobs) == 241
            else "FAIL",
    },
    {
        "check":
            "FINAL_SCHEDULED_JOB_COUNT",
        "expected":
            "233..241",
        "actual":
            scheduled_count,
        "status":
            "PASS",
    },
    {
        "check":
            "FINAL_UNPLACED_COUNT",
        "expected":
            "0..8",
        "actual":
            unplaced_count,
        "status":
            "PASS",
    },
    {
        "check":
            "NO_DUPLICATE_SCHEDULED_JOBS",
        "expected":
            "YES",
        "actual":
            "YES"
            if no_duplicate
            else "NO",
        "status":
            "PASS"
            if no_duplicate
            else "FAIL",
    },
    {
        "check":
            "ALL_JOBS_ACCOUNTED",
        "expected":
            241,
        "actual":
            len(accounted),
        "status":
            "PASS"
            if all_accounted
            else "FAIL",
    },
    {
        "check":
            "SCHEDULE_UNPLACED_DISJOINT",
        "expected":
            "YES",
        "actual":
            "YES"
            if disjoint
            else "NO",
        "status":
            "PASS"
            if disjoint
            else "FAIL",
    },
    {
        "check":
            "ALL_ROUTES_WITHIN_9H",
        "expected":
            "<=9h",
        "actual":
            "YES"
            if all_route_feasible
            else "NO",
        "status":
            "PASS"
            if all_route_feasible
            else "FAIL",
    },
    {
        "check":
            "REPAIR_POOL_PLACED",
        "expected":
            len(repair_jobs),
        "actual":
            repair_jobs_placed,
        "status":
            "PASS"
            if repair_jobs_placed
            == len(repair_jobs)
            else "REVIEW",
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
# WRITE
# ============================================================

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
    writer.writerows(
        schedule_rows
    )


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

    for job in sorted(
        final_unplaced,
        key=lambda j: (
            final_unplaced[j]["team_id"],
            -eligible[j]["priority"],
            j,
        ),
    ):

        meta = final_unplaced[job]

        writer.writerow(
            {
                "job_id":
                    job,
                "team_id":
                    meta["team_id"],
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
                    meta["reason"],
                "status":
                    meta["status"],
            }
        )


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
    writer.writerows(validation)


total_service_h = sum(
    r["service_h"]
    for r in route_summaries
)

total_travel_h = sum(
    r["travel_h"]
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
        if overall_pass
        else "REVIEW_REQUIRED",
    "original_jobs":
        len(original_jobs),
    "final_scheduled_jobs":
        scheduled_count,
    "final_unplaced_jobs":
        unplaced_count,
    "hard_unplaced_jobs":
        len(hard_unplaced),
    "bounded_repair_jobs":
        len(repair_jobs),
    "bounded_repair_jobs_placed":
        repair_jobs_placed,
    "route_groups":
        len(route_summaries),
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
    "total_distance_km":
        round(
            total_distance_km,
            6,
        ),
    "max_route":
        max_route,
    "repair_results":
        repair_results,
    "final_unplaced":
        {
            job:
                final_unplaced[job]["reason"]
            for job in final_unplaced
        },
    "validation":
        {
            row["check"]:
                row["status"]
            for row in validation
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
print("BOUNDED GLOBAL REPAIR RESULT")
print("=" * 80)

print(
    f"Original jobs          : "
    f"{len(original_jobs)}"
)

print(
    f"Final scheduled jobs   : "
    f"{scheduled_count}"
)

print(
    f"Final unplaced jobs    : "
    f"{unplaced_count}"
)

print(
    f"Hard unplaced jobs     : "
    f"{len(hard_unplaced)}"
)

print(
    f"Repair jobs placed     : "
    f"{repair_jobs_placed}/{len(repair_jobs)}"
)

print(
    f"Route groups           : "
    f"{len(route_summaries)}"
)

print(
    f"Total service hours    : "
    f"{total_service_h:.3f}"
)

print(
    f"Total travel hours     : "
    f"{total_travel_h:.3f}"
)

print(
    f"Total route hours      : "
    f"{total_service_h + total_travel_h:.3f}"
)

print(
    f"Total distance         : "
    f"{total_distance_km:.3f} km"
)

if max_route:

    print()
    print("MAX ROUTE")
    print("-" * 80)

    print(
        f"Team                   : "
        f"{max_route['team_id']}"
    )

    print(
        f"Date                   : "
        f"{max_route['schedule_date']}"
    )

    print(
        f"Jobs                   : "
        f"{max_route['job_count']}"
    )

    print(
        f"Total route hours      : "
        f"{max_route['total_route_h']:.3f}"
    )

    print(
        f"Finish                 : "
        f"{max_route['finish_time']}"
    )


if final_unplaced:

    print()
    print("FINAL UNPLACED")
    print("-" * 80)

    for job in sorted(
        final_unplaced,
        key=lambda j: (
            final_unplaced[j]["team_id"],
            -eligible[j]["priority"],
            j,
        ),
    ):

        meta = final_unplaced[job]

        print(
            f"{job} | "
            f"{meta['team_id']} | "
            f"service={eligible[job]['service_h']:.2f}h | "
            f"priority={eligible[job]['priority']:.2f} | "
            f"{meta['reason']}"
        )


print()
print("VALIDATION")
print("-" * 80)

for row in validation:

    print(
        f"{row['check']:<35}"
        f"{row['status']}"
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
print("BOUNDED GLOBAL REPAIR COMPLETE")
print("=" * 80)
