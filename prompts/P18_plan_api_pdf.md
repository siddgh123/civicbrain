# P18 — Plan API, PDF export, assignment messages
**Day 5 · agent ≈ 3 h · human 0 min · Needs: P14, P17 · Model: strongest**

## Goal
Officers generate, view, re-order (re-time), approve, assign and cancel action plans through the API; the PDF downloads;
on assignment every owner (incl. merged children) gets "Contractor X assigned, date D" and the contractor gets
ACTION_PLAN_ASSIGNED. Smoke stage `plan` passes.

## Read first
`docs/04_API_CONTRACT.md` §6 (Plans + plan lifecycle) · `docs/12_ERROR_HANDLING.md` §2–§3 (P0001 prefixes, STALE_VERSION,
PLAN_STATE_CONFLICT, CONTRACTOR_NOT_ELIGIBLE, COMPLAINT_NOT_PLANNABLE) · `docs/02_ARCHITECTURE.md` §5 rules 2 and 6 ·
`docs/03_DATABASE.md` §4 (`fn_approve_action_plan`, `fn_assign_action_plan`) · `tests/smoke/smoke_flow.py` (`stage_plan`)

## Build
1. `POST /officer/plans/generate` → `optimizer_runs` row QUEUED (trigger enqueues the job) → 202 `{runId}` ·
   `GET /officer/optimizer-runs/{runId}` → `{status, actionPlanIds, droppedJobs, error?}` · `GET /officer/plans` ·
   `GET /officer/plans/{id}` (shape of 04 §6 incl. `version`, `planCode`, `totals`, `items` with `complaintId`, `publicRef`,
   `sequenceNo`, times, `lat`, `lon`; `routeGeoJson`; `revisions`).
2. `PUT /officer/plans/{id} {version, plannedDate, items, notes}` → RETIME run, 202 `{runId}`; old version → 409 STALE_VERSION;
   not DRAFT → 409 PLAN_STATE_CONFLICT.
3. `POST …/approve` (`fn_approve_action_plan`; complaints → SCHEDULED) · `POST …/assign {contractorId}` (`fn_assign_action_plan`;
   complaints → ASSIGNED; wrong work type / inactive → 422 CONTRACTOR_NOT_ELIGIBLE) · `POST …/cancel {reason}` (rules of 04 §6:
   only DRAFT/APPROVED/ASSIGNED; ACTIVE items' complaints back to VERIFIED in the same transaction; work started → 409).
   Map every P0001 message prefix to its code (12 §3). Plan lifecycle helper: IN_PROGRESS at the first INSPECTED item,
   COMPLETED when every ACTIVE item's complaint is COMPLETED/CLOSED, CANCELLED when all items are REMOVED - re-checked after every
   status change of an item's complaint (used fully in P20/P23).
4. Notifications: the ASSIGNED status rows come from the DB trigger (recipients incl. merged children) and
   `fn_assign_action_plan` itself inserts the ACTION_PLAN_ASSIGNED outbox row (`db/V2__civicbrain_app_layer.sql`, do NOT add a
   second one); the dispatcher sends it to the firm's contractor user (02 §5 rule 2); placeholders `contractor_name` (firm name), `planned_date`, `plan_code`, `job_count`, `plan_url`.
5. `GET /officer/plans/{id}/export.pdf?version=` (OpenPDF): header (plan code, date, work type, contractor, version, totals),
   stop table (sequence, CB number, category, ward, landmark, planned start/end, est. workers, est. cost), a simple straight-line
   route sketch (cut list item 2: drop the sketch first if short of time), "AI estimates are preliminary" note.
   Officers only (in scope); `Content-Disposition: attachment; filename=<planCode>.pdf`.

## Tests (write first)
Backend IT (insert a DRAFT plan as the worker would): approve → SCHEDULED · assign wrong-work-type firm → 422 · assign → ASSIGNED +
outbox rows (status rows for citizen + merged child owner, exactly ONE ACTION_PLAN_ASSIGNED row) · stale version → 409 · edit non-DRAFT → 409 PLAN_STATE_CONFLICT · cancel
ASSIGNED → complaints VERIFIED and plannable · PDF: content-type, non-empty, plan code inside (PDF text extraction) · officer of
another scope → 404.

## Verify (agent)
1. in `backend`: `.\mvnw.cmd -q verify`.
2. E2E smoke: `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage plan` → `SMOKE PLAN PASSED` → `start-all.ps1 -Restart`.
3. Save one generated PDF to `docs/screenshots/P18_plan.pdf` (from the smoke's plan via the browser as `ui.officer`, or a test output).

## Ask the human (yes/no)
- Q1. Open `docs/screenshots/P18_plan.pdf` - is the plan readable (stops in order, times, contractor, totals)?
- Q2. In Mailpit, does citizen1's mail say "contractor <firm> has been assigned … Planned date …"?

## Done when
verify green · `SMOKE PLAN PASSED` · PDF checked · committed + pushed.

## Next
`/run-prompt P19` — plan builder UI (≈ 2.5 h)
