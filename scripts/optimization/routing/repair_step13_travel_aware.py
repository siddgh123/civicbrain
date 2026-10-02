import csv
import json
import itertools
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(".")

ELIGIBLE_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
ROUTE_FILE = ROOT / "data/optimization/routing/route_results.csv"
AUDIT_FILE = ROOT / "data/optimization/routing/final_schedule_route_audit.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"
SCHEDULE_SUMMARY_FILE = ROOT / "data/optimization/scheduling/scheduling_summary.json"

OUT_SCHEDULE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_candidate.csv"
OUT_UNPLACED = ROOT / "data/optimization/scheduling/travel_aware_unplaced_jobs.csv"
OUT_VALIDATION = ROOT / "data/optimization/scheduling/travel_aware_repair_validation.csv"
OUT_SUMMARY = ROOT / "data/optimization/scheduling/travel_aware_repair_summary.json"

SHIFT_HOURS = 9.0
SHIFT_START_HOUR = 8
OSRM_URL = "https://router.project-osrm.org/table/v1/driving"

SOURCE_BLOCK = 20
DEST_BLOCK = 50
REQUEST_DELAY = 0.35

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def read_csv(path):
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


def pick_col(row, names):
    for name in names:
        if name in row and str(row[name]).strip() != "":
            return name
    return None


def as_float(value, field):
    try:
        return float(value)
    except Exception:
        raise RuntimeError(f"Invalid numeric value for {field}: {value!r}")


def norm_date(value):
    return str(value).strip().split("T")[0]


def find_key(obj, candidates):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in candidates:
                return v
        for v in obj.values():
            found = find_key(v, candidates)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, candidates)
            if found is not None:
                return found
    return None


# ------------------------------------------------------------
# Load files
# ------------------------------------------------------------

for p in [
    ELIGIBLE_FILE,
    ROUTE_FILE,
    AUDIT_FILE,
    DEPOT_FILE,
    SCHEDULE_SUMMARY_FILE,
]:
    if not p.exists():
        raise RuntimeError(f"Required file not found: {p}")


eligible_rows = read_csv(ELIGIBLE_FILE)
route_rows = read_csv(ROUTE_FILE)
audit_rows = read_csv(AUDIT_FILE)
depot_rows = read_csv(DEPOT_FILE)

with open(SCHEDULE_SUMMARY_FILE, encoding="utf-8-sig") as f:
    schedule_summary = json.load(f)


require_columns(
    eligible_rows,
    ELIGIBLE_FILE,
    [
        "job_id",
        "latitude", "longitude", "service_duration_hours",
        "work_type",
        "priority_score",
    ],
)

require_columns(
    route_rows,
    ROUTE_FILE,
    [
        "group_index",
        "team_id",
        "schedule_date",
        "node_type",
        "job_id",
    ],
)

require_columns(
    audit_rows,
    AUDIT_FILE,
    [
        "group_index",
        "team_id",
        "schedule_date",
        "status",
    ],
)

require_columns(
    depot_rows,
    DEPOT_FILE,
    [],
)


# ------------------------------------------------------------
# Build eligible-job lookup
# ------------------------------------------------------------

eligible = {}

for r in eligible_rows:
    job_id = str(r["job_id"]).strip()

    if job_id in eligible:
        raise RuntimeError(f"Duplicate eligible job_id: {job_id}")

    lat_col = pick_col(r, ["lat", "latitude"])
    lon_col = pick_col(r, ["long", "lon", "longitude"])

    if not lat_col or not lon_col:
        raise RuntimeError(
            f"Latitude/longitude columns not found for job {job_id}"
        )

    cost_col = pick_col(
        r,
        [
            "estimated_cost",
            "estimated_cost_inr",
            "cost",
            "estimated_cost_h",
        ],
    )

    cluster_col = pick_col(
        r,
        [
            "cluster_id",
        ],
    )

    eligible[job_id] = {
        "lat": as_float(r[lat_col], f"{job_id}.lat"),
        "lon": as_float(r[lon_col], f"{job_id}.lon"),
        "service_h": as_float(
            r["service_duration_hours"],
            f"{job_id}.service_duration_hours",
        ),
        "work_type": str(r["work_type"]).strip(),
        "priority": as_float(
            r["priority_score"],
            f"{job_id}.priority_score",
        ),
        "cost": (
            str(r[cost_col]).strip()
            if cost_col
            else ""
        ),
        "cluster_id": (
            str(r[cluster_col]).strip()
            if cluster_col
            else ""
        ),
    }


# ------------------------------------------------------------
# Identify 45 violating groups
# ------------------------------------------------------------

violating_groups = set()

for r in audit_rows:
    status = str(r["status"]).strip().upper()

    if status == "TRAVEL_TIME_VIOLATION":
        violating_groups.add(
            str(r["group_index"]).strip()
        )


if not violating_groups:
    raise RuntimeError(
        "No TRAVEL_TIME_VIOLATION groups found in audit."
    )


# ------------------------------------------------------------
# Build current group -> jobs
# ------------------------------------------------------------

groups = defaultdict(
    lambda: {
        "team_id": None,
        "schedule_date": None,
        "jobs": [],
    }
)

job_origin = {}
current_scheduled_jobs = set()

for r in route_rows:

    if str(r["node_type"]).strip().upper() != "JOB":
        continue

    group_id = str(r["group_index"]).strip()
    job_id = str(r["job_id"]).strip()
    team_id = str(r["team_id"]).strip()
    schedule_date = norm_date(r["schedule_date"])

    if not job_id:
        raise RuntimeError(
            f"JOB row without job_id in group {group_id}"
        )

    if job_id not in eligible:
        raise RuntimeError(
            f"Job {job_id} exists in route_results "
            f"but not in eligible_jobs.csv"
        )

    if job_id in current_scheduled_jobs:
        raise RuntimeError(
            f"Duplicate scheduled job in route_results: {job_id}"
        )

    current_scheduled_jobs.add(job_id)

    groups[group_id]["team_id"] = team_id
    groups[group_id]["schedule_date"] = schedule_date
    groups[group_id]["jobs"].append(job_id)

    job_origin[job_id] = {
        "team_id": team_id,
        "schedule_date": schedule_date,
        "group_index": group_id,
    }


# ------------------------------------------------------------
# Split fixed groups and repair pool
# ------------------------------------------------------------

fixed_daily_jobs = defaultdict(list)
repair_jobs = set()

for group_id, info in groups.items():

    if group_id in violating_groups:
        for job_id in info["jobs"]:
            repair_jobs.add(job_id)
    else:
        key = (
            info["team_id"],
            info["schedule_date"],
        )

        fixed_daily_jobs[key].extend(info["jobs"])


fixed_job_count = sum(
    len(v)
    for v in fixed_daily_jobs.values()
)

repair_job_count = len(repair_jobs)


if fixed_job_count + repair_job_count != len(
    current_scheduled_jobs
):
    raise RuntimeError(
        "Fixed + repair job accounting mismatch."
    )


# ------------------------------------------------------------
# Depot
# ------------------------------------------------------------

depot = depot_rows[0]

depot_lat_col = pick_col(
    depot,
    ["lat", "latitude"]
)

depot_lon_col = pick_col(
    depot,
    ["long", "lon", "longitude"]
)

if not depot_lat_col or not depot_lon_col:
    raise RuntimeError(
        "Depot latitude/longitude columns not found."
    )

DEPOT_ID = str(
    depot.get("depot_id", "D001")
).strip()

DEPOT_LAT = as_float(
    depot[depot_lat_col],
    "depot.latitude",
)

DEPOT_LON = as_float(
    depot[depot_lon_col],
    "depot.longitude",
)


# ------------------------------------------------------------
# Scheduling horizon
# ------------------------------------------------------------

horizon_start = find_key(
    schedule_summary,
    {
        "horizon_start",
        "start_date",
        "schedule_start",
    },
)

horizon_end = find_key(
    schedule_summary,
    {
        "horizon_end",
        "end_date",
        "schedule_end",
    },
)

horizon_days = find_key(
    schedule_summary,
    {
        "horizon_days",
        "planning_horizon_days",
    },
)

current_dates = [
    info["schedule_date"]
    for info in groups.values()
    if info["schedule_date"]
]

if horizon_start:
    start_date = datetime.strptime(
        norm_date(horizon_start),
        "%Y-%m-%d",
    ).date()
else:
    start_date = datetime.strptime(
        min(current_dates),
        "%Y-%m-%d",
    ).date()


if horizon_end:
    end_date = datetime.strptime(
        norm_date(horizon_end),
        "%Y-%m-%d",
    ).date()
elif horizon_days:
    end_date = (
        start_date
        + timedelta(days=int(horizon_days) - 1)
    )
else:
    end_date = start_date + timedelta(days=29)


horizon_dates = []

d = start_date
while d <= end_date:
    horizon_dates.append(d.isoformat())
    d += timedelta(days=1)


# ------------------------------------------------------------
# Team -> all currently scheduled jobs
# ------------------------------------------------------------

team_jobs = defaultdict(set)

for job_id, origin in job_origin.items():
    team_jobs[origin["team_id"]].add(job_id)


# ------------------------------------------------------------
# OSRM full team matrices
# ------------------------------------------------------------

print("=" * 80)
print("CIVICBRAIN STEP 13 — TRAVEL-AWARE REPAIR PASS")
print("=" * 80)

print(f"Current scheduled jobs      : {len(current_scheduled_jobs)}")
print(f"Fixed jobs                  : {fixed_job_count}")
print(f"Repair pool jobs            : {repair_job_count}")
print(f"Violating groups            : {len(violating_groups)}")
print(
    f"Horizon                     : "
    f"{horizon_dates[0]} -> {horizon_dates[-1]}"
)
print()


matrix_by_team = {}


def osrm_table_request(
    team_id,
    nodes,
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

    query = (
        f"?annotations=duration,distance"
        f"&sources={source_string}"
        f"&destinations={destination_string}"
    )

    url = (
        f"{OSRM_URL}/"
        f"{urllib.parse.quote(coord_string, safe=',;')}"
        f"{query}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "CivicBrain-Step13-Research-Prototype/1.0"
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=60,
        ) as response:

            payload = json.loads(
                response.read().decode("utf-8")
            )

    except Exception as exc:
        raise RuntimeError(
            f"OSRM request failed "
            f"(team={team_id}): {exc}"
        )

    if payload.get("code") != "Ok":
        raise RuntimeError(
            f"OSRM returned non-Ok "
            f"(team={team_id}): "
            f"{payload.get('code')} "
            f"{payload.get('message', '')}"
        )

    if "durations" not in payload:
        raise RuntimeError(
            f"OSRM durations missing for team {team_id}"
        )

    if "distances" not in payload:
        raise RuntimeError(
            f"OSRM distances missing for team {team_id}"
        )

    return payload


for team_id in sorted(team_jobs):

    jobs = sorted(team_jobs[team_id])

    node_ids = [f"__DEPOT__:{DEPOT_ID}"] + jobs

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

    time_matrix = {}
    distance_matrix = {}

    print(
        f"Building OSRM matrix for {team_id} "
        f"with {n - 1} jobs..."
    )

    total_requests = 0

    for s0 in range(0, n, SOURCE_BLOCK):

        sources = list(
            range(
                s0,
                min(
                    s0 + SOURCE_BLOCK,
                    n,
                ),
            )
        )

        for d0 in range(0, n, DEST_BLOCK):

            destinations = list(
                range(
                    d0,
                    min(
                        d0 + DEST_BLOCK,
                        n,
                    ),
                )
            )

            payload = osrm_table_request(
                team_id,
                node_ids,
                coords,
                sources,
                destinations,
            )

            durations = payload["durations"]
            distances = payload["distances"]

            if len(durations) != len(sources):
                raise RuntimeError(
                    f"OSRM duration row mismatch "
                    f"for {team_id}"
                )

            if len(distances) != len(sources):
                raise RuntimeError(
                    f"OSRM distance row mismatch "
                    f"for {team_id}"
                )

            for si, source_index in enumerate(
                sources
            ):

                if len(
                    durations[si]
                ) != len(destinations):

                    raise RuntimeError(
                        f"OSRM duration column mismatch "
                        f"for {team_id}"
                    )

                if len(
                    distances[si]
                ) != len(destinations):

                    raise RuntimeError(
                        f"OSRM distance column mismatch "
                        f"for {team_id}"
                    )

                for di, destination_index in enumerate(
                    destinations
                ):

                    duration_value = durations[si][di]
                    distance_value = distances[si][di]

                    if (
                        duration_value is None
                        or distance_value is None
                    ):
                        raise RuntimeError(
                            f"No OSRM route for "
                            f"{team_id}: "
                            f"{node_ids[source_index]}"
                            f" -> "
                            f"{node_ids[destination_index]}"
                        )

                    time_matrix[
                        (
                            source_index,
                            destination_index,
                        )
                    ] = float(duration_value)

                    distance_matrix[
                        (
                            source_index,
                            destination_index,
                        )
                    ] = float(distance_value)

            total_requests += 1
            time.sleep(REQUEST_DELAY)

    matrix_by_team[team_id] = {
        "node_ids": node_ids,
        "node_index": {
            node_id: i
            for i, node_id in enumerate(
                node_ids
            )
        },
        "time": time_matrix,
        "distance": distance_matrix,
    }

    print(
        f"  OSRM requests completed : "
        f"{total_requests}"
    )
    print(
        f"  Matrix entries          : "
        f"{len(time_matrix)}"
    )
    print()


# ------------------------------------------------------------
# Exact feasible route for a daily job set
#
# Primary objective: minimum road distance
# Constraint: total travel + service <= 9h
#
# Daily routes are small in this prototype.
# ------------------------------------------------------------

route_cache = {}


def best_feasible_route(team_id, jobs):

    jobs = tuple(
        sorted(
            set(jobs)
        )
    )

    cache_key = (
        team_id,
        jobs,
    )

    if cache_key in route_cache:
        return route_cache[cache_key]

    if not jobs:
        result = {
            "jobs": [],
            "travel_s": 0.0,
            "distance_m": 0.0,
            "total_h": 0.0,
        }

        route_cache[cache_key] = result
        return result

    if len(jobs) > 8:
        raise RuntimeError(
            f"Daily route has {len(jobs)} jobs "
            f"for {team_id}; exact permutation "
            f"repair guard reached."
        )

    matrix = matrix_by_team[team_id]
    idx = matrix["node_index"]
    tm = matrix["time"]
    dm = matrix["distance"]

    best = None

    for perm in itertools.permutations(jobs):

        full = [
            idx[f"__DEPOT__:{DEPOT_ID}"]
        ]

        full.extend(
            idx[job]
            for job in perm
        )

        full.append(
            idx[f"__DEPOT__:{DEPOT_ID}"]
        )

        travel_s = 0.0
        distance_m = 0.0

        for i in range(
            len(full) - 1
        ):

            a = full[i]
            b = full[i + 1]

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
        else:
            if (
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

    route_cache[cache_key] = best

    return best


# ------------------------------------------------------------
# Initial fixed routes
# ------------------------------------------------------------

daily_jobs = defaultdict(list)

for key, jobs in fixed_daily_jobs.items():
    daily_jobs[key] = list(
        dict.fromkeys(jobs)
    )


# Verify fixed groups still fit
for key, jobs in daily_jobs.items():

    team_id, schedule_date = key

    route = best_feasible_route(
        team_id,
        jobs,
    )

    if route is None:
        raise RuntimeError(
            f"Previously feasible group became "
            f"infeasible unexpectedly: "
            f"{team_id} {schedule_date}"
        )


# ------------------------------------------------------------
# Repair order
#
# First hard-to-place jobs:
#   1. longer service duration
#   2. higher priority
#   3. original group
# ------------------------------------------------------------

repair_order = sorted(
    repair_jobs,
    key=lambda job: (
        -eligible[job]["service_h"],
        -eligible[job]["priority"],
        job_origin[job]["group_index"],
        job,
    ),
)


# ------------------------------------------------------------
# Greedy repair
#
# Keep same team.
# Prefer same date.
# Then minimize added road distance.
# Then minimize total route hours.
# ------------------------------------------------------------

placed_repair_jobs = set()
unplaced_jobs = []


for pos, job_id in enumerate(
    repair_order,
    start=1,
):

    origin = job_origin[job_id]

    origin_team = origin["team_id"]
    origin_date = origin["schedule_date"]

    best_slot = None

    for schedule_date in horizon_dates:

        key = (
            origin_team,
            schedule_date,
        )

        existing_jobs = daily_jobs[key]

        if job_id in existing_jobs:
            continue

        trial_jobs = (
            existing_jobs
            + [job_id]
        )

        route = best_feasible_route(
            origin_team,
            trial_jobs,
        )

        if route is None:
            continue

        old_route = best_feasible_route(
            origin_team,
            existing_jobs,
        )

        old_distance = (
            old_route["distance_m"]
            if old_route
            else 0.0
        )

        added_distance = (
            route["distance_m"]
            - old_distance
        )

        date_change = (
            0
            if schedule_date == origin_date
            else 1
        )

        score = (
            date_change,
            added_distance,
            route["total_h"],
            schedule_date,
        )

        if (
            best_slot is None
            or score < best_slot["score"]
        ):

            best_slot = {
                "date": schedule_date,
                "score": score,
                "route": route,
            }

    if best_slot is None:

        unplaced_jobs.append(
            {
                "job_id": job_id,
                "team_id": origin_team,
                "original_schedule_date":
                    origin_date,
                "original_group_index":
                    origin["group_index"],
                "priority_score":
                    eligible[job_id]["priority"],
                "service_duration_h":
                    eligible[job_id]["service_h"],
                "reason":
                    "TRAVEL_AWARE_REPAIR_NO_FEASIBLE_SLOT",
                "status":
                    "UNPLACED",
            }
        )

    else:

        target_key = (
            origin_team,
            best_slot["date"],
        )

        daily_jobs[target_key].append(
            job_id
        )

        placed_repair_jobs.add(job_id)

    if pos % 10 == 0 or pos == len(
        repair_order
    ):
        print(
            f"Repair progress: "
            f"{pos}/{len(repair_order)}"
            f" | placed={len(placed_repair_jobs)}"
            f" | unplaced={len(unplaced_jobs)}"
        )


# ------------------------------------------------------------
# Build final candidate routes
# ------------------------------------------------------------

schedule_rows = []

route_summaries = []

schedule_counter = 1

for (team_id, schedule_date) in sorted(
    daily_jobs.keys(),
    key=lambda x: (
        x[0],
        x[1],
    ),
):

    jobs = daily_jobs[
        (team_id, schedule_date)
    ]

    if not jobs:
        continue

    route = best_feasible_route(
        team_id,
        jobs,
    )

    if route is None:
        raise RuntimeError(
            f"Final daily route infeasible: "
            f"{team_id} {schedule_date}"
        )

    planned_dt = datetime.strptime(
        f"{schedule_date} 08:00",
        "%Y-%m-%d %H:%M",
    )

    previous = f"__DEPOT__:{DEPOT_ID}"

    matrix = matrix_by_team[team_id]
    idx = matrix["node_index"]
    tm = matrix["time"]
    dm = matrix["distance"]

    total_service_h = 0.0

    for sequence_no, job_id in enumerate(
        route["jobs"],
        start=1,
    ):

        from_node = idx[
            previous
        ]

        to_node = idx[
            job_id
        ]

        incoming_travel_s = tm[
            (from_node, to_node)
        ]

        incoming_distance_m = dm[
            (from_node, to_node)
        ]

        start_dt = (
            planned_dt
            + timedelta(
                seconds=incoming_travel_s
            )
        )

        end_dt = (
            start_dt
            + timedelta(
                hours=eligible[job_id]["service_h"]
            )
        )

        origin = job_origin[job_id]

        if (
            origin["schedule_date"]
            == schedule_date
        ):
            repair_action = (
                "REPAIRED_SAME_DATE"
            )
        else:
            repair_action = (
                "MOVED_TO_NEW_DATE"
            )

        schedule_id = (
            f"TRV-{schedule_date}-"
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
                    start_dt.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                "planned_end":
                    end_dt.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                "service_duration_h":
                    round(
                        eligible[job_id]["service_h"],
                        3,
                    ),
                "travel_distance_m":
                    round(
                        incoming_distance_m,
                        1,
                    ),
                "travel_time_min":
                    round(
                        incoming_travel_s / 60.0,
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
                    "SCHEDULED_TRAVEL_AWARE_CANDIDATE",
                "repair_action":
                    repair_action,
                "original_group_index":
                    origin["group_index"],
                "original_schedule_date":
                    origin["schedule_date"],
            }
        )

        planned_dt = end_dt
        previous = job_id
        total_service_h += (
            eligible[job_id]["service_h"]
        )

    route_summaries.append(
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


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

scheduled_job_ids = [
    r["job_id"]
    for r in schedule_rows
]

unique_scheduled_job_ids = set(
    scheduled_job_ids
)

origin_team_by_job = {
    job: info["team_id"]
    for job, info in job_origin.items()
}

team_preserved = all(
    row["team_id"]
    == origin_team_by_job[row["job_id"]]
    for row in schedule_rows
)

fixed_preserved = True

for key, fixed_jobs in fixed_daily_jobs.items():

    team_id, schedule_date = key

    candidate_jobs = set(
        daily_jobs[key]
    )

    for job_id in fixed_jobs:
        if job_id not in candidate_jobs:
            fixed_preserved = False
            break

    if not fixed_preserved:
        break


horizon_valid = all(
    start_date.isoformat()
    <= row["schedule_date"]
    <= end_date.isoformat()
    for row in schedule_rows
)

all_shift_feasible = all(
    r["total_route_h"]
    <= SHIFT_HOURS + 1e-9
    for r in route_summaries
)

scheduled_count_preserved = (
    len(unique_scheduled_job_ids)
    == len(current_scheduled_jobs)
)

no_duplicate_jobs = (
    len(scheduled_job_ids)
    == len(unique_scheduled_job_ids)
)

repair_pool_placed = (
    len(placed_repair_jobs)
    == repair_job_count
)

overall_pass = all(
    [
        scheduled_count_preserved,
        no_duplicate_jobs,
        team_preserved,
        fixed_preserved,
        horizon_valid,
        all_shift_feasible,
        repair_pool_placed,
    ]
)


validation_rows = [
    {
        "check": "CURRENT_SCHEDULED_JOB_COUNT",
        "expected": len(current_scheduled_jobs),
        "actual": len(unique_scheduled_job_ids),
        "status": (
            "PASS"
            if scheduled_count_preserved
            else "FAIL"
        ),
    },
    {
        "check": "NO_DUPLICATE_SCHEDULED_JOBS",
        "expected": len(unique_scheduled_job_ids),
        "actual": len(scheduled_job_ids),
        "status": (
            "PASS"
            if no_duplicate_jobs
            else "FAIL"
        ),
    },
    {
        "check": "TEAM_ASSIGNMENT_PRESERVED",
        "expected": "CURRENT_TEAM",
        "actual": "PRESERVED",
        "status": (
            "PASS"
            if team_preserved
            else "FAIL"
        ),
    },
    {
        "check": "FIXED_JOBS_PRESERVED",
        "expected": "YES",
        "actual": (
            "YES"
            if fixed_preserved
            else "NO"
        ),
        "status": (
            "PASS"
            if fixed_preserved
            else "FAIL"
        ),
    },
    {
        "check": "HORIZON_VALID",
        "expected":
            f"{horizon_dates[0]}..{horizon_dates[-1]}",
        "actual": "ALL_VALID",
        "status": (
            "PASS"
            if horizon_valid
            else "FAIL"
        ),
    },
    {
        "check": "ALL_DAILY_ROUTES_WITHIN_9H",
        "expected": "<=9.0h",
        "actual": (
            "ALL_VALID"
            if all_shift_feasible
            else "VIOLATIONS"
        ),
        "status": (
            "PASS"
            if all_shift_feasible
            else "FAIL"
        ),
    },
    {
        "check": "REPAIR_POOL_PLACED",
        "expected": repair_job_count,
        "actual": len(placed_repair_jobs),
        "status": (
            "PASS"
            if repair_pool_placed
            else "FAIL"
        ),
    },
    {
        "check": "OVERALL",
        "expected": "PASS",
        "actual": (
            "PASS"
            if overall_pass
            else "REVIEW_REQUIRED"
        ),
        "status": (
            "PASS"
            if overall_pass
            else "FAIL"
        ),
    },
]


# ------------------------------------------------------------
# Write candidate schedule
# ------------------------------------------------------------

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

    fieldnames = [
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
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(schedule_rows)


# ------------------------------------------------------------
# Write unplaced jobs
# ------------------------------------------------------------

with open(
    OUT_UNPLACED,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fieldnames = [
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
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(unplaced_jobs)


# ------------------------------------------------------------
# Write validation
# ------------------------------------------------------------

with open(
    OUT_VALIDATION,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fieldnames = [
        "check",
        "expected",
        "actual",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(validation_rows)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

max_route = max(
    route_summaries,
    key=lambda r: r["total_route_h"],
    default=None,
)

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

summary = {
    "status": (
        "PASS"
        if overall_pass
        else "REVIEW_REQUIRED"
    ),
    "current_scheduled_jobs":
        len(current_scheduled_jobs),
    "fixed_jobs":
        fixed_job_count,
    "repair_pool_jobs":
        repair_job_count,
    "placed_repair_jobs":
        len(placed_repair_jobs),
    "unplaced_repair_jobs":
        len(unplaced_jobs),
    "candidate_scheduled_jobs":
        len(unique_scheduled_job_ids),
    "candidate_route_groups":
        len(route_summaries),
    "horizon_start":
        horizon_dates[0],
    "horizon_end":
        horizon_dates[-1],
    "shift_hours":
        SHIFT_HOURS,
    "total_service_hours":
        round(total_service_h, 6),
    "total_travel_hours":
        round(total_travel_h, 6),
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
    "validation":
        {
            row["check"]: row["status"]
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


# ------------------------------------------------------------
# Console result
# ------------------------------------------------------------

print()
print("=" * 80)
print("TRAVEL-AWARE REPAIR RESULT")
print("=" * 80)

print(
    f"Current scheduled jobs      : "
    f"{len(current_scheduled_jobs)}"
)

print(
    f"Repair pool jobs            : "
    f"{repair_job_count}"
)

print(
    f"Placed repair jobs          : "
    f"{len(placed_repair_jobs)}"
)

print(
    f"Unplaced repair jobs        : "
    f"{len(unplaced_jobs)}"
)

print(
    f"Candidate scheduled jobs    : "
    f"{len(unique_scheduled_job_ids)}"
)

print(
    f"Candidate route groups      : "
    f"{len(route_summaries)}"
)

print(
    f"Total service hours         : "
    f"{total_service_h:.3f}"
)

print(
    f"Total travel hours          : "
    f"{total_travel_h:.3f}"
)

print(
    f"Total route hours           : "
    f"{total_service_h + total_travel_h:.3f}"
)

print(
    f"Total road distance         : "
    f"{total_distance_km:.3f} km"
)

if max_route:
    print()
    print("MAX ROUTE")
    print("-" * 80)
    print(
        f"Team                       : "
        f"{max_route['team_id']}"
    )
    print(
        f"Date                       : "
        f"{max_route['schedule_date']}"
    )
    print(
        f"Jobs                       : "
        f"{max_route['job_count']}"
    )
    print(
        f"Service hours              : "
        f"{max_route['service_h']:.3f}"
    )
    print(
        f"Travel hours               : "
        f"{max_route['travel_h']:.3f}"
    )
    print(
        f"Total route hours          : "
        f"{max_route['total_route_h']:.3f}"
    )
    print(
        f"Finish time                : "
        f"{max_route['finish_time']}"
    )

print()
print("VALIDATION")
print("-" * 80)

for row in validation_rows:
    print(
        f"{row['check']:<35} "
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
print(f"Schedule   : {OUT_SCHEDULE}")
print(f"Unplaced   : {OUT_UNPLACED}")
print(f"Validation : {OUT_VALIDATION}")
print(f"Summary    : {OUT_SUMMARY}")

print()
print("=" * 80)
print("TRAVEL-AWARE REPAIR PASS COMPLETE")
print("=" * 80)


