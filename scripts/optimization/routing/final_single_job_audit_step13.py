import csv
import json
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(".")

JOBS_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"

JOB_IDS = ["11", "143", "179"]

SHIFT_HOURS = 9.0

jobs = {}

with open(JOBS_FILE, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        job_id = str(r["job_id"]).strip()

        if job_id in JOB_IDS:
            jobs[job_id] = {
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "service_h": float(
                    r["service_duration_hours"]
                ),
                "work_type": r["work_type"],
                "priority": float(
                    r["priority_score"]
                ),
            }

with open(DEPOT_FILE, encoding="utf-8-sig") as f:
    depot = next(csv.DictReader(f))

depot_lat = float(
    depot.get("latitude", depot.get("lat"))
)

depot_lon = float(
    depot.get(
        "longitude",
        depot.get(
            "long",
            depot.get("lon")
        )
    )
)

coords = [
    (depot_lon, depot_lat)
]

for job_id in JOB_IDS:
    coords.append(
        (
            jobs[job_id]["longitude"],
            jobs[job_id]["latitude"],
        )
    )

coordinate_string = ";".join(
    f"{lon},{lat}"
    for lon, lat in coords
)

url = (
    "https://router.project-osrm.org/table/v1/driving/"
    + urllib.parse.quote(
        coordinate_string,
        safe=",;"
    )
    + "?annotations=duration,distance"
)

request = urllib.request.Request(
    url,
    headers={
        "User-Agent":
            "CivicBrain-Step13-FinalSingleJobAudit/1.0"
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

durations = payload["durations"]
distances = payload["distances"]

print("=" * 80)
print("CIVICBRAIN STEP 13 — FINAL SINGLE-JOB FEASIBILITY")
print("=" * 80)

print(
    f"Depot : {depot_lat}, {depot_lon}"
)

print()

for i, job_id in enumerate(JOB_IDS, start=1):

    outbound_s = durations[0][i]
    return_s = durations[i][0]

    outbound_m = distances[0][i]
    return_m = distances[i][0]

    travel_s = (
        outbound_s
        + return_s
    )

    travel_h = travel_s / 3600.0

    total_h = (
        jobs[job_id]["service_h"]
        + travel_h
    )

    slack_h = (
        SHIFT_HOURS
        - total_h
    )

    feasible = (
        total_h
        <= SHIFT_HOURS
    )

    print("-" * 80)

    print(
        f"JOB                  : {job_id}"
    )

    print(
        f"WORK TYPE            : "
        f"{jobs[job_id]['work_type']}"
    )

    print(
        f"SERVICE HOURS        : "
        f"{jobs[job_id]['service_h']:.3f}"
    )

    print(
        f"OUTBOUND DISTANCE    : "
        f"{outbound_m:.1f} m"
    )

    print(
        f"RETURN DISTANCE      : "
        f"{return_m:.1f} m"
    )

    print(
        f"TOTAL TRAVEL         : "
        f"{travel_h:.3f} h"
    )

    print(
        f"SERVICE + TRAVEL    : "
        f"{total_h:.3f} h"
    )

    print(
        f"SHIFT SLACK          : "
        f"{slack_h:.3f} h"
    )

    print(
        f"9H SHIFT FEASIBLE    : "
        f"{'YES' if feasible else 'NO'}"
    )

print()
print("=" * 80)
print("FINAL SINGLE-JOB AUDIT COMPLETE")
print("=" * 80)
