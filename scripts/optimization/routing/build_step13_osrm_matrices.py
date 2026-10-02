import csv
import json
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(".")

DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"
JOBS_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
SCHEDULE_FILE = ROOT / "data/optimization/scheduling/schedule_results.csv"

OUT_DIR = ROOT / "data/optimization/routing"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DIST_FILE = OUT_DIR / "route_distance_matrix.csv"
TIME_FILE = OUT_DIR / "route_time_matrix.csv"
NODES_FILE = OUT_DIR / "route_group_nodes.csv"

# ------------------------------------------------------------------
# Load inputs
# ------------------------------------------------------------------

with open(DEPOT_FILE, encoding="utf-8-sig") as f:
    depot = next(csv.DictReader(f))

with open(JOBS_FILE, encoding="utf-8-sig") as f:
    jobs = {r["job_id"]: r for r in csv.DictReader(f)}

with open(SCHEDULE_FILE, encoding="utf-8-sig") as f:
    schedule = list(csv.DictReader(f))

# ------------------------------------------------------------------
# Basic checks
# ------------------------------------------------------------------

if len(schedule) != 241:
    raise RuntimeError(f"Expected 241 scheduled rows, found {len(schedule)}")

job_ids = [r["job_id"] for r in schedule]

if len(set(job_ids)) != 241:
    raise RuntimeError("Scheduled job IDs are not unique")

missing = [jid for jid in job_ids if jid not in jobs]

if missing:
    raise RuntimeError(f"Missing jobs in eligible_jobs.csv: {missing[:10]}")

# ------------------------------------------------------------------
# Group by team + date
# ------------------------------------------------------------------

groups = defaultdict(list)

for r in schedule:
    groups[(r["team_id"], r["schedule_date"])].append(r)

groups = dict(sorted(groups.items()))

print("=" * 80)
print("CIVICBRAIN STEP 13 — OSRM ROUTING MATRICES")
print("=" * 80)

print("Scheduled jobs :", len(schedule))
print("Routing groups :", len(groups))

# ------------------------------------------------------------------
# Output writers
# ------------------------------------------------------------------

distance_rows = []
time_rows = []
node_rows = []

depot_lon = float(depot["longitude"])
depot_lat = float(depot["latitude"])

successful_groups = 0
failed_groups = []

for group_index, ((team_id, schedule_date), rows) in enumerate(groups.items(), start=1):

    rows = sorted(rows, key=lambda x: int(x["sequence_no"]))

    # --------------------------------------------------------------
    # Build nodes
    # node 0 = depot
    # nodes 1..N = actual jobs
    # --------------------------------------------------------------

    nodes = [
        {
            "node_index": 0,
            "node_type": "DEPOT",
            "node_id": depot["depot_id"],
            "job_id": "",
            "latitude": depot_lat,
            "longitude": depot_lon,
        }
    ]

    for idx, r in enumerate(rows, start=1):
        job = jobs[r["job_id"]]

        nodes.append(
            {
                "node_index": idx,
                "node_type": "JOB",
                "node_id": r["job_id"],
                "job_id": r["job_id"],
                "latitude": float(job["latitude"]),
                "longitude": float(job["longitude"]),
            }
        )

    # Save node mapping
    for n in nodes:
        node_rows.append(
            {
                "group_index": group_index,
                "team_id": team_id,
                "schedule_date": schedule_date,
                "node_index": n["node_index"],
                "node_type": n["node_type"],
                "node_id": n["node_id"],
                "job_id": n["job_id"],
                "latitude": n["latitude"],
                "longitude": n["longitude"],
            }
        )

    # --------------------------------------------------------------
    # OSRM Table request
    # --------------------------------------------------------------

    coords = ";".join(
        f'{n["longitude"]},{n["latitude"]}'
        for n in nodes
    )

    url = (
        f"https://router.project-osrm.org/"
        f"table/v1/driving/{coords}"
        f"?annotations=distance,duration"
    )

    print(
        f"[{group_index:03d}/{len(groups):03d}] "
        f"{team_id} / {schedule_date} / "
        f"jobs={len(rows)}"
    )

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "CivicBrain/1.0"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)

        if data.get("code") != "Ok":
            raise RuntimeError(
                f"OSRM code={data.get('code')}"
            )

        distances = data.get("distances")
        durations = data.get("durations")

        expected_size = len(nodes)

        if len(distances) != expected_size:
            raise RuntimeError("Distance matrix row count mismatch")

        if len(durations) != expected_size:
            raise RuntimeError("Duration matrix row count mismatch")

        for i in range(expected_size):
            if len(distances[i]) != expected_size:
                raise RuntimeError(
                    f"Distance matrix column mismatch at row {i}"
                )

            if len(durations[i]) != expected_size:
                raise RuntimeError(
                    f"Duration matrix column mismatch at row {i}"
                )

            for j in range(expected_size):
                distance_rows.append(
                    {
                        "group_index": group_index,
                        "team_id": team_id,
                        "schedule_date": schedule_date,
                        "from_node_index": i,
                        "to_node_index": j,
                        "distance_m": distances[i][j],
                    }
                )

                time_rows.append(
                    {
                        "group_index": group_index,
                        "team_id": team_id,
                        "schedule_date": schedule_date,
                        "from_node_index": i,
                        "to_node_index": j,
                        "travel_time_s": durations[i][j],
                    }
                )

        successful_groups += 1

    except Exception as e:
        failed_groups.append(
            {
                "group_index": group_index,
                "team_id": team_id,
                "schedule_date": schedule_date,
                "error": str(e),
            }
        )

    # Be polite to public OSRM
    time.sleep(0.5)

# ------------------------------------------------------------------
# Write outputs
# ------------------------------------------------------------------

with open(DIST_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_index",
            "team_id",
            "schedule_date",
            "from_node_index",
            "to_node_index",
            "distance_m",
        ],
    )
    writer.writeheader()
    writer.writerows(distance_rows)

with open(TIME_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_index",
            "team_id",
            "schedule_date",
            "from_node_index",
            "to_node_index",
            "travel_time_s",
        ],
    )
    writer.writeheader()
    writer.writerows(time_rows)

with open(NODES_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "group_index",
            "team_id",
            "schedule_date",
            "node_index",
            "node_type",
            "node_id",
            "job_id",
            "latitude",
            "longitude",
        ],
    )
    writer.writeheader()
    writer.writerows(node_rows)

# ------------------------------------------------------------------
# Final report
# ------------------------------------------------------------------

print()
print("=" * 80)
print("OSRM MATRIX BUILD SUMMARY")
print("=" * 80)
print("Groups total       :", len(groups))
print("Groups successful  :", successful_groups)
print("Groups failed      :", len(failed_groups))
print("Distance rows      :", len(distance_rows))
print("Time rows          :", len(time_rows))
print("Node mapping rows  :", len(node_rows))
print()

if failed_groups:
    print("FAILED GROUPS")
    for f in failed_groups:
        print(
            f'{f["group_index"]}: '
            f'{f["team_id"]} / '
            f'{f["schedule_date"]} / '
            f'{f["error"]}'
        )
    raise RuntimeError("One or more OSRM groups failed")

print("STATUS             : PASS")
print("Distance output    :", DIST_FILE)
print("Time output        :", TIME_FILE)
print("Node output        :", NODES_FILE)
