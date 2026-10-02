import csv
from pathlib import Path

ROOT = Path(".")

ROUTE_FILE = ROOT / "data/optimization/routing/final_step13_route_audit.csv"
JOBS_FILE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
DEPOT_FILE = ROOT / "data/optimization/routing/depot_master.csv"

OUT_FILE = ROOT / "data/optimization/evaluation/load_step13_routes.sql"


def sql_text(value):
    if value is None:
        return "NULL"

    value = str(value).strip()

    if value == "":
        return "NULL"

    return "'" + value.replace("'", "''") + "'"


def sql_num(value):
    if value is None or str(value).strip() == "":
        return "NULL"

    return str(value).strip()


with open(ROUTE_FILE, encoding="utf-8-sig", newline="") as f:
    routes = list(csv.DictReader(f))

with open(JOBS_FILE, encoding="utf-8-sig", newline="") as f:
    jobs = {
        str(r["job_id"]).strip(): r
        for r in csv.DictReader(f)
    }

with open(DEPOT_FILE, encoding="utf-8-sig", newline="") as f:
    depot = next(csv.DictReader(f))

if len(routes) != 109:
    raise RuntimeError(
        f"Expected 109 final routes, found {len(routes)}"
    )

# ------------------------------------------------------------------
# Validate route job coverage
# ------------------------------------------------------------------

all_route_jobs = []

for r in routes:
    route_jobs = [
        j.strip()
        for j in str(r["jobs"]).split("|")
        if j.strip()
    ]

    if len(route_jobs) != int(r["job_count"]):
        raise RuntimeError(
            f"Job-count mismatch for "
            f"{r['team_id']} / {r['schedule_date']}"
        )

    for job_id in route_jobs:
        if job_id not in jobs:
            raise RuntimeError(
                f"Route references missing eligible job_id={job_id}"
            )

    all_route_jobs.extend(route_jobs)

if len(all_route_jobs) != 238:
    raise RuntimeError(
        f"Expected 238 routed jobs, found {len(all_route_jobs)}"
    )

if len(set(all_route_jobs)) != 238:
    raise RuntimeError(
        "Final route audit contains duplicate job IDs."
    )

# ------------------------------------------------------------------
# Generate SQL
# ------------------------------------------------------------------

sql = []

sql.append("-- ================================================================")
sql.append("-- CIVICBRAIN STEP 13 - LOAD FINAL ROUTES")
sql.append("-- Source: final_step13_route_audit.csv")
sql.append("-- Final routes: 109")
sql.append("-- Final routed jobs: 238")
sql.append("-- ================================================================")
sql.append("")
sql.append("BEGIN;")
sql.append("")

sql.append("TRUNCATE TABLE")
sql.append("    step13_route_stops,")
sql.append("    step13_routes")
sql.append("RESTART IDENTITY;")
sql.append("")

# ------------------------------------------------------------------
# Route headers
# ------------------------------------------------------------------

for idx, r in enumerate(routes, start=1):

    route_id_expr = f"{idx}"

    sql.append(
        "INSERT INTO step13_routes ("
        "team_id, "
        "schedule_date, "
        "distance_km, "
        "travel_time_h, "
        "service_time_h, "
        "total_route_time_h, "
        "finish_time, "
        "status, "
        "source"
        ") VALUES ("
        f"{sql_text(r['team_id'])}, "
        f"{sql_text(r['schedule_date'])}, "
        f"{sql_num(r['distance_km'])}, "
        f"{sql_num(r['travel_h'])}, "
        f"{sql_num(r['service_h'])}, "
        f"{sql_num(r['total_route_h'])}, "
        f"{sql_text(r['finish_time'])}, "
        f"{sql_text(r['status'])}, "
        "'final_step13_route_audit'"
        ");"
    )

    route_jobs = [
        j.strip()
        for j in str(r["jobs"]).split("|")
        if j.strip()
    ]

    # --------------------------------------------------------------
    # Depot start
    # --------------------------------------------------------------

    sql.append(
        "INSERT INTO step13_route_stops ("
        "route_id, "
        "stop_order, "
        "node_type, "
        "job_id, "
        "latitude, "
        "longitude, "
        "travel_distance_m, "
        "travel_time_s"
        ") VALUES ("
        f"{route_id_expr}, "
        "0, "
        "'DEPOT', "
        "NULL, "
        f"{sql_num(depot['latitude'])}, "
        f"{sql_num(depot['longitude'])}, "
        "NULL, "
        "NULL"
        ");"
    )

    # --------------------------------------------------------------
    # Actual job stops in final optimized route order
    # --------------------------------------------------------------

    for stop_no, job_id in enumerate(route_jobs, start=1):

        job = jobs[job_id]

        sql.append(
            "INSERT INTO step13_route_stops ("
            "route_id, "
            "stop_order, "
            "node_type, "
            "job_id, "
            "latitude, "
            "longitude, "
            "travel_distance_m, "
            "travel_time_s"
            ") VALUES ("
            f"{route_id_expr}, "
            f"{stop_no}, "
            "'JOB', "
            f"{sql_text(job_id)}, "
            f"{sql_num(job['latitude'])}, "
            f"{sql_num(job['longitude'])}, "
            "NULL, "
            "NULL"
            ");"
        )

    # --------------------------------------------------------------
    # Return to depot
    # --------------------------------------------------------------

    return_order = len(route_jobs) + 1

    sql.append(
        "INSERT INTO step13_route_stops ("
        "route_id, "
        "stop_order, "
        "node_type, "
        "job_id, "
        "latitude, "
        "longitude, "
        "travel_distance_m, "
        "travel_time_s"
        ") VALUES ("
        f"{route_id_expr}, "
        f"{return_order}, "
        "'DEPOT', "
        "NULL, "
        f"{sql_num(depot['latitude'])}, "
        f"{sql_num(depot['longitude'])}, "
        "NULL, "
        "NULL"
        ");"
    )

    sql.append("")

sql.append("COMMIT;")
sql.append("")

# ------------------------------------------------------------------
# Verification
# ------------------------------------------------------------------

sql.append("-- ================================================================")
sql.append("-- VERIFICATION")
sql.append("-- ================================================================")
sql.append("")

sql.append(
    "SELECT COUNT(*) AS route_count "
    "FROM step13_routes;"
)

sql.append("")

sql.append(
    "SELECT COUNT(*) AS route_stop_count "
    "FROM step13_route_stops;"
)

sql.append("")

sql.append(
    "SELECT COUNT(DISTINCT job_id) AS unique_route_jobs "
    "FROM step13_route_stops "
    "WHERE node_type = 'JOB';"
)

sql.append("")

sql.append(
    "SELECT "
    "status, "
    "COUNT(*) AS route_count "
    "FROM step13_routes "
    "GROUP BY status "
    "ORDER BY status;"
)

sql.append("")

sql.append(
    "SELECT "
    "team_id, "
    "COUNT(*) AS route_count, "
    "SUM(distance_km) AS distance_km, "
    "SUM(total_route_time_h) AS route_hours "
    "FROM step13_routes "
    "GROUP BY team_id "
    "ORDER BY team_id;"
)

sql.append("")

sql.append(
    "SELECT "
    "MIN(finish_time) AS earliest_finish, "
    "MAX(finish_time) AS latest_finish "
    "FROM step13_routes;"
)

with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(sql))

print("=" * 80)
print("STEP 13 ROUTE DB LOAD SQL GENERATED")
print("=" * 80)
print(f"Final route rows       : {len(routes)}")
print(f"Final routed jobs      : {len(all_route_jobs)}")
print(f"Unique routed jobs     : {len(set(all_route_jobs))}")
print(f"SQL output             : {OUT_FILE}")
print("=" * 80)
