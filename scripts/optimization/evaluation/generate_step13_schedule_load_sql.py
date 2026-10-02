import csv
from pathlib import Path

ROOT = Path(".")

SCHEDULE_FILE = ROOT / "data/optimization/scheduling/final_step13_schedule_candidate.csv"
OUT_FILE = ROOT / "data/optimization/evaluation/load_step13_schedule.sql"

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)


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


with open(SCHEDULE_FILE, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 238:
    raise RuntimeError(
        f"Expected 238 final scheduled rows, found {len(rows)}"
    )

job_ids = [str(r["job_id"]).strip() for r in rows]

if len(set(job_ids)) != 238:
    raise RuntimeError("Final schedule contains duplicate job IDs.")

# ---------------------------------------------------------------
# Build unique schedule headers
# ---------------------------------------------------------------

schedule_headers = {}

for r in rows:
    schedule_id = str(r["schedule_id"]).strip()

    if not schedule_id:
        raise RuntimeError(
            f"Blank schedule_id for job_id={r['job_id']}"
        )

    key = schedule_id

    header = (
        str(r["team_id"]).strip(),
        str(r["schedule_date"]).strip(),
    )

    if key in schedule_headers and schedule_headers[key] != header:
        raise RuntimeError(
            f"Schedule ID maps to multiple team/date values: {key}"
        )

    schedule_headers[key] = header

# ---------------------------------------------------------------
# Generate SQL
# ---------------------------------------------------------------

sql = []

sql.append("-- ================================================================")
sql.append("-- CIVICBRAIN STEP 13 - LOAD FINAL SCHEDULE")
sql.append("-- Source: final_step13_schedule_candidate.csv")
sql.append("-- Validated scheduled jobs: 238")
sql.append("-- ================================================================")
sql.append("")
sql.append("BEGIN;")
sql.append("")

# Re-runnable only for isolated Step 13 prototype tables.
sql.append("TRUNCATE TABLE")
sql.append("    step13_schedule_job,")
sql.append("    step13_schedules")
sql.append("RESTART IDENTITY;")
sql.append("")

# ---------------------------------------------------------------
# Schedule headers
# ---------------------------------------------------------------

for schedule_id in sorted(schedule_headers):

    team_id, schedule_date = schedule_headers[schedule_id]

    sql.append(
        "INSERT INTO step13_schedules ("
        "schedule_id, "
        "team_id, "
        "schedule_date, "
        "schedule_status, "
        "source"
        ") VALUES ("
        f"{sql_text(schedule_id)}, "
        f"{sql_text(team_id)}, "
        f"{sql_text(schedule_date)}, "
        "'FINAL_CANDIDATE', "
        "'step13_final_travel_aware'"
        ");"
    )

sql.append("")

# ---------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------

for r in rows:

    cluster_id = str(r.get("cluster_id", "")).strip()

    sql.append(
        "INSERT INTO step13_schedule_job ("
        "schedule_id, "
        "job_id, "
        "sequence_no, "
        "cluster_id, "
        "planned_start, "
        "planned_end, "
        "service_duration_h, "
        "travel_distance_m, "
        "travel_time_min, "
        "priority_score, "
        "estimated_cost, "
        "status, "
        "repair_action"
        ") VALUES ("
        f"{sql_text(r['schedule_id'])}, "
        f"{sql_text(r['job_id'])}, "
        f"{sql_num(r['sequence_no'])}, "
        f"{sql_text(cluster_id)}, "
        f"{sql_text(r['planned_start'])}, "
        f"{sql_text(r['planned_end'])}, "
        f"{sql_num(r['service_duration_h'])}, "
        f"{sql_num(r['travel_distance_m'])}, "
        f"{sql_num(r['travel_time_min'])}, "
        f"{sql_num(r['priority_score'])}, "
        f"{sql_num(r['estimated_cost'])}, "
        f"{sql_text(r['status'])}, "
        f"{sql_text(r.get('repair_action', ''))}"
        ");"
    )

sql.append("")
sql.append("COMMIT;")
sql.append("")

# ---------------------------------------------------------------
# Verification queries
# ---------------------------------------------------------------

sql.append("-- ================================================================")
sql.append("-- VERIFICATION")
sql.append("-- ================================================================")
sql.append("")

sql.append(
    "SELECT COUNT(*) AS schedule_header_count "
    "FROM step13_schedules;"
)

sql.append("")

sql.append(
    "SELECT COUNT(*) AS scheduled_job_count "
    "FROM step13_schedule_job;"
)

sql.append("")

sql.append(
    "SELECT COUNT(DISTINCT job_id) AS unique_scheduled_jobs "
    "FROM step13_schedule_job;"
)

sql.append("")

sql.append(
    "SELECT "
    "s.team_id, "
    "COUNT(*) AS schedule_count "
    "FROM step13_schedules s "
    "GROUP BY s.team_id "
    "ORDER BY s.team_id;"
)

sql.append("")

sql.append(
    "SELECT "
    "s.schedule_status, "
    "COUNT(*) AS count "
    "FROM step13_schedules s "
    "GROUP BY s.schedule_status "
    "ORDER BY s.schedule_status;"
)

sql.append("")

sql.append(
    "SELECT "
    "MIN(planned_start) AS earliest_start, "
    "MAX(planned_end) AS latest_end "
    "FROM step13_schedule_job;"
)

with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(sql))

print("=" * 80)
print("STEP 13 SCHEDULE DB LOAD SQL GENERATED")
print("=" * 80)
print(f"Final schedule rows : {len(rows)}")
print(f"Schedule headers    : {len(schedule_headers)}")
print(f"Unique job IDs      : {len(set(job_ids))}")
print(f"SQL output          : {OUT_FILE}")
print("=" * 80)
