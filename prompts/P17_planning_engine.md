# P17 — Planning engine (OPTIMIZE_PLAN with straight-line travel times)
**Day 5 · agent ≈ 2.5 h · human 0 min · Needs: P12 · Model: strongest**

## Goal
The worker turns an optimizer run into DRAFT action plans: FROZEN grouping with `fn_cluster_jobs` (same work type,
≤ 2 km, ≤ 10 jobs), an OR-Tools one-crew day from depot D001 within 08:00–17:00, straight-line travel times
(`ROUTING_MODE=haversine`), dropped jobs with reasons, and RETIME with the officer's order.

## Read first
`docs/06_AI_PIPELINE.md` §3 (all 8 steps) and the MVP note at its top · `.agents/rules/02-frozen-rules.md` (grouping, depot) ·
`docs/03_DATABASE.md` §3–§4 (`optimizer_runs`, `action_plans`, items, revisions, `fn_cluster_jobs`) ·
`scripts/optimization/routing/*.py` if `docs/INVENTORY.md` lists it (the validated Step 13 OR-Tools code - reuse its settings;
if it is missing, 06 §3 alone is enough)

## Build
1. `optimizer/haversine.py`: matrix of minutes = great-circle km × 1.3 (detour factor, ASSUMPTION) / 20 km/h × 60, rounded
   to whole minutes; distance matrix in metres; route geometry = straight LineString depot → stops → depot.
   `optimizer/osrm.py` keeps the Phase-2 interface (`ROUTING_MODE=osrm`) but is not used.
2. `optimizer/cluster.py`: selection of 06 §3 step 1 (VERIFIED/REOPENED, work type, wards or ids, `current_action_plan_id IS NULL`,
   current estimate required → else dropped "no estimate") → `fn_cluster_jobs(ids, 2000, 10)`.
3. `optimizer/routing.py`: OR-Tools RoutingModel, one vehicle, time dimension horizon 540 min, service time = estimate hours × 60,
   `AddDisjunction([node], 100000 + priority_score × 1000)`, PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH, `time_limit.seconds = 10`,
   deterministic: besides the 10 s time limit set a `solution_limit` (e.g. 200) so the same input always gives the same
   plan (a pure time limit is not reproducible); job > 540 min alone → dropped "Work longer than one shift".
4. `optimizer/plan_writer.py`: one DRAFT `action_plans` row per group with ≥ 1 job (`plan_code` `AP-YYYYMMDD-<WT>-NNN`), items with
   sequence, planned start/end (Asia/Kolkata local `timestamp without time zone`), travel minutes/metres, totals (workers = max of
   items), revision 1 snapshot (matrix hash, `routing_mode: haversine`, solver params), `route_geojson`; run → SUCCEEDED with
   `actionPlanIds` and `dropped_jobs` [{complaintId, publicRef, reason}]; on error → FAILED with a readable message.
5. RETIME (`request.mode = 'RETIME'`, `actionPlanId`, `items` order): keep the given order, recompute times/travel/route/totals,
   new revision (version + 1).
6. Handler `OPTIMIZE_PLAN` replaces the P02 placeholder (timeout 60 s).

## Tests (write first)
fixture of 12 jobs with fixed coordinates/service times → the same plan twice (deterministic) · no stop ends after 17:00 ·
every job planned or dropped with a reason · a 10-h job is dropped with "Work longer than one shift" · haversine: two points
1 km apart → 1.3 km road ≈ 3.9 → 4 min · RETIME keeps the order and bumps the version · integration (`civicbrain_test`): a
GENERATE run for 3 VERIFIED ROAD complaints writes 1 DRAFT plan with 3 items and revision 1.

## Verify (agent)
ruff + pytest in `ai-service` · `start-all.ps1 -Only worker -Restart` → worker log shows the 4 job types registered.

## Ask the human (yes/no)
- Q1. Planning uses straight-line distance × 1.3 at 20 km/h (stated as an assumption in the report; OSRM road times are Phase 2). OK?

## Done when
tests green · committed + pushed. (The end-to-end plan flow is checked by the smoke `plan` stage in P18.)

## Next
`/run-prompt P18` — plan API + PDF + assignment messages (≈ 3 h, strongest model)
