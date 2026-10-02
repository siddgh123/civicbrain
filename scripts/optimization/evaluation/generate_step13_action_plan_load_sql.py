import csv
from pathlib import Path

ROOT = Path(".")

AP_FILE = ROOT / "data/optimization/action_plan/action_plan.csv"
OUT_FILE = ROOT / "data/optimization/evaluation/load_step13_action_plans.sql"

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


with open(AP_FILE, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 109:
    raise RuntimeError(
        f"Expected 109 action plans, found {len(rows)}"
    )

action_plan_ids = [
    str(r["action_plan_id"]).strip()
    for r in rows
]

if len(set(action_plan_ids)) != 109:
    raise RuntimeError("Action-plan IDs are not unique.")

for r in rows:

    if not str(r.get("workers_required", "")).strip():
        raise RuntimeError(
            f"Missing workers_required: {r['action_plan_id']}"
        )

    if not str(r.get("equipment", "")).strip():
        raise RuntimeError(
            f"Missing equipment: {r['action_plan_id']}"
        )

    if not str(r.get("route", "")).strip():
        raise RuntimeError(
            f"Missing route: {r['action_plan_id']}"
        )

sql = []

sql.append("-- ================================================================")
sql.append("-- CIVICBRAIN STEP 13 - LOAD FINAL ACTION PLANS")
sql.append("-- Source: action_plan.csv")
sql.append("-- Action plans: 109")
sql.append("-- ================================================================")
sql.append("")
sql.append("BEGIN;")
sql.append("")

sql.append(
    "TRUNCATE TABLE step13_action_plans;"
)
sql.append("")

for r in rows:

    sql.append(
        "INSERT INTO step13_action_plans ("
        "action_plan_id, "
        "schedule_date, "
        "team_id, "
        "job_count, "
        "jobs, "
        "priority_sum, "
        "priority_avg, "
        "priority_max, "
        "priority_min, "
        "workers_required, "
        "equipment, "
        "prototype_team_equipment, "
        "start_time, "
        "end_time, "
        "service_time_h, "
        "travel_time_h, "
        "total_route_time_h, "
        "distance_km, "
        "estimated_cost, "
        "route, "
        "status"
        ") VALUES ("
        f"{sql_text(r['action_plan_id'])}, "
        f"{sql_text(r['schedule_date'])}, "
        f"{sql_text(r['team_id'])}, "
        f"{sql_num(r['job_count'])}, "
        f"{sql_text(r['jobs'])}, "
        f"{sql_num(r['priority_sum'])}, "
        f"{sql_num(r['priority_avg'])}, "
        f"{sql_num(r['priority_max'])}, "
        f"{sql_num(r['priority_min'])}, "
        f"{sql_num(r['workers_required'])}, "
        f"{sql_text(r['equipment'])}, "
        f"{sql_text(r['prototype_team_equipment'])}, "
        f"{sql_text(r['start_time'])}, "
        f"{sql_text(r['end_time'])}, "
        f"{sql_num(r['service_time_h'])}, "
        f"{sql_num(r['travel_time_h'])}, "
        f"{sql_num(r['total_route_time_h'])}, "
        f"{sql_num(r['distance_km'])}, "
        f"{sql_num(r['estimated_cost'])}, "
        f"{sql_text(r['route'])}, "
        f"{sql_text(r['status'])}"
        ");"
    )

sql.append("")
sql.append("COMMIT;")
sql.append("")

sql.append("-- ================================================================")
sql.append("-- VERIFICATION")
sql.append("-- ================================================================")
sql.append("")

sql.append(
    "SELECT COUNT(*) AS action_plan_count "
    "FROM step13_action_plans;"
)
sql.append("")

sql.append(
    "SELECT "
    "COUNT(DISTINCT action_plan_id) AS unique_action_plans "
    "FROM step13_action_plans;"
)
sql.append("")

sql.append(
    "SELECT "
    "team_id, "
    "COUNT(*) AS action_plan_count, "
    "SUM(job_count) AS job_count, "
    "SUM(distance_km) AS distance_km, "
    "SUM(total_route_time_h) AS route_hours "
    "FROM step13_action_plans "
    "GROUP BY team_id "
    "ORDER BY team_id;"
)
sql.append("")

sql.append(
    "SELECT "
    "status, "
    "COUNT(*) AS action_plan_count "
    "FROM step13_action_plans "
    "GROUP BY status "
    "ORDER BY status;"
)

with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(sql))

print("=" * 80)
print("STEP 13 ACTION PLAN DB LOAD SQL GENERATED")
print("=" * 80)
print(f"Action-plan rows : {len(rows)}")
print(f"Unique IDs       : {len(set(action_plan_ids))}")
print(f"SQL output       : {OUT_FILE}")
print("=" * 80)
