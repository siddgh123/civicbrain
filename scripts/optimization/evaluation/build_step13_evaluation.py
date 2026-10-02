import csv
import json
from pathlib import Path
from collections import Counter

ROOT = Path(".")

EVAL = ROOT / "data/optimization/evaluation"
EVAL.mkdir(parents=True, exist_ok=True)

ELIGIBLE = ROOT / "data/optimization/jobs/eligible_jobs.csv"
FEASIBLE = ROOT / "data/optimization/teams/feasible_team_assignments.csv"
BASELINE_SCHEDULE = EVAL / "baseline_schedule.csv"
BASELINE_UNSCHEDULED = EVAL / "baseline_unscheduled_jobs.csv"
BASELINE_METRICS = EVAL / "baseline_route_metrics.json"
BASELINE_AUDIT = EVAL / "baseline_route_audit.csv"

OPT_SCHEDULE = ROOT / "data/optimization/scheduling/final_step13_schedule_candidate.csv"
OPT_UNSCHEDULED = ROOT / "data/optimization/scheduling/final_step13_unscheduled_jobs.csv"
OPT_SUMMARY = ROOT / "data/optimization/scheduling/final_step13_summary.json"
OPT_AUDIT = ROOT / "data/optimization/routing/final_step13_route_audit.csv"

BASELINE_RESULTS = EVAL / "baseline_results.csv"
OPT_RESULTS = EVAL / "optimization_results.csv"
METRICS_SUMMARY = EVAL / "step13_metrics_summary.csv"
EDGE_CASES = EVAL / "step13_edge_case_validation.csv"
REPORT = EVAL / "step13_evaluation_report.md"


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


eligible = read_csv(ELIGIBLE)
feasible = read_csv(FEASIBLE)

baseline_schedule = read_csv(BASELINE_SCHEDULE)
baseline_unscheduled = read_csv(BASELINE_UNSCHEDULED)
baseline_audit = read_csv(BASELINE_AUDIT)

opt_schedule = read_csv(OPT_SCHEDULE)
opt_unscheduled = read_csv(OPT_UNSCHEDULED)
opt_audit = read_csv(OPT_AUDIT)

with open(BASELINE_METRICS, encoding="utf-8") as f:
    baseline_metrics = json.load(f)

with open(OPT_SUMMARY, encoding="utf-8") as f:
    opt_summary = json.load(f)

eligible_ids = {str(r["job_id"]).strip() for r in eligible}
feasible_ids = {
    str(r["job_id"]).strip()
    for r in feasible
    if str(r.get("overall_feasible", "")).strip().lower() == "true"
}

baseline_ids = [str(r["job_id"]).strip() for r in baseline_schedule]
baseline_unscheduled_ids = [
    str(r["job_id"]).strip()
    for r in baseline_unscheduled
]

opt_ids = [str(r["job_id"]).strip() for r in opt_schedule]
opt_unscheduled_ids = [
    str(r["job_id"]).strip()
    for r in opt_unscheduled
]

# ------------------------------------------------------------------
# Core metrics
# ------------------------------------------------------------------

baseline_route_groups = len(baseline_audit)
opt_route_groups = len(opt_audit)

baseline_pass_groups = sum(
    1 for r in baseline_audit
    if r["status"] == "PASS"
)

baseline_violation_groups = sum(
    1 for r in baseline_audit
    if r["status"] != "PASS"
)

opt_pass_groups = sum(
    1 for r in opt_audit
    if r["status"] == "PASS"
)

opt_violation_groups = sum(
    1 for r in opt_audit
    if r["status"] != "PASS"
)

baseline = {
    "method": "FIFO_Greedy_Baseline",
    "eligible_jobs": len(eligible),
    "scheduled_jobs": len(baseline_schedule),
    "unscheduled_jobs": len(baseline_unscheduled),
    "route_groups": baseline_route_groups,
    "service_hours": float(baseline_metrics["service_hours"]),
    "travel_hours": float(baseline_metrics["travel_hours"]),
    "total_route_hours": float(baseline_metrics["total_route_hours"]),
    "total_distance_km": float(baseline_metrics["total_distance_km"]),
    "average_jobs_per_shift": float(
        baseline_metrics["jobs_per_shift_average"]
    ),
    "route_groups_pass": baseline_pass_groups,
    "route_groups_violation": baseline_violation_groups,
}

optimized = {
    "method": "CivicBrain_Travel_Aware_Optimized",
    "eligible_jobs": int(opt_summary["eligible_jobs"]),
    "scheduled_jobs": int(opt_summary["scheduled_jobs"]),
    "unscheduled_jobs": int(opt_summary["unscheduled_jobs"]),
    "route_groups": int(opt_summary["route_groups"]),
    "service_hours": float(opt_summary["total_service_hours"]),
    "travel_hours": float(opt_summary["total_travel_hours"]),
    "total_route_hours": float(opt_summary["total_route_hours"]),
    "total_distance_km": float(opt_summary["total_distance_km"]),
    "average_jobs_per_shift": round(
        int(opt_summary["scheduled_jobs"])
        / int(opt_summary["route_groups"]),
        3
    ),
    "route_groups_pass": opt_pass_groups,
    "route_groups_violation": opt_violation_groups,
}

# ------------------------------------------------------------------
# Save baseline_results.csv and optimization_results.csv
# ------------------------------------------------------------------

result_fields = [
    "method",
    "eligible_jobs",
    "scheduled_jobs",
    "unscheduled_jobs",
    "route_groups",
    "service_hours",
    "travel_hours",
    "total_route_hours",
    "total_distance_km",
    "average_jobs_per_shift",
    "route_groups_pass",
    "route_groups_violation",
]

write_csv(
    BASELINE_RESULTS,
    [baseline],
    result_fields,
)

write_csv(
    OPT_RESULTS,
    [optimized],
    result_fields,
)

# ------------------------------------------------------------------
# Metric comparison
# ------------------------------------------------------------------

metric_rows = []

comparison_metrics = [
    ("eligible_jobs", "Eligible jobs"),
    ("scheduled_jobs", "Scheduled jobs"),
    ("unscheduled_jobs", "Unscheduled jobs"),
    ("route_groups", "Route groups / active shifts"),
    ("service_hours", "Service hours"),
    ("travel_hours", "Travel hours"),
    ("total_route_hours", "Total route hours"),
    ("total_distance_km", "Total road distance km"),
    ("average_jobs_per_shift", "Average jobs per active shift"),
    ("route_groups_pass", "Route groups <= 9h"),
    ("route_groups_violation", "Route groups > 9h"),
]

for key, label in comparison_metrics:
    b = baseline[key]
    o = optimized[key]

    try:
        delta = float(o) - float(b)
    except Exception:
        delta = ""

    metric_rows.append({
        "metric": label,
        "baseline": b,
        "optimized": o,
        "optimized_minus_baseline": delta,
    })

write_csv(
    METRICS_SUMMARY,
    metric_rows,
    [
        "metric",
        "baseline",
        "optimized",
        "optimized_minus_baseline",
    ],
)

# ------------------------------------------------------------------
# Edge-case validation
# ------------------------------------------------------------------

job_by_id = {
    str(r["job_id"]).strip(): r
    for r in eligible
}

checks = []


def add_edge(name, status, details):
    checks.append({
        "edge_case": name,
        "status": status,
        "details": details,
    })


# 1. Duplicate child
duplicate_children = [
    r for r in eligible
    if str(r.get("is_duplicate_child", "")).strip().lower() == "true"
]

dup_scheduled = [
    r["job_id"]
    for r in duplicate_children
    if r["job_id"] in set(baseline_ids) or r["job_id"] in set(opt_ids)
]

add_edge(
    "duplicate_child",
    "PASS" if not dup_scheduled else "FAIL",
    f"eligible_duplicate_children={len(duplicate_children)}, routed={len(dup_scheduled)}"
)

# 2. Uncertain complaint
uncertain_rows = [
    r for r in eligible
    if str(r.get("duplicate_status", "")).strip().upper() == "UNCERTAIN"
    or str(r.get("review_required", "")).strip().lower() == "true"
]

uncertain_scheduled = [
    r["job_id"]
    for r in uncertain_rows
    if r["job_id"] in set(baseline_ids)
    or r["job_id"] in set(opt_ids)
]

add_edge(
    "uncertain_complaint",
    "PASS" if not uncertain_scheduled else "FAIL",
    f"uncertain_or_review={len(uncertain_rows)}, scheduled={len(uncertain_scheduled)}"
)

# 3. Long-duration job
long_jobs = [
    r for r in eligible
    if float(r["service_duration_hours"]) > 9
]

long_scheduled = [
    r["job_id"]
    for r in long_jobs
    if r["job_id"] in set(baseline_ids)
    or r["job_id"] in set(opt_ids)
]

add_edge(
    "long_duration_job",
    "PASS" if not long_scheduled else "FAIL",
    f"long_jobs={len(long_jobs)}, scheduled={len(long_scheduled)}"
)

# 4. Missing equipment
missing_equipment_rows = [
    r for r in eligible
    if not str(r.get("required_equipment", "")).strip()
]

add_edge(
    "missing_equipment",
    "INFO",
    f"jobs_with_missing_required_equipment={len(missing_equipment_rows)}; no synthetic case introduced"
)

# 5. No feasible team
no_feasible = eligible_ids - feasible_ids

scheduled_no_feasible = [
    jid for jid in (set(baseline_ids) | set(opt_ids))
    if jid in no_feasible
]

add_edge(
    "no_feasible_team",
    "PASS" if not scheduled_no_feasible else "FAIL",
    f"jobs_without_feasible_team={len(no_feasible)}, scheduled={len(scheduled_no_feasible)}"
)

# 6. Multiple teams
team_by_job = {}
for r in feasible:
    if str(r.get("overall_feasible", "")).strip().lower() != "true":
        continue
    team_by_job.setdefault(r["job_id"], set()).add(r["team_id"])

multiple_team_jobs = [
    jid for jid, teams in team_by_job.items()
    if len(teams) > 1
]

add_edge(
    "multiple_teams",
    "INFO",
    f"jobs_with_multiple_feasible_teams={len(multiple_team_jobs)}"
)

# 7. Standalone job
add_edge(
    "standalone_job",
    "INFO",
    "Current clustering result has no standalone jobs."
)

# 8. High-priority job
high_priority_jobs = [
    r for r in eligible
    if str(r.get("priority_level", "")).strip().upper()
    in {"HIGH", "CRITICAL"}
]

high_opt = [
    r["job_id"] for r in high_priority_jobs
    if r["job_id"] in set(opt_ids)
]

add_edge(
    "high_priority_job",
    "INFO",
    f"high_or_critical_eligible={len(high_priority_jobs)}, optimized_scheduled={len(high_opt)}"
)

# 9. No jobs
add_edge(
    "no_jobs",
    "INFO",
    "No zero-job production group exists in the current non-empty test dataset."
)

# 10. Invalid location
invalid_locations = [
    r for r in eligible
    if str(r.get("location_valid", "")).strip().lower() != "true"
]

invalid_scheduled = [
    r["job_id"]
    for r in invalid_locations
    if r["job_id"] in set(baseline_ids)
    or r["job_id"] in set(opt_ids)
]

add_edge(
    "invalid_location",
    "PASS" if not invalid_scheduled else "FAIL",
    f"invalid_location_jobs={len(invalid_locations)}, scheduled={len(invalid_scheduled)}"
)

# 11. No route
baseline_no_route = [
    r for r in baseline_audit
    if r["status"] not in {"PASS", "ROUTE_SHIFT_VIOLATION"}
]

opt_no_route = [
    r for r in opt_audit
    if r["status"] not in {"PASS", "ROUTE_SHIFT_VIOLATION"}
]

add_edge(
    "no_route",
    "PASS" if not baseline_no_route and not opt_no_route else "FAIL",
    f"baseline_no_route={len(baseline_no_route)}, optimized_no_route={len(opt_no_route)}"
)

# 12. Job scheduled twice
baseline_duplicates = [
    jid for jid, count in Counter(baseline_ids).items()
    if count > 1
]

optimized_duplicates = [
    jid for jid, count in Counter(opt_ids).items()
    if count > 1
]

add_edge(
    "job_scheduled_twice",
    "PASS"
    if not baseline_duplicates and not optimized_duplicates
    else "FAIL",
    f"baseline_duplicates={len(baseline_duplicates)}, optimized_duplicates={len(optimized_duplicates)}"
)

# 13. Every eligible job accounted for
baseline_accounted = (
    set(baseline_ids)
    | set(baseline_unscheduled_ids)
) == eligible_ids and (
    set(baseline_ids).isdisjoint(set(baseline_unscheduled_ids))
)

optimized_accounted = (
    set(opt_ids)
    | set(opt_unscheduled_ids)
) == eligible_ids and (
    set(opt_ids).isdisjoint(set(opt_unscheduled_ids))
)

add_edge(
    "every_eligible_job_accounted_for",
    "PASS" if baseline_accounted and optimized_accounted else "FAIL",
    f"baseline={baseline_accounted}, optimized={optimized_accounted}"
)

write_csv(
    EDGE_CASES,
    checks,
    ["edge_case", "status", "details"],
)

# ------------------------------------------------------------------
# Evaluation report
# ------------------------------------------------------------------

with open(REPORT, "w", encoding="utf-8") as f:

    f.write("# CivicBrain Step 13 — Evaluation Report\n\n")

    f.write("## Dataset and Methods\n\n")
    f.write(
        "The evaluation uses the canonical Step 13 eligible jobs dataset "
        "and compares a deterministic FIFO Greedy Baseline against the "
        "travel-aware CivicBrain optimized candidate.\n\n"
    )

    f.write("## Core Metrics\n\n")
    f.write(
        "| Metric | Baseline | Optimized | Difference |\n"
        "|---|---:|---:|---:|\n"
    )

    for row in metric_rows:
        f.write(
            f"| {row['metric']} | {row['baseline']} | "
            f"{row['optimized']} | {row['optimized_minus_baseline']} |\n"
        )

    f.write("\n## Route Feasibility\n\n")
    f.write(
        f"- Baseline routes within 9h: {baseline_pass_groups}/{baseline_route_groups}\n"
        f"- Baseline route violations: {baseline_violation_groups}\n"
        f"- Optimized routes within 9h: {opt_pass_groups}/{opt_route_groups}\n"
        f"- Optimized route violations: {opt_violation_groups}\n\n"
    )

    f.write("## Edge Cases\n\n")
    f.write("| Edge case | Status | Details |\n")
    f.write("|---|---|---|\n")

    for row in checks:
        details = row["details"].replace("|", "/")
        f.write(
            f"| {row['edge_case']} | {row['status']} | {details} |\n"
        )

    f.write("\n## Interpretation\n\n")
    f.write(
        "This report records measured results on the current synthetic "
        "prototype test set. It does not establish universal superiority "
        "of either method.\n"
    )

# ------------------------------------------------------------------
# Final console output
# ------------------------------------------------------------------

failed_edges = [
    r for r in checks
    if r["status"] == "FAIL"
]

print("=" * 80)
print("CIVICBRAIN STEP 13 - FINAL EVALUATION")
print("=" * 80)

print()
print("CORE METRICS")
print("-" * 80)

for row in metric_rows:
    print(
        f"{row['metric']:35s} "
        f"Baseline={row['baseline']}  "
        f"Optimized={row['optimized']}  "
        f"Delta={row['optimized_minus_baseline']}"
    )

print()
print("ROUTE FEASIBILITY")
print("-" * 80)
print(
    f"Baseline  : {baseline_pass_groups}/{baseline_route_groups} within 9h"
)
print(
    f"Optimized : {opt_pass_groups}/{opt_route_groups} within 9h"
)

print()
print("EDGE CASES")
print("-" * 80)

for row in checks:
    print(
        f"{row['edge_case']:35s} {row['status']}"
    )

print()
print("OUTPUTS")
print("-" * 80)
print("Baseline results      :", BASELINE_RESULTS)
print("Optimized results     :", OPT_RESULTS)
print("Metrics summary       :", METRICS_SUMMARY)
print("Edge-case validation  :", EDGE_CASES)
print("Evaluation report     :", REPORT)

print()
print("OVERALL EVALUATION STATUS :", "PASS" if not failed_edges else "FAIL")
print("=" * 80)

if failed_edges:
    raise RuntimeError(
        f"Evaluation has {len(failed_edges)} failed edge-case checks."
    )
