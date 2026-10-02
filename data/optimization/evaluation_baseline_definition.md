# CivicBrain Step 13 — Evaluation Baseline Definition

## Baseline Name
FIFO Greedy Baseline

## Purpose
Provide a deterministic, reproducible benchmark for comparison with the
travel-aware CivicBrain optimized schedule.

## Input
Canonical Step 13 eligible jobs:

data\optimization\jobs\eligible_jobs.csv

Total eligible jobs:
441

## Job Ordering
1. submitted_at ascending
2. job_id ascending as deterministic tie-breaker

## Team Assignment
Use the validated feasible team assignment for each job.

No new team capability assumptions are introduced.

## Working Calendar
Shift:
08:00–17:00

Shift length:
9 hours

Evaluation horizon:
30 days

## Scheduling Logic
For each team independently:
1. Read jobs in FIFO order.
2. Skip jobs whose service duration exceeds one 9-hour shift.
3. Assign each remaining job to the earliest available schedule position.
4. A team cannot execute overlapping jobs.
5. Jobs remain assigned to their validated feasible team.

## Priority
Step 11 priority is NOT used for baseline ordering.

No new priority formula is created.

## Clustering
Operational clustering is NOT used as a scheduling optimization mechanism.

## Routing
Routes use actual complaint/job coordinates.

Conceptual route:

Depot -> Job -> Job -> ... -> Depot

Cluster centroids are not used as route stops.

## Travel Metrics
Road distance and travel time must use the same OSRM basis and the same
prototype depot configuration used for the optimized result.

## Comparison Metrics
The baseline will be compared with the optimized result on:

- total road distance
- total route/service time
- jobs completed per shift
- total scheduled jobs
- total unscheduled jobs

## Required Edge Cases
The evaluation must report:

- duplicate child
- uncertain complaint
- long-duration job
- missing equipment
- no feasible team
- multiple teams
- standalone job
- high-priority job
- no jobs
- invalid location
- no route
- job scheduled twice
- every eligible job accounted for

## Interpretation Rule
The comparison reports measured results only.

It does not establish that one method is universally better.
