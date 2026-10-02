import csv
import json
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(".")

ELIGIBLE_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
BOUNDED_FILE = ROOT / "data/optimization/scheduling/schedule_results_travel_aware_bounded_candidate.csv"
T001_FILE = ROOT / "data/optimization/scheduling/schedule_results_t001_vrp_candidate.csv"
OLD_UNSCHEDULED_FILE = ROOT / "data/optimization/scheduling/unscheduled_jobs.csv"
T001_UNPLACED_FILE = ROOT / "data/optimization/scheduling/t001_vrp_unplaced_jobs.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"

OUT_SCHEDULE = ROOT / "data/optimization/scheduling/final_step13_schedule_candidate.csv"
OUT_UNSCHEDULED = ROOT / "data/optimization/scheduling/final_step13_unscheduled_jobs.csv"
OUT_ROUTE_AUDIT = ROOT / "data/optimization/routing/final_step13_route_audit.csv"
OUT_VALIDATION = ROOT / "data/optimization/scheduling/final_step13_validation.csv"
OUT_SUMMARY = ROOT / "data/optimization/scheduling/final_step13_summary.json"

SHIFT_HOURS = 9.0
SHIFT_START = "08:00"

OSRM_URL = "https://router.project-osrm.org/table/v1/driving"
REQUEST_DELAY = 0.30


# ============================================================
# HELPERS
# ============================================================

def read_csv(path):
    if not path.exists():
        raise RuntimeError(f"Missing file: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fnum(value, name):
    try:
        return float(value)
    except Exception:
        raise RuntimeError(f"Invalid number for {name}: {value!r}")


def date_only(value):
    return str(value).strip().split("T")[0]


# ============================================================
# LOAD
# ============================================================

eligible_rows = read_csv(ELIGIBLE_FILE)
bounded_rows = read_csv(BOUNDED_FILE)
t001_rows = read_csv(T001_FILE)
old_unscheduled_rows = read_csv(OLD_UNSCHEDULED_FILE)
t001_unplaced_rows = read_csv(T001_UNPLACED_FILE)
depot_rows = read_csv(DEPOT_FILE)


# ============================================================
# ELIGIBLE LOOKUP
# ============================================================

eligible = {}

for r in eligible_rows:

    job = str(r["job_id"]).strip()

    if job in eligible:
        raise RuntimeError(
            f"Duplicate eligible job: {job}"
        )

    eligible[job] = {
        "complaint_id":
            str(
                r.get(
                    "complaint_id",
                    job,
                )
            ).strip(),
        "lat":
            fnum(
                r["latitude"],
                f"{job}.latitude",
            ),
        "lon":
            fnum(
                r["longitude"],
                f"{job}.longitude",
            ),
        "service_h":
            fnum(
                r["service_duration_hours"],
                f"{job}.service_duration_hours",
            ),
        "work_type":
            str(
                r.get(
                    "work_type",
                    "",
                )
            ).strip(),
        "priority":
            fnum(
                r["priority_score"],
                f"{job}.priority_score",
            ),
        "cluster_id":
            str(
                r.get(
                    "cluster_id",
                    "",
                )
            ).strip(),
        "cost":
            str(
                r.get(
                    "estimated_cost",
                    "",
                )
            ).strip(),
    }


# ============================================================
# MERGE SCHEDULE
#
# T001 is replaced by the full T001 VRP result.
# T002/T003/T004 are retained from bounded candidate.
# ============================================================

final_rows = []

for r in bounded_rows:

    team = str(
        r["team_id"]
    ).strip()

    if team != "T001":
        final_rows.append(
            dict(r)
        )

final_rows.extend(dict(r) for r in t001_rows if str(r["team_id"]).strip() == "T001")


# ============================================================
# BASIC SCHEDULE VALIDATION
# ============================================================

scheduled_ids = [
    str(
        r["job_id"]
    ).strip()
    for r in final_rows
]

scheduled_set = set(
    scheduled_ids
)

if len(scheduled_ids) != len(scheduled_set):
    duplicates = sorted(
        {
            x
            for x in scheduled_ids
            if scheduled_ids.count(x) > 1
        }
    )

    raise RuntimeError(
        f"Duplicate scheduled jobs after merge: "
        f"{duplicates}"
    )

missing_from_eligible = [
    job
    for job in scheduled_set
    if job not in eligible
]

if missing_from_eligible:
    raise RuntimeError(
        f"Scheduled jobs missing in eligible_jobs.csv: "
        f"{missing_from_eligible}"
    )


if len(scheduled_set) != 238:
    raise RuntimeError(
        "Expected 238 final scheduled jobs after "
        f"T001 replacement, found {len(scheduled_set)}"
    )


# ============================================================
# FINAL NEWLY UNSCHEDULED
# ============================================================

new_unplaced = []

for job in [
    "11",
    "143",
    "179",
]:

    if job in scheduled_set:
        raise RuntimeError(
            f"Job {job} unexpectedly scheduled."
        )


for r in t001_unplaced_rows:

    job = str(
        r["job_id"]
    ).strip()

    if job not in {
        "11",
        "143",
        "179",
    }:
        raise RuntimeError(
            "T001 VRP unplaced file contains "
            f"unexpected job: {job}"
        )

    row = {
        "job_id":
            job,
        "complaint_id":
            eligible[job]["complaint_id"],
        "cluster_id":
            eligible[job]["cluster_id"],
        "work_type":
            eligible[job]["work_type"],
        "priority_score":
            round(
                eligible[job]["priority"],
                6,
            ),
        "reason":
            (
                "SERVICE_DURATION_PLUS_DEPOT_TRAVEL_EXCEEDS_SHIFT"
            ),
        "details":
            (
                "Single-job OSRM depot round trip plus "
                "service duration exceeds the 08:00-17:00 "
                "prototype shift."
            ),
        "status":
            "UNSCHEDULED",
    }

    new_unplaced.append(row)


new_unplaced_ids = {
    r["job_id"]
    for r in new_unplaced
}

if new_unplaced_ids != {
    "11",
    "143",
    "179",
}:
    raise RuntimeError(
        "Final new-unplaced set mismatch."
    )


# ============================================================
# COMBINE OLD 200 UNSCHEDULED + NEW 3
# ============================================================

final_unscheduled = []

old_unscheduled_ids = set()

for r in old_unscheduled_rows:

    job = str(
        r["job_id"]
    ).strip()

    if job in old_unscheduled_ids:
        raise RuntimeError(
            f"Duplicate original unscheduled job: {job}"
        )

    if job in scheduled_set:
        raise RuntimeError(
            f"Original unscheduled job now appears "
            f"in final schedule: {job}"
        )

    old_unscheduled_ids.add(job)

    final_unscheduled.append(
        {
            "job_id":
                job,
            "complaint_id":
                str(
                    r.get(
                        "complaint_id",
                        eligible.get(
                            job,
                            {}
                        ).get(
                            "complaint_id",
                            "",
                        ),
                    )
                ).strip(),
            "cluster_id":
                str(
                    r.get(
                        "cluster_id",
                        eligible.get(
                            job,
                            {}
                        ).get(
                            "cluster_id",
                            "",
                        ),
                    )
                ).strip(),
            "work_type":
                str(
                    r.get(
                        "work_type",
                        eligible.get(
                            job,
                            {}
                        ).get(
                            "work_type",
                            "",
                        ),
                    )
                ).strip(),
            "priority_score":
                str(
                    r.get(
                        "priority_score",
                        eligible.get(
                            job,
                            {}
                        ).get(
                            "priority",
                            "",
                        ),
                    )
                ).strip(),
            "reason":
                str(
                    r.get(
                        "reason",
                        "UNSCHEDULED",
                    )
                ).strip(),
            "details":
                str(
                    r.get(
                        "details",
                        "",
                    )
                ).strip(),
            "status":
                "UNSCHEDULED",
        }
    )


final_unscheduled.extend(
    new_unplaced
)

final_unscheduled_ids = {
    r["job_id"]
    for r in final_unscheduled
}

if (
    old_unscheduled_ids
    & new_unplaced_ids
):
    raise RuntimeError(
        "Overlap between original and newly unscheduled jobs."
    )


if len(final_unscheduled_ids) != 203:
    raise RuntimeError(
        "Expected 203 total unscheduled jobs, found "
        f"{len(final_unscheduled_ids)}"
    )


# ============================================================
# GLOBAL 441-JOB ACCOUNTING
# ============================================================

eligible_ids = set(
    eligible.keys()
)

accounted_ids = (
    scheduled_set
    | final_unscheduled_ids
)

missing_accounted = (
    eligible_ids
    - accounted_ids
)

unexpected_accounted = (
    accounted_ids
    - eligible_ids
)

if missing_accounted:
    raise RuntimeError(
        "Eligible jobs not accounted for: "
        f"{sorted(missing_accounted)[:20]}"
    )

if unexpected_accounted:
    raise RuntimeError(
        "Jobs accounted but not present in eligible_jobs: "
        f"{sorted(unexpected_accounted)}"
    )


if (
    len(scheduled_set)
    + len(final_unscheduled_ids)
    != 441
):
    raise RuntimeError(
        "441-job accounting failed."
    )


if scheduled_set & final_unscheduled_ids:
    raise RuntimeError(
        "Scheduled and unscheduled sets overlap."
    )


# ============================================================
# DEPOT
# ============================================================

depot = depot_rows[0]

if str(
    depot.get(
        "latitude",
        ""
    )
).strip():

    depot_lat = fnum(
        depot["latitude"],
        "depot.latitude",
    )

elif str(
    depot.get(
        "lat",
        ""
    )
).strip():

    depot_lat = fnum(
        depot["lat"],
        "depot.lat",
    )

else:
    raise RuntimeError(
        "Depot latitude missing."
    )


if str(
    depot.get(
        "longitude",
        ""
    )
).strip():

    depot_lon = fnum(
        depot["longitude"],
        "depot.longitude",
    )

elif str(
    depot.get(
        "long",
        ""
    )
).strip():

    depot_lon = fnum(
        depot["long"],
        "depot.long",
    )

elif str(
    depot.get(
        "lon",
        ""
    )
).strip():

    depot_lon = fnum(
        depot["lon"],
        "depot.lon",
    )

else:
    raise RuntimeError(
        "Depot longitude missing."
    )


# ============================================================
# GROUP FINAL SCHEDULE
# ============================================================

groups = defaultdict(list)

for r in final_rows:

    team = str(
        r["team_id"]
    ).strip()

    date = date_only(
        r["schedule_date"]
    )

    groups[
        (team, date)
    ].append(
        dict(r)
    )


# ============================================================
# ROUTE AUDIT
# ============================================================

route_audit = []
route_violations = []


def osrm_route(
    coordinates
):

    coordinate_string = ";".join(
        f"{lon},{lat}"
        for lon, lat in coordinates
    )

    # Full matrix is tiny here:
    # depot + maximum few jobs + depot.
    url = (
        f"{OSRM_URL}/"
        f"{urllib.parse.quote(
            coordinate_string,
            safe=',;'
        )}"
        "?annotations=duration,distance"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "CivicBrain-Step13-FinalAudit/1.0"
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


print("=" * 80)
print("CIVICBRAIN STEP 13 — FINAL CANDIDATE BUILD + OSRM AUDIT")
print("=" * 80)

print(
    f"Eligible jobs            : {len(eligible_ids)}"
)

print(
    f"Final scheduled jobs      : {len(scheduled_set)}"
)

print(
    f"Final unscheduled jobs    : {len(final_unscheduled_ids)}"
)

print()


for group_number, (
    (team, date),
    rows,
) in enumerate(
    sorted(groups.items()),
    start=1,
):

    rows.sort(
        key=lambda r: int(
            r["sequence_no"]
        )
    )

    # Check sequence integrity.
    expected_sequence = list(
        range(
            1,
            len(rows) + 1,
        )
    )

    actual_sequence = [
        int(
            r["sequence_no"]
        )
        for r in rows
    ]

    if actual_sequence != expected_sequence:

        raise RuntimeError(
            f"Bad sequence for "
            f"{team} {date}: "
            f"{actual_sequence}"
        )


    job_ids = [
        str(
            r["job_id"]
        ).strip()
        for r in rows
    ]

    if len(job_ids) != len(
        set(job_ids)
    ):

        raise RuntimeError(
            f"Duplicate jobs inside route "
            f"{team} {date}"
        )


    coordinates = [
        (
            depot_lon,
            depot_lat,
        )
    ]

    coordinates.extend(
        (
            eligible[job]["lon"],
            eligible[job]["lat"],
        )
        for job in job_ids
    )

    payload = osrm_route(
        coordinates
    )

    durations = payload["durations"]
    distances = payload["distances"]

    route_travel_s = 0.0
    route_distance_m = 0.0

    current_time_s = 0.0

    base_dt = datetime.strptime(
        f"{date} {SHIFT_START}",
        "%Y-%m-%d %H:%M",
    )

    updated_rows = []

    for i, row in enumerate(
        rows,
        start=1,
    ):

        # depot/job sequence:
        # matrix index i -> current job
        from_idx = i - 1
        to_idx = i

        travel_s = durations[
            from_idx
        ][
            to_idx
        ]

        distance_m = distances[
            from_idx
        ][
            to_idx
        ]

        if (
            travel_s is None
            or distance_m is None
        ):

            raise RuntimeError(
                f"Missing route "
                f"{team} {date} "
                f"{from_idx}->{to_idx}"
            )


        travel_s = float(
            travel_s
        )

        distance_m = float(
            distance_m
        )

        current_time_s += travel_s

        start_dt = (
            base_dt
            + timedelta(
                seconds=current_time_s
            )
        )

        service_h = eligible[
            row["job_id"]
        ]["service_h"]

        end_dt = (
            start_dt
            + timedelta(
                hours=service_h
            )
        )

        updated = dict(row)

        updated[
            "planned_start"
        ] = start_dt.strftime(
            "%Y-%m-%d %H:%M"
        )

        updated[
            "planned_end"
        ] = end_dt.strftime(
            "%Y-%m-%d %H:%M"
        )

        updated[
            "travel_distance_m"
        ] = round(
            distance_m,
            1,
        )

        updated[
            "travel_time_min"
        ] = round(
            travel_s / 60.0,
            3,
        )

        updated_rows.append(
            updated
        )

        current_time_s += (
            service_h
            * 3600.0
        )

        route_travel_s += (
            travel_s
        )

        route_distance_m += (
            distance_m
        )


    # --------------------------------------------------------
    # Return to depot
    # --------------------------------------------------------

    last_job_index = len(rows)

    return_travel_s = durations[
        last_job_index
    ][
        0
    ]

    return_distance_m = distances[
        last_job_index
    ][
        0
    ]

    if (
        return_travel_s is None
        or return_distance_m is None
    ):

        raise RuntimeError(
            f"Missing return-to-depot route "
            f"{team} {date}"
        )

    return_travel_s = float(
        return_travel_s
    )

    return_distance_m = float(
        return_distance_m
    )

    route_travel_s += (
        return_travel_s
    )

    route_distance_m += (
        return_distance_m
    )

    service_h = sum(
        eligible[job]["service_h"]
        for job in job_ids
    )

    travel_h = (
        route_travel_s
        / 3600.0
    )

    total_h = (
        service_h
        + travel_h
    )

    finish_dt = (
        base_dt
        + timedelta(
            seconds=
            total_h * 3600.0
        )
    )

    status = (
        "PASS"
        if total_h
        <= SHIFT_HOURS + 1e-9
        else
        "TRAVEL_TIME_VIOLATION"
    )

    if status != "PASS":

        route_violations.append(
            {
                "team_id":
                    team,
                "schedule_date":
                    date,
                "job_count":
                    len(job_ids),
                "service_h":
                    round(
                        service_h,
                        6,
                    ),
                "travel_h":
                    round(
                        travel_h,
                        6,
                    ),
                "total_route_h":
                    round(
                        total_h,
                        6,
                    ),
                "finish_time":
                    finish_dt.strftime(
                        "%H:%M"
                    ),
                "status":
                    status,
            }
        )


    route_audit.append(
        {
            "team_id":
                team,
            "schedule_date":
                date,
            "job_count":
                len(job_ids),
            "jobs":
                "|".join(job_ids),
            "service_h":
                round(
                    service_h,
                    6,
                ),
            "travel_h":
                round(
                    travel_h,
                    6,
                ),
            "total_route_h":
                round(
                    total_h,
                    6,
                ),
            "distance_km":
                round(
                    route_distance_m
                    / 1000.0,
                    6,
                ),
            "finish_time":
                finish_dt.strftime(
                    "%H:%M"
                ),
            "status":
                status,
        }
    )


    # Replace rows with freshly OSRM-audited times.
    group_key = (
        team,
        date,
    )

    groups[group_key] = (
        updated_rows
    )

    if (
        group_number % 10 == 0
        or group_number
        == len(groups)
    ):

        print(
            f"Route audit progress: "
            f"{group_number}/"
            f"{len(groups)}"
        )

    time.sleep(
        REQUEST_DELAY
    )


# ============================================================
# REBUILD FINAL SCHEDULE WITH AUDITED ROWS
# ============================================================

audited_schedule = []

for (
    team,
    date,
), rows in sorted(
    groups.items(),
    key=lambda x: (
        x[0][1],
        x[0][0],
    ),
):

    audited_schedule.extend(
        rows
    )


# ============================================================
# FINAL VALIDATION
# ============================================================

audited_ids = [
    str(
        r["job_id"]
    ).strip()
    for r in audited_schedule
]

audited_set = set(
    audited_ids
)

checks = [
    {
        "check":
            "ELIGIBLE_JOB_COUNT",
        "expected":
            441,
        "actual":
            len(eligible_ids),
        "status":
            "PASS"
            if len(eligible_ids)
            == 441
            else "FAIL",
    },
    {
        "check":
            "FINAL_SCHEDULED_JOB_COUNT",
        "expected":
            238,
        "actual":
            len(audited_set),
        "status":
            "PASS"
            if len(audited_set)
            == 238
            else "FAIL",
    },
    {
        "check":
            "FINAL_UNSCHEDULED_JOB_COUNT",
        "expected":
            203,
        "actual":
            len(final_unscheduled_ids),
        "status":
            "PASS"
            if len(final_unscheduled_ids)
            == 203
            else "FAIL",
    },
    {
        "check":
            "NO_DUPLICATE_SCHEDULED_JOBS",
        "expected":
            len(audited_set),
        "actual":
            len(audited_ids),
        "status":
            "PASS"
            if len(audited_set)
            == len(audited_ids)
            else "FAIL",
    },
    {
        "check":
            "ALL_441_JOBS_ACCOUNTED",
        "expected":
            441,
        "actual":
            len(
                audited_set
                | final_unscheduled_ids
            ),
        "status":
            "PASS"
            if (
                audited_set
                | final_unscheduled_ids
            )
            == eligible_ids
            else "FAIL",
    },
    {
        "check":
            "SCHEDULED_UNSCHEDULED_DISJOINT",
        "expected":
            "YES",
        "actual":
            "YES"
            if audited_set.isdisjoint(
                final_unscheduled_ids
            )
            else "NO",
        "status":
            "PASS"
            if audited_set.isdisjoint(
                final_unscheduled_ids
            )
            else "FAIL",
    },
    {
        "check":
            "ROUTE_SHIFT_FEASIBILITY",
        "expected":
            "<=9h",
        "actual":
            (
                "PASS"
                if not route_violations
                else "VIOLATIONS"
            ),
        "status":
            (
                "PASS"
                if not route_violations
                else "FAIL"
            ),
    },
]


overall_pass = all(
    row["status"] == "PASS"
    for row in checks
)


# ============================================================
# WRITE FINAL CANDIDATES
# ============================================================

schedule_fields = [
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
        fieldnames=schedule_fields,
    )

    writer.writeheader()

    for row in audited_schedule:

        writer.writerow(
            {
                field:
                    row.get(
                        field,
                        "",
                    )
                for field in schedule_fields
            }
        )


unscheduled_fields = [
    "job_id",
    "complaint_id",
    "cluster_id",
    "work_type",
    "priority_score",
    "reason",
    "details",
    "status",
]


with open(
    OUT_UNSCHEDULED,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=unscheduled_fields,
    )

    writer.writeheader()

    for row in sorted(
        final_unscheduled,
        key=lambda r: (
            -float(
                r["priority_score"]
                or 0
            ),
            r["job_id"],
        ),
    ):

        writer.writerow(
            {
                field:
                    row.get(
                        field,
                        "",
                    )
                for field in unscheduled_fields
            }
        )


with open(
    OUT_ROUTE_AUDIT,
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "team_id",
        "schedule_date",
        "job_count",
        "jobs",
        "service_h",
        "travel_h",
        "total_route_h",
        "distance_km",
        "finish_time",
        "status",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(
        route_audit
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
    writer.writerows(
        checks
    )


# ============================================================
# SUMMARY
# ============================================================

total_service_h = sum(
    r["service_h"]
    for r in route_audit
)

total_travel_h = sum(
    r["travel_h"]
    for r in route_audit
)

total_route_h = sum(
    r["total_route_h"]
    for r in route_audit
)

total_distance_km = sum(
    r["distance_km"]
    for r in route_audit
)

max_route = max(
    route_audit,
    key=lambda r: r["total_route_h"],
    default=None,
)

summary = {
    "status":
        "PASS"
        if overall_pass
        else "REVIEW_REQUIRED",
    "eligible_jobs":
        441,
    "scheduled_jobs":
        len(audited_set),
    "unscheduled_jobs":
        len(final_unscheduled_ids),
    "new_travel_infeasible_jobs":
        ["11", "143", "179"],
    "route_groups":
        len(route_audit),
    "route_violations":
        len(route_violations),
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
    "max_route":
        max_route,
    "validation":
        {
            row["check"]:
                row["status"]
            for row in checks
        },
    "outputs":
        {
            "schedule":
                str(OUT_SCHEDULE),
            "unscheduled":
                str(OUT_UNSCHEDULED),
            "route_audit":
                str(OUT_ROUTE_AUDIT),
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
print("FINAL STEP 13 CANDIDATE RESULT")
print("=" * 80)

print(
    f"Eligible jobs          : "
    f"{len(eligible_ids)}"
)

print(
    f"Scheduled jobs         : "
    f"{len(audited_set)}"
)

print(
    f"Unscheduled jobs       : "
    f"{len(final_unscheduled_ids)}"
)

print(
    f"Route groups           : "
    f"{len(route_audit)}"
)

print(
    f"Route violations       : "
    f"{len(route_violations)}"
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
    f"{total_route_h:.3f}"
)

print(
    f"Total road distance    : "
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
        f"Service                : "
        f"{max_route['service_h']:.3f} h"
    )

    print(
        f"Travel                 : "
        f"{max_route['travel_h']:.3f} h"
    )

    print(
        f"Total                  : "
        f"{max_route['total_route_h']:.3f} h"
    )

    print(
        f"Finish                 : "
        f"{max_route['finish_time']}"
    )

if route_violations:

    print()
    print("ROUTE VIOLATIONS")
    print("-" * 80)

    for row in route_violations:

        print(
            f"{row['team_id']} "
            f"{row['schedule_date']} "
            f"jobs={row['job_count']} "
            f"total={row['total_route_h']:.3f}h"
        )


print()
print("VALIDATION")
print("-" * 80)

for row in checks:

    print(
        f"{row['check']:<40}"
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
    f"Unscheduled: {OUT_UNSCHEDULED}"
)

print(
    f"Route audit: {OUT_ROUTE_AUDIT}"
)

print(
    f"Validation : {OUT_VALIDATION}"
)

print(
    f"Summary    : {OUT_SUMMARY}"
)

print()
print("=" * 80)
print("FINAL STEP 13 CANDIDATE AUDIT COMPLETE")
print("=" * 80)

