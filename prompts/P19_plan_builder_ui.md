# P19 — Action plan builder UI
**Day 5 · agent ≈ 2.5 h · human ≈ 5 min · Needs: P15, P18 · Model: Flash, strongest for the map**

## Goal
The officer builds a day plan on screen: filters → generate (progress) → map with numbered stops and straight route
lines → re-order with ▲/▼ (and drag) → save (re-time) → approve → assign an eligible contractor → download the PDF;
cancel where allowed; stale-version dialog.

## Read first
`docs/05_UI_SPEC.md` §5 "Action plan builder" · `docs/04_API_CONTRACT.md` §6 Plans · `docs/12_ERROR_HANDLING.md` §6

## Build
1. `/officer/plans` list (status, date, work type, contractor, jobs) and `/officer/plans/new` builder:
   step 1 filters (date, work type, wards or "use selected complaints" from P15's row selection, contractors to consider) →
   Generate → poll `GET /officer/optimizer-runs/{id}` every 2 s (max 60 s, progress bar, cancel) → for one or more plans:
2. Plan view: `WardMap` with numbered stop markers + straight route polyline (`routeGeoJson`), stop list with ▲/▼ buttons
   (keyboard accessible) and native HTML5 drag-and-drop, Remove, totals (jobs, workers, service h, travel h, km, ₹ with Indian
   grouping), dropped jobs with reasons, version badge, "Save changes" (PUT → re-time → reload), Approve, Assign (dropdown only
   ACTIVE firms registered for the plan's work type, with crew capacity), Download PDF (blob download), Cancel plan.
   `STALE_VERSION` → dialog "Plan changed by someone else — reload"; `PLAN_STATE_CONFLICT` → message + reload.
3. Item rows show the complaint status; an item whose inspection says "issue not found" shows "Remove from plan" (P14 action).

## Tests (write first, Vitest + MSW)
▲ moves a stop up and marks the plan dirty; Save sends the new order with the current version · STALE_VERSION opens the reload
dialog · assign dropdown lists only eligible firms · polling stops at SUCCEEDED and shows dropped jobs.

## Verify (agent)
1. in `frontend`: lint · typecheck · test · build.
2. E2E walkthrough: `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` → smoke `--stage officer` (A and C VERIFIED) →
   browser as `ui.officer`: select A and C → Plan selected → generate → reorder → save → approve → assign "UI Test Road Works" →
   download the PDF. Screenshots `docs/screenshots/P19_generated.png`, `P19_reordered.png`, `P19_assigned.png` →
   `start-all.ps1 -Restart`.

## Ask the human (yes/no)
- Q1. In `P19_generated.png`, are the numbered stops and the route line visible on the ward map?
- Q2. Is the stop list easy to re-order (▲/▼) in `P19_reordered.png`?

## Done when
checks green · walkthrough screenshots committed · pushed.

## Next
Day 6: `/run-prompt P20` — contractor API (≈ 2.5 h, strongest model)
