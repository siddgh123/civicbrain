# CivicBrain Step 13 — Evaluation Report

## Dataset and Methods

The evaluation uses the canonical Step 13 eligible jobs dataset and compares a deterministic FIFO Greedy Baseline against the travel-aware CivicBrain optimized candidate.

## Core Metrics

| Metric | Baseline | Optimized | Difference |
|---|---:|---:|---:|
| Eligible jobs | 441 | 441 | 0.0 |
| Scheduled jobs | 191 | 238 | 47.0 |
| Unscheduled jobs | 250 | 203 | -47.0 |
| Route groups / active shifts | 110 | 109 | -1.0 |
| Service hours | 772.2 | 839.1 | 66.89999999999998 |
| Travel hours | 38.536 | 38.231251 | -0.30474900000000105 |
| Total route hours | 810.736 | 877.331251 | 66.59525099999996 |
| Total road distance km | 1353.78 | 1285.5256 | -68.25440000000003 |
| Average jobs per active shift | 1.736 | 2.183 | 0.44699999999999984 |
| Route groups <= 9h | 92 | 109 | 17.0 |
| Route groups > 9h | 18 | 0 | -18.0 |

## Route Feasibility

- Baseline routes within 9h: 92/110
- Baseline route violations: 18
- Optimized routes within 9h: 109/109
- Optimized route violations: 0

## Edge Cases

| Edge case | Status | Details |
|---|---|---|
| duplicate_child | PASS | eligible_duplicate_children=0, routed=0 |
| uncertain_complaint | PASS | uncertain_or_review=0, scheduled=0 |
| long_duration_job | PASS | long_jobs=120, scheduled=0 |
| missing_equipment | INFO | jobs_with_missing_required_equipment=0; no synthetic case introduced |
| no_feasible_team | PASS | jobs_without_feasible_team=120, scheduled=0 |
| multiple_teams | INFO | jobs_with_multiple_feasible_teams=0 |
| standalone_job | INFO | Current clustering result has no standalone jobs. |
| high_priority_job | INFO | high_or_critical_eligible=61, optimized_scheduled=19 |
| no_jobs | INFO | No zero-job production group exists in the current non-empty test dataset. |
| invalid_location | PASS | invalid_location_jobs=0, scheduled=0 |
| no_route | PASS | baseline_no_route=0, optimized_no_route=0 |
| job_scheduled_twice | PASS | baseline_duplicates=0, optimized_duplicates=0 |
| every_eligible_job_accounted_for | PASS | baseline=True, optimized=True |

## Interpretation

This report records measured results on the current synthetic prototype test set. It does not establish universal superiority of either method.
