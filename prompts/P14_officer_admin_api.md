# P14 — Officer, admin and contractor-management API (+ all E2E accounts)
**Day 4 · agent ≈ 3 h · human 0 min · Needs: P10, P12 · Model: strongest**

## Goal
Officers see and act on the complaints of their scope (tabs, map data, full detail, reject/merge/unmerge/accept/
restore/remove-from-plan/re-analyse/verify-completion), create contractors (one-time password) and admins create
officers with scopes. The E2E seed creates all 8 fixed accounts + the UI accounts. Smoke stage `officer` passes.

## Read first
`docs/04_API_CONTRACT.md` §6 (complaints, contractors), §8 (officers + scopes) · `docs/03_DATABASE.md` §3–§4
(`v_officer_complaint_queue`, scope tables, status rules, V5 release trigger) · `docs/07_SECURITY.md` §2 ·
`docs/08_TEST_PLAN.md` §2 (fixed accounts and scopes) · `docs/12_ERROR_HANDLING.md` §2–§3 · `tests/smoke/smoke_flow.py` (`stage_officer`)

## Build
1. `GET /officer/complaints` (tabs NEW / NEEDS_REVIEW / IN_PROGRESS / COMPLETED / REJECTED exactly as 04 §6 defines them;
   filters ward, category, work type, priority, authenticity, dates, `includeSynthetic=false`; paging; merged children never
   listed on their own) · `GET /officer/complaints/geojson` (same filters; FeatureCollection) · `GET /officer/complaints/{id}`
   (full detail: images with `displayImageId` = best photo of the group, detections in pixels + image size, measurements AI
   vs contractor, estimate lines, priority factors + explanation, authenticity checks, duplicates/children, timeline,
   inspection, completion) · `GET /officer/stats`.
   **Scope inside every query**: OFFICER sees only complaints matching one of their scope rows (ward and/or work type);
   ADMIN sees all; out of scope → 404.
2. Actions (reason/remarks required; return the updated detail; all through `WorkflowActor`; DB errors mapped by 12 §3):
   reject · merge `{masterComplaintId}` · unmerge · accept (SUBMITTED → VERIFIED when analysis failed/stuck) · restore
   (REJECTED → VERIFIED) · remove-from-plan (SCHEDULED/ASSIGNED/INSPECTED → VERIFIED; V5 trigger frees it) · reanalyze
   (insert ANALYZE_COMPLAINT job, `ON CONFLICT DO NOTHING`, 202) · verify-completion `{approved, remarks}`
   (COMPLETED → CLOSED / REOPENED). Every mutating call writes `audit_logs`.
3. Contractors: `GET/POST /officer/contractors`, `GET/PUT /officer/contractors/{id}`, status, workers (data only),
   equipment. Create = firm + CONTRACTOR user with a one-time password returned ONCE and `must_change_password = true`.
   List items include `id`, `firmName`, `email`, `status`, `workTypes`, `crewCapacity`. Officers create contractors only for
   their work types.
4. Admin: `GET/POST /admin/officers` (create = OFFICER user with a one-time password returned ONCE and
   `must_change_password = true`, like contractors), `PUT /admin/officers/{id}`, `PUT /admin/officers/{id}/scopes`,
   `POST /admin/users/{id}/disable` (revokes tokens).
5. `E2eSeedRunner` now creates all fixed accounts of 08 §2 from `.env.test`: officer.road (scope ROAD, all wards),
   officer.w3 (ward 3, all work types), contractor.patil (firm "Patil Road Works", ROAD), contractor.other (firm
   "Other Water Works", WATER), staff.patil (CONTRACTOR_STAFF of Patil) - plus `ui.officer` (ROAD, all wards) and
   `ui.contractor` (own firm "UI Test Road Works", ROAD) when the `E2E_UI_*` variables exist. TOTP: store the
   `.env.test` TOTP secrets encrypted for officers/admin but keep `app.security.mfa-required=false` (P25 may switch it on).

## Tests (write first)
officer in scope sees the complaint; ward-3 officer → 404 · citizen calling an officer endpoint → 403 · reject → REJECTED +
history + outbox; restore → VERIFIED · verify-completion on a VERIFIED complaint → 409 INVALID_TRANSITION · merge into a
master → child MERGED, master's recipients include the child owner · remove-from-plan frees the complaint (V5) · contractor
create returns the one-time password once, the new user gets 403 PASSWORD_CHANGE_REQUIRED until changed · admin disables an
officer → login refused and existing token rejected.

## Verify (agent)
1. in `backend`: `.\mvnw.cmd -q verify`.
2. E2E smoke (now all accounts): `start-all.ps1 -Stop` → `seed-e2e.ps1` → `start-all.ps1 -E2E` →
   `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage officer` → `SMOKE OFFICER PASSED` → `start-all.ps1 -Restart`.

## Ask the human (yes/no)
- Q1. The smoke run shows the ward-3 officer cannot see a ward-1 complaint and a citizen cannot call officer endpoints. Continue?

## Done when
verify green · `SMOKE OFFICER PASSED` · `seed-e2e.ps1` reports 8 fixed accounts (+ UI accounts) · committed + pushed.

## Next
`/run-prompt P15` — officer portal UI (≈ 3 h)
