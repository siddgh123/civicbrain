# P20 — Contractor API (inspection, start, completion with proof)
**Day 6 (Tue 6 Oct) · agent ≈ 2.5 h · human 0 min · Needs: P18 · Model: strongest**

## Goal
A contractor sees the firm's worklist and stops, records an inspection with tape values + photo + GPS, starts work and
uploads 1–3 proof photos; the officer gets COMPLETION_SUBMITTED; the plan becomes IN_PROGRESS / COMPLETED by itself.
Smoke stage `contractor` passes.

## Read first
`docs/04_API_CONTRACT.md` §7 and the plan lifecycle in §6 · `docs/02_ARCHITECTURE.md` §5 rule 3 · `docs/07_SECURITY.md` §2–§3 ·
`docs/03_DATABASE.md` §3 (`v_contractor_worklist`, inspections, completions, status rules) · `tests/smoke/smoke_flow.py` (`stage_contractor`)

## Build
1. Access rule (one reusable query/guard): the complaint has an ACTIVE item in an ASSIGNED/IN_PROGRESS plan of the caller's firm
   (CONTRACTOR = the firm's user, CONTRACTOR_STAFF = staff of that firm); anything else → 404.
2. `GET /contractor/worklist?date=` (from `v_contractor_worklist`) · `GET /contractor/plans/{id}` · `GET /contractor/complaints/{id}`
   (photo ids, description, landmark, location, category, planned times - **no citizen name/e-mail/phone**).
3. `POST /contractor/capture-sessions` (same rules as citizen sessions).
4. `POST /contractor/complaints/{id}/inspection` multipart `data {issueConfirmed, findings, lengthM?, widthM?, depthM?,
   expectedCompletionDate, latitude, longitude, accuracyM, captureSessionId}` + `photos` 1–3 (same photo pipeline as P10: magic
   bytes, size, re-encode, storage, sha256; role INSPECTION) → contractor measurement row (source CONTRACTOR, MANUAL_TAPE,
   MEASURED_ON_SITE) + `estimate_source` CONTRACTOR_INSPECTION when tape values exist; distance from the complaint > 100 m →
   saved with a warning flag; complaint → INSPECTED (even when `issueConfirmed=false`; the officer decides); plan → IN_PROGRESS
   at the first inspection. 201.
5. `POST …/start` → IN_PROGRESS (200). `POST …/completion` multipart `data {workSummary, actualWorkers, actualHours, actualCost?,
   materialsUsed[], latitude, longitude, accuracyM, captureSessionId}` + `photos` 1–3 (role COMPLETION_PROOF) → COMPLETED;
   COMPLETION_SUBMITTED outbox row to the plan's `assigned_by_user_id` in the same transaction; plan → COMPLETED when every ACTIVE
   item's complaint is COMPLETED/CLOSED. 201.
6. Rate limits and audit like the citizen endpoints. ANALYZE_IMAGE (reuse check) is Phase 2 - do not enqueue it.

## Tests (write first)
other firm → 404 on detail/inspection/start/completion · staff of the same firm allowed · response has no citizen contact data ·
inspection 240 m away → saved with warning flag · inspection → INSPECTED + plan IN_PROGRESS · start → IN_PROGRESS · completion →
COMPLETED + officer outbox row + plan COMPLETED when it was the last item · completion with 0 or 4 photos → 400 · wrong status
order (completion before start) → 409 INVALID_TRANSITION.

## Verify (agent)
1. in `backend`: `.\mvnw.cmd -q verify`.
2. E2E smoke: `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage contractor` → `SMOKE CONTRACTOR PASSED` → `start-all.ps1 -Restart`.

## Ask the human (yes/no)
- Q1. In Mailpit, did officer.road@test.local get "completion proof submitted for CB-…", and did citizen1 get the INSPECTED / work started / completed mails?

## Done when
verify green · `SMOKE CONTRACTOR PASSED` · committed + pushed. **Feature freeze for the backend after P23.**

## Next
`/run-prompt P21` — AI polish + message details (≈ 1.5 h)
