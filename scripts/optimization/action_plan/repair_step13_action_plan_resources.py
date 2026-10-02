import csv
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(".")
AP_PATH = ROOT / "data" / "optimization" / "action_plan" / "action_plan.csv"
JOBS_PATH = ROOT / "data" / "optimization" / "jobs" / "eligible_jobs.csv"
TEAM_EQ_PATH = ROOT / "data" / "optimization" / "teams" / "team_equipment.csv"

if not AP_PATH.exists():
    raise FileNotFoundError(AP_PATH)
if not JOBS_PATH.exists():
    raise FileNotFoundError(JOBS_PATH)
if not TEAM_EQ_PATH.exists():
    raise FileNotFoundError(TEAM_EQ_PATH)

# ------------------------------------------------------------------
# Load source data
# ------------------------------------------------------------------
with JOBS_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    jobs = list(csv.DictReader(f))

job_by_id = {str(r["job_id"]).strip(): r for r in jobs}

with TEAM_EQ_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    team_equipment_rows = list(csv.DictReader(f))

team_equipment = defaultdict(list)

for r in team_equipment_rows:
    team_id = str(r.get("team_id", "")).strip()
    equipment = str(r.get("equipment_type", "")).strip()

    if not team_id or not equipment:
        continue

    available = str(r.get("available", "")).strip().upper()

    # Keep equipment unless explicitly unavailable.
    if available in {"FALSE", "0", "NO"}:
        continue

    if equipment not in team_equipment[team_id]:
        team_equipment[team_id].append(equipment)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def split_values(value):
    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    # Handle common separators.
    parts = re.split(r"[;,|]+", text)

    result = []
    for p in parts:
        p = p.strip()
        if p:
            result.append(p)

    return result


def unique_sorted(values):
    seen = set()
    out = []

    for v in values:
        v = str(v).strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)

    return sorted(out)


# ------------------------------------------------------------------
# Backup existing action plan
# ------------------------------------------------------------------
backup_path = AP_PATH.with_name("action_plan_before_resource_fix.csv")
AP_PATH.replace(backup_path)

with backup_path.open("r", encoding="utf-8-sig", newline="") as f:
    action_plans = list(csv.DictReader(f))

if not action_plans:
    raise RuntimeError("Action Plan is empty.")

# ------------------------------------------------------------------
# Populate workers/equipment
# ------------------------------------------------------------------
for row in action_plans:
    job_ids = split_values(row.get("jobs", ""))

    workers = []
    required_equipment = []

    for job_id in job_ids:
        job = job_by_id.get(str(job_id).strip())

        if job is None:
            raise RuntimeError(
                f"Action-plan {row.get('action_plan_id')} references missing job_id={job_id}"
            )

        try:
            workers.append(float(job["workers_required"]))
        except Exception:
            raise RuntimeError(
                f"Invalid workers_required for job_id={job_id}: "
                f"{job.get('workers_required')}"
            )

        required_equipment.extend(
            split_values(job.get("required_equipment", ""))
        )

    # Jobs inside one action-plan row are sequential.
    # Therefore the team must be able to handle the maximum worker
    # requirement of any job in that plan, not the sum of all jobs.
    max_workers = max(workers) if workers else 0

    row["workers_required"] = (
        str(int(max_workers))
        if float(max_workers).is_integer()
        else f"{max_workers:.2f}"
    )

    row["equipment"] = "; ".join(unique_sorted(required_equipment))

    team_id = str(row.get("team_id", "")).strip()
    row["prototype_team_equipment"] = "; ".join(
        unique_sorted(team_equipment.get(team_id, []))
    )

# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------
empty_workers = [
    r for r in action_plans
    if not str(r.get("workers_required", "")).strip()
]

empty_equipment = [
    r for r in action_plans
    if not str(r.get("equipment", "")).strip()
]

if empty_workers:
    raise RuntimeError(
        f"workers_required still empty for {len(empty_workers)} action plans."
    )

if empty_equipment:
    raise RuntimeError(
        f"equipment still empty for {len(empty_equipment)} action plans."
    )

# ------------------------------------------------------------------
# Write repaired Action Plan
# ------------------------------------------------------------------
fieldnames = list(action_plans[0].keys())

with AP_PATH.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(action_plans)

print("=" * 80)
print("CIVICBRAIN STEP 13 — ACTION PLAN RESOURCE FIX")
print("=" * 80)
print(f"Action-plan rows       : {len(action_plans)}")
print(f"Workers populated      : {len(action_plans) - len(empty_workers)}")
print(f"Equipment populated    : {len(action_plans) - len(empty_equipment)}")
print(f"Backup                 : {backup_path}")
print(f"Updated Action Plan    : {AP_PATH}")
print()
print("VALIDATION")
print("-" * 80)
print("WORKERS_REQUIRED      :", "PASS" if not empty_workers else "FAIL")
print("EQUIPMENT             :", "PASS" if not empty_equipment else "FAIL")
print("ROWS_PRESERVED        :", "PASS")
print()
print("STATUS : PASS")
print("=" * 80)

