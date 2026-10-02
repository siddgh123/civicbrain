import csv
from pathlib import Path

ROOT = Path(".")
CLUSTER_FILE = ROOT / "data/optimization/clusters/cluster_results.csv"
MEMBER_FILE = ROOT / "data/optimization/clusters/cluster_members.csv"
OUT_FILE = ROOT / "data/optimization/evaluation/load_step13_clusters.sql"


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


with open(CLUSTER_FILE, encoding="utf-8-sig", newline="") as f:
    clusters = list(csv.DictReader(f))

with open(MEMBER_FILE, encoding="utf-8-sig", newline="") as f:
    members = list(csv.DictReader(f))

if len(clusters) != 67:
    raise RuntimeError(
        f"Expected 67 clusters, found {len(clusters)}"
    )

if len(members) != 441:
    raise RuntimeError(
        f"Expected 441 cluster members, found {len(members)}"
    )

sql = []

sql.append("-- ================================================================")
sql.append("-- CIVICBRAIN STEP 13 - LOAD VALIDATED CLUSTER DATA")
sql.append("-- Generated from validated CSV outputs.")
sql.append("-- Existing production tables are not modified.")
sql.append("-- ================================================================")
sql.append("")
sql.append("BEGIN;")
sql.append("")

# Re-runnable prototype load.
sql.append("TRUNCATE TABLE")
sql.append("    step13_cluster_complaint,")
sql.append("    step13_clusters")
sql.append("RESTART IDENTITY;")
sql.append("")

# ------------------------------------------------------------------
# Cluster headers
# ------------------------------------------------------------------

for r in clusters:
    sql.append(
        "INSERT INTO step13_clusters ("
        "cluster_id, "
        "work_type, "
        "complaint_count, "
        "total_service_hours, "
        "max_workers, "
        "required_equipment, "
        "serviceability_status, "
        "required_shift_blocks, "
        "centroid_latitude, "
        "centroid_longitude, "
        "internal_radius_m"
        ") VALUES ("
        f"{sql_text(r['cluster_id'])}, "
        f"{sql_text(r['work_type'])}, "
        f"{sql_num(r['complaint_count'])}, "
        f"{sql_num(r['total_service_duration_hours'])}, "
        f"{sql_num(r['max_workers_required'])}, "
        f"{sql_text(r['required_equipment'])}, "
        f"{sql_text(r['serviceability_status'])}, "
        f"{sql_num(r.get('required_shift_blocks'))}, "
        f"{sql_num(r['centroid_lat'])}, "
        f"{sql_num(r['centroid_lon'])}, "
        f"{sql_num(r['max_internal_distance_m'])}"
        ");"
    )

sql.append("")

# ------------------------------------------------------------------
# Cluster memberships
# ------------------------------------------------------------------

for r in members:
    sql.append(
        "INSERT INTO step13_cluster_complaint ("
        "cluster_id, "
        "job_id"
        ") VALUES ("
        f"{sql_text(r['cluster_id'])}, "
        f"{sql_text(r['job_id'])}"
        ");"
    )

sql.append("")
sql.append("COMMIT;")
sql.append("")

# ------------------------------------------------------------------
# Verification SQL
# ------------------------------------------------------------------

sql.append("-- ================================================================")
sql.append("-- VERIFICATION")
sql.append("-- ================================================================")
sql.append(
    "SELECT COUNT(*) AS cluster_count "
    "FROM step13_clusters;"
)
sql.append("")
sql.append(
    "SELECT COUNT(*) AS cluster_member_count "
    "FROM step13_cluster_complaint;"
)
sql.append("")
sql.append(
    "SELECT "
    "c.serviceability_status, "
    "COUNT(*) AS cluster_count "
    "FROM step13_clusters c "
    "GROUP BY c.serviceability_status "
    "ORDER BY c.serviceability_status;"
)
sql.append("")
sql.append(
    "SELECT "
    "c.work_type, "
    "COUNT(*) AS cluster_count, "
    "SUM(c.complaint_count) AS job_count "
    "FROM step13_clusters c "
    "GROUP BY c.work_type "
    "ORDER BY c.work_type;"
)

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(sql))

print("=" * 80)
print("STEP 13 CLUSTER DB LOAD SQL GENERATED")
print("=" * 80)
print(f"Clusters source rows       : {len(clusters)}")
print(f"Cluster-member source rows : {len(members)}")
print(f"SQL output                 : {OUT_FILE}")
print("=" * 80)
