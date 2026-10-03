# PROGRESS — CivicBrain build log

The agent updates this file in the same commit as every task. Humans approve each phase gate here.

## Current plan: 7-DAY MVP (`docs/09_BUILD_PLAN_7DAY.md`), 1–7 Oct 2026
| Day | Date | Gate (from §5) | Status | Evidence / bugs | Approved by |
|---|---|---|---|---|---|
| D1 | Thu 1 Oct | build laptop ready, backend + Flyway + seed, Vite layout, worker claims a job, YOLO training started, CI green | PASSED (human yes 2026-10-03 12:12; tag `d1-done`) | check-env all required PASS (8 WARN) · `verify-all.ps1 -SkipE2E` GREEN (SQL 7/7, 6/6, 11/11, 11/11 · backend 70 + 13 IT 0 failures incl. SchemaIT 74 tables + ward 1 · AI ruff clean, 82 passed · frontend lint/typecheck, 39 passed) · frontend build OK · Flyway v5 on `civicbrain`, 23 wards, seed 500 · dataset check exit 0 · Kaggle run committed · CI green incl. full-history gitleaks (human yes) · SCRIPT FIX `verify-all`/`start-backend`/`seed-e2e` `[NullString]::Value` (Task log "D1 gate") · commit b0a5f43 | human (yes 2026-10-03 12:12) |
| D2 | Fri 2 Oct | register → OTP → login, admin exists, priority 0 mismatches, duplicates test, YOLO ONNX detects | PASSED (human yes 2026-10-03 19:47; tag `d2-done`) | `verify-all.ps1 -SkipE2E` GREEN (SQL 7/7, 6/6, 11/11, 11/11 · backend 124 + 46 IT 0 failures · AI ruff clean, 311 passed · frontend lint/typecheck, 69 passed; log `logs/verify-all_20261003_193442.txt`) · fresh E2E seed → **`SMOKE AUTH PASSED: 19 / 19`** · browser walkthrough P07 (register → Mailpit OTP → verify → login → logout) `1 passed` + P07 human yes · YOLO installed (`/health` 3 models "ok"), 4/4 fixtures find their own class, `yolo_metrics.json` mAP50 0.607 (existing test split) · classifier sanity acc 0.90 / macro-F1 0.8995 · `PRIORITY GOLDEN: 500 rows checked, 0 mismatches` · duplicates repro 3 pairs · `models` tests 12 passed 0 skipped · first admin: bootstrap IT green, real admin in P24 (P06 prompt) · Task log "D2 gate" · commit 7bb904a | human (yes 2026-10-03 19:47) |
| D3 | Sat 3 Oct | phone capture → submit → "Under review" < 60 s, SUBMITTED mail, duplicate → Linked | NOT STARTED | | |
| D4 | Sun 4 Oct | officer map/detail/actions, contractor created, WhatsApp sandbox, optimizer test | NOT STARTED | | |
| D5 | Mon 5 Oct | plan generate → reorder → approve → assign → "Contractor X assigned" to all owners, PDF; feature freeze | NOT STARTED | | |
| D6 | Tue 6 Oct | complete flow to CLOSED + rating on demo laptop with 2 phones, all mails | NOT STARTED | | |
| D7 | Wed 7 Oct | flow twice without error, `mvp-v1` tag, backup on USB | NOT STARTED | | |

## Autopilot log (single laptop, `/run-prompt P<nn>`)
Status values: NOT STARTED · IN PROGRESS · BLOCKED · DONE (human yes <date time>). The agent adds a detailed entry per prompt under "Task log".

| Prompt | What | Day | Status | Evidence (smoke / tests) |
|---|---|---|---|---|
| P01 | Repo, environment check, databases | D1 | DONE (human yes 2026-10-02) | check-env 0 FAIL (13 WARN) · SQL tests 4/4 (7/7, 6/6, 11/11, 11/11) · AGENT_CAN_START=yes · INVENTORY written · commit 6c2481e |
| P02 | AI service skeleton + venv + worker loop | D1 | DONE (human yes 2026-10-02 19:45) | ruff clean · pytest 82 passed ×5 (14 integration on civicbrain_test) · worker alive, waits for schema (dev DB empty until P04) · /health 503 "schema missing" · V4 claim over-claim found + handled (V6 fix = Phase 2) · commit f0575ee |
| P03 | Dataset check + fixtures + Kaggle package (YOLO training starts) | D1 | DONE (human yes 2026-10-02 20:29) | dataset check exit 0 (0 label problems, 0 leakage, 3,258 train lines) · 6 fixtures + README · zip 6,802 files / 174.6 MB · ruff clean · pytest 82 passed · Kaggle cells 1-4 OK, 0.9 min/epoch, committed run "Running" (finish ≈ 22:30 at the latest) · commit 8141812 |
| P03b | Fallback: auto-label (only if labels are missing) | D1 | NOT STARTED | |
| P04 | Backend skeleton + Flyway + demo seed | D2 | DONE (human yes 2026-10-03 10:24) | mvnw verify 83 tests 0 failures (70 unit + 13 IT on Testcontainers PostGIS) · Flyway "Successfully applied 6 migrations" on `civicbrain` · `DB check: 23 wards visible to civicbrain_app` · seed complaints=500, wards=23 · SQL tests 4/4 · AI /health 200 db ok |
| P05 | Frontend skeleton | D2 | DONE (human yes 2026-10-03 11:28) | lint 0 problems · typecheck 0 errors · vitest 39 passed (6 files, lines 87 %) · build OK · `start-all -Only frontend` healthy · walkthrough 6 passed (desktop + 390 px) · proxy `/api/v1/public/categories` → backend 404 problem+json · `package-lock.json` committed · commit 79d097b |
| P06 | Auth backend + E2E seed runner + smoke auth | D2 | DONE (human yes 2026-10-03 13:31) | mvnw verify 168 tests 0 failures (122 unit + 46 IT on Testcontainers PostGIS + Mailpit; 152 before the X-Forwarded-For fix) · `SMOKE AUTH PASSED: 19 / 19` (twice) · seed-e2e 5 accounts (3 fixed) · log scan 0 hits · frontend lint/typecheck/39 tests green |
| P07 | Auth screens + CameraCapture | D2 | DONE (human yes 2026-10-03 14:41) | lint/typecheck 0 errors · vitest 69 passed (14 files) · build OK · walkthrough 2 passed (desktop + phone, E2E stack) · 4 screenshots · backend verify 170 tests 0 failures (`RefreshCookieTest`) |
| P08 | Text classifier, YOLO detector (install Kaggle model), authenticity | D3 | DONE (human yes 2026-10-03 15:16) | YOLO installed sha256 `93af36422072…`, ONNX check 1x8x8400 · test split mAP50 0.607 / mAP50-95 0.379 (Pothole 0.347) · text clf C=10, sanity acc 0.90 / macro-F1 0.8995 · ruff clean · pytest 202 passed (8 `models` tests ran, 0 skipped; 5 new IT) · CPU 82 ms/image (median) · `/health` yolo + text clf "ok", MiniLM "folder missing" (P09) |
| P09 | Priority + duplicates (FROZEN) + MiniLM | D3 | DONE (human yes 2026-10-03 19:32) | priority golden **500 rows, 0 mismatches** (+ 6 factor rules 500/500 vs research factor files; location risk 500/500 through the live loader on `civicbrain_test`) · duplicates repro 3 pairs (DUPLICATE/UNCERTAIN/NOT_DUPLICATE) within 1e-6, formula 109/109 pairs · MiniLM installed (commit 1110a243fdf4, 11 files, 384-dim ok) · ruff clean · pytest 310 passed (12 `models` tests ran, 0 skipped) · `/health` all 3 models "ok" |
| P10 | Complaint intake API + e-mail outbox + smoke intake | D3 | IN PROGRESS | |
| P11 | Citizen screens | D3 | NOT STARTED | |
| P12 | Measure, estimate, quality, analyze orchestrator + smoke analysis | D4 | NOT STARTED | |
| P13 | Phone test over the tunnel | D4 | NOT STARTED | |
| P14 | Officer/admin/contractor-management API + smoke officer | D4 | NOT STARTED | |
| P15 | Officer portal UI | D4 | NOT STARTED | |
| P16 | WhatsApp (Twilio sandbox / log) | D5 | NOT STARTED | |
| P17 | Planning engine (haversine + OR-Tools) | D5 | NOT STARTED | |
| P18 | Plan API + PDF + assignment notifications + smoke plan | D5 | NOT STARTED | |
| P19 | Plan builder UI | D5 | NOT STARTED | |
| P20 | Contractor API + smoke contractor | D6 | NOT STARTED | |
| P21 | AI polish + message bodies | D6 | NOT STARTED | |
| P22 | Contractor screens + citizen feedback UI | D6 | NOT STARTED | |
| P23 | Close/reopen + security pass + smoke all (FEATURE FREEZE) | D6 | NOT STARTED | |
| P24 | Full-flow test with 2 phones + demo accounts | D7 | NOT STARTED | |
| P25 | Officer TOTP (stretch, optional) | D6/D7 | NOT STARTED | |
| P26 | Playwright happy path (optional) | D7 | NOT STARTED | |
| P27 | Bug bash | D7 | NOT STARTED | |
| P28 | Demo build + Gmail + backup | D7 | NOT STARTED | |
| P29 | Report material (metrics, screenshots, limits) | D7 | NOT STARTED | |
| P30 | Rehearsal + freeze + tag mvp-v1 | D7 | NOT STARTED | |

**Open issues (carry into the named prompt)**
- **RESOLVED 2026-10-03 09:36 - P03 S2 licence (`tests/fixtures/images/waterlogging_1.jpg`):** CC BY 4.0, attribution added.
  S2 = "Waterlogging Dataset" by yolo and car accident detection,
  https://universe.roboflow.com/yolo-and-car-accident-detection-xaltb/waterlogging (licence confirmed by the human/team).
  `data/yolo/dataset_sources.csv` S2 row (URL + `CC BY 4.0`) and `tests/fixtures/images/README.md` (attribution) updated;
  the fixture stays, nothing to do in P13.

## Full plan (after the deadline)
- **App track:** P0 — Machines, repo, Antigravity (status: covered by the MVP days; re-check its gate)
- **ML track:** P2 — ML data and models (status: NOT STARTED — MVP used the existing images only)
- **Known issue (P02):** V4 `fn_claim_jobs` can claim more jobs than `p_limit` (LIMIT … FOR UPDATE SKIP LOCKED re-scanned in a
  nested-loop semi join). MVP: the worker processes / releases every claimed row. Phase 2: V6 migration with
  `WITH picked AS MATERIALIZED (SELECT … LIMIT p_limit FOR UPDATE SKIP LOCKED) UPDATE jobs … FROM picked` (Task log P02).

## Phase gates
| Phase | Status | Gate evidence (command → result) | Approved by / date |
|---|---|---|---|
| P0 Setup | NOT STARTED | | |
| P1 Database | NOT STARTED | | |
| P2 ML data & models | NOT STARTED | | |
| P3 Backend & security | NOT STARTED | | |
| P4 Citizen portal | NOT STARTED | | |
| P5 Notifications | NOT STARTED | | |
| P6 AI worker | NOT STARTED | | |
| P7 Officer dashboard | NOT STARTED | | |
| P8 Action plans | NOT STARTED | | |
| P9 Contractor & closure | NOT STARTED | | |
| P10 Privacy & hardening | NOT STARTED | | |
| P11 Measurement & evaluation | NOT STARTED | | |
| P12 Demo readiness | NOT STARTED | | |

## Task log (newest first)

### 2026-10-03 — P10 — Complaint intake API + e-mail outbox dispatcher + smoke intake (IN PROGRESS, started 20:05)
- Requirement(s): FR-10 (server part), FR-11, FR-12, FR-13, FR-15, FR-50 (e-mail), FR-51, FR-52; docs/04 §3, §4, §5; 02 §1, §5
  (Submit, Notify rules 1-7 + 10); 07 §3; 12 §2, §4, §5; 03 §3; 09_7DAY §4 (intake happy path + 4 error codes, other citizen 404).
**Plan** (Claude Code, Auto mode; estimate 3 h → time box 4.5 h). JdbcClient everywhere (P06 decision), no new dependency/migration.
1. `complaints/`: `GET /public/categories`, `GET /public/wards` (5 m simplified in UTM 43N, 60 s cache) · `POST /citizen/capture-sessions` ·
   `POST /citizen/complaints` (validation order of 04 §5 in `ComplaintIntakeService`) · `GET /citizen/complaints[/{id}]` · feedback upsert
   (REOPENED via `WorkflowActor`). `common/RateLimiter.refund`.
2. `files/`: `PhotoProcessor` (magic bytes, header dimensions before decode, EXIF facts via metadata-extractor, orientation, long side
   ≤ 1920, JPEG q85 without metadata, SHA-256) · `PhotoStorage` (`photos/yyyy/mm/<uuid>.jpg`, delete on rollback) · `GET /files/{id}`
   (owner / officer in scope / assigned contractor / admin, else 404).
3. `notifications/`: `OutboxDispatcher` (@Scheduled 10 s, SKIP LOCKED, batch 50) → `NotificationPlanner` (rules 1-3, 5) →
   `TemplateRenderer` (`{{x}}`, HTML-escaping, unknown = error) + `PlaceholderValues` (16 values) → `NotificationChannel`
   (`EmailChannel` + Thymeleaf `templates/mail/layout.html`, `LogWhatsAppChannel`); retries 1/5/30 min, max 5; provider names rule 7.
Tests first: unit `TemplateRendererTest` (21 seeded templates from the V2 file render, no `{{`), `PhotoProcessorTest`, `RetryPolicyTest`;
IT `ComplaintIntakeIT` (happy path + every error code + 429 + rollback deletes the file), `CitizenComplaintsIT` (list/detail/feedback,
other citizen 404 incl. photo, officer scope/contractor/admin file access), `OutboxDispatcherIT` (Mailpit: SUBMITTED one mail per
recipient, VERIFIED none, twice → no duplicates, opt-out, WhatsApp `log`), `PublicReferenceIT`.
Verify: `.\mvnw.cmd -q verify` → E2E smoke `intake` (stop → seed-e2e -MinAccounts 3 → -E2E → smoke → -Restart) → log scan.

**Results so far** (2026-10-03, 20:05-20:40; no new dependency, no migration)
1. Files (`backend/`): `complaints/` (`api/PublicReferenceController`, `CitizenComplaintController`, `ComplaintData`; `service/ComplaintIntake`,
   `CitizenComplaints`; `repo/ReferenceRepository`, `CaptureSessionRepository`, `ComplaintRepository`, `FeedbackRepository`;
   `model/CaptureMethod`, `DepthAnswer`) · `files/` (`service/PhotoProcessor`, `PhotoStorage`; `repo/ImageAccessRepository`;
   `api/FileController`) · `notifications/` (`service/OutboxDispatcher`, `NotificationPlanner`, `PlaceholderValues`, `TemplateRenderer`,
   `MessageFormats`, `RetryPolicy`; `repo/NotificationRepository`; `channel/NotificationChannel`, `EmailChannel`, `LogWhatsAppChannel`) ·
   `resources/templates/mail/layout.html` (also removes the P04 Thymeleaf "Cannot find template location" WARN) · `common/RateLimiter.refund`,
   `common/AuditLog.userActionByKey` · `workflow/WorkflowActor.actAs` (actor context for the INSERT; `changeStatus` uses it, behaviour unchanged).
   Tests (all new): unit `PhotoProcessorTest` 5, `TemplateRendererTest` 4, `RetryPolicyTest` 1, `RateLimiterRefundTest` 1; IT `ComplaintIntakeIT` 10,
   `CitizenComplaintsIT` 5, `OutboxDispatcherIT` 4, `PublicReferenceIT` 2 (+ `it/support/ComplaintItSupport`); fixture
   `src/test/resources/photos/exif_gps_orientation6.jpg` (800x600, EXIF Make/Model, Orientation 6, DateTimeOriginal, GPS 18.7440/73.6760;
   written by a scratchpad Pillow script). No existing test changed.
2. Runs:

   | Check | Command | Result | |
   |---|---|---|---|
   | backend run 1 | in `backend`: `.\mvnw.cmd -q verify` | unit green; IT 2 of my new tests wrong (int vs long count; `listOfRows` gives `java.sql.Timestamp`, not `OffsetDateTime`) → tests fixed, code unchanged | FAIL→test fixed |
   | backend run 2 | same | IT 1 failure, a real bug: the owner of a merged child got the master's earlier SUBMITTED mail ("your complaint CB-…21 was received") because the recipient function runs at dispatch time → DECISION below, code fixed | FAIL→fixed |
   | backend run 3 | same | exit 0; reports: surefire `tests=135 failures=0 errors=0 skipped=0`, failsafe `tests=67 failures=0 errors=0 skipped=0` (was 124 + 46); test log: 0 JWTs, 0 `password=`, 0 full `+91` numbers, WhatsApp log line masked (`+91******5091`), 0 template WARN | PASS |
   | E2E seed (repo root) | `start-all.ps1 -Stop` → `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` | `E2E seed on civicbrain_e2e: 5 accounts created, 0 already present` · `PASS E2E database civicbrain_e2e ready with 3 fixed accounts` | PASS |
   | E2E stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E` | `PASS stack 'e2e' is up` (5 services healthy) | PASS |
   | smoke | `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage intake` | `FAIL stage 'intake' crashed: AttributeError: 'list' object has no attribute 'get'` after `PASS citizen1 list works` → **smoke script bug**, see "Open" below | FAIL (script) |
   | diagnosis (scratchpad, not the official evidence) | `probe_list.py` (GET /citizen/complaints → `200 {"items":[],"page":0,"size":20,"totalItems":0,"totalPages":0}`) · `probe_intake.py` = `smoke_flow.main(["--stage","intake"])` with `code_of` patched **in memory** for array bodies (file unchanged) | **`SMOKE INTAKE PASSED: 29 / 29`** (A → 201 `CB-000001` ward 1; used session 422; accuracy 400 → 422; outside → 422; text file → 415; Pothole without depth → 400; detail timeline + images; citizen2 → 404 for complaint and photo; own photo JPEG without EXIF; SUBMITTED mail to citizen1 with the CB number) | (PASS) |
   | log scan (E2E run) | `Select-String` over `logs\{backend,frontend,worker,ai-api}.log` for JWT / `password=` / `__Host-cb_rt=` / OTP codes / full `+91` numbers | `hits: 0` each; backend 0 ERROR; `complaint CB-000001 submitted (ward 1, category 1)`, `notification dispatcher: 1 outbox row(s) processed, 1 sent, 0 failed`; worker claimed job 1 ANALYZE_COMPLAINT → "built in P12" (expected) | PASS |
   | dev stack back | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` | `PASS stack 'dev' is up`; backend log `DB check: 23 wards visible to civicbrain_app`, 0 ERROR, **0 Thymeleaf template WARN** | PASS |
- DECISION: per-user limit 5 / 24 h counts **accepted** complaints (FR-11 "> 5 complaints by the same user in 24 h"): the token is taken in
  the documented position (2nd check) and given back (`RateLimiter.refund`) when a later check rejects the request; the per-IP limit
  (20 / h) counts every attempt. Reason: 5 GPS/photo mistakes must not lock a citizen out for a day.
- DECISION: merged-child owners receive a master's status mail only for events from their merge on (MERGED history row ≤ the outbox row's
  `created_at`); `fn_complaint_notification_recipients` is still the source. Without it the child owner can get the master's SUBMITTED
  text "your complaint CB-<master> was received" (worker merge within the 10-s dispatcher interval).
- DECISION: a template that needs a value the event does not have (e.g. ASSIGNED without a contractor) gives a FAILED notification row
  with `last_error = template error: no value for {{x}}` and no retry ("never a blank", 02 §5 rule 6); seen only for test data.
- DECISION: e-mail `rendered_body` = the HTML-escaped template text (renderer HTML mode); the Thymeleaf layout adds links and the
  plain-text part is its unescaped copy; subject and WhatsApp body are rendered as text. Rule 8 photos (`include_photo`) are P21.
- DECISION: notifications are claimed (SENDING, attempt counted) in a short transaction and sent outside it; a row still SENDING after
  10 min (process stopped mid-send) is closed FAILED without retry ("at most once", FR-51). Outbox rows are processed one per transaction
  (`FOR UPDATE SKIP LOCKED`); a failing row is retried next run and closed after 5 attempts.
- DECISION: photos — shorter side ≥ 320 px; ≤ 40 MP from the header before decoding; EXIF orientation applied before the metadata is
  dropped (the officer/YOLO see an upright photo); EXIF kept = `present`, `dateTimeOriginal`, `offsetTimeOriginal`, GPS lat/lon/timestamp
  (no make/model); JPEG magic but undecodable → 415; stored `file_name` = the random name (never the client's). `location_source`
  BROWSER_GPS. Location freshness = |server time − `locationCapturedAt`| ≤ 10 min (a phone clock ahead is treated like one behind).
- DECISION: officer scope = an active `officers` row with a scope row whose `ward_id` / `work_type_code` match (NULL = any; no row =
  nothing, docs/01 §2); assigned contractor = ACTIVE item in an ASSIGNED / IN_PROGRESS plan of the caller's firm (firm login or active
  staff). Timeline newest first (05 §4.7). Feedback "not fixed" remarks are a fixed sentence, never the citizen's comment (the REOPENED
  mail also goes to merged-child owners). `GET /public/wards` is GeoJSON served as `application/json` (the SPA sends
  `Accept: application/json`); simplified 5 m in EPSG:32643. Lat/lon box 18.6–18.8 / 73.6–73.8 = 400 (07 §3), inside the box but
  outside TDMC = 422 OUTSIDE_BOUNDARY.
- Not built (outside the prompt's Build list): the nightly orphan-photo cleanup of 12 §5 (marked "(P10)" there = full-plan phase P10
  "Privacy & hardening"); the plan-completion re-check after a citizen reopen (04 §6) comes with the plans (P18/P23).
- **Open (ASK-FIRST, waiting for the human):** `tests/smoke/smoke_flow.py` `code_of()` does `r.json().get("code")`, which raises
  `AttributeError` for any JSON **array** body; `categories()` calls `brief(r)` on `GET /public/categories`, which docs/04 §3 defines as an
  array (the same line checks `isinstance(r.json(), list)`). So the script misreads a docs/04-conformant response (rule 03: fix only then,
  record why). Proposed 3-line fix: return the code only when the body is a JSON object. The file passed before (stage `auth`) → asked.

### 2026-10-03 — D2 follow-up — requirement IDs in the existing tests (DONE 2026-10-03 19:55, human request Q2)
- Human yes (19:47): add the five IDs the gate found only by test name as comments; comments only, no test logic or assertion
  changed (ASK-FIRST item "changing a test that already passed" - approved).
- Changes (header comments only; three one-line Javadocs reflowed into multi-line ones with the same text): `AuthLoginIT`
  (FR-02 without officer TOTP (P25), NFR-01) · `AuthSessionIT` (NFR-01) · `ClientIpTest` (NFR-01) · `SetupRunnersIT` (FR-04
  first-admin part only - the bootstrap is in the docs/01 roles table, officer management is P14) · `LoginPage.test.tsx` (FR-02)
  · `CameraCapture.test.tsx` (FR-10 camera part) · `ai-service/tests/unit/test_authenticity.py` (FR-20). `git diff`: 16 lines
  added, 3 removed (the reflowed comments), no code line touched.
- Re-runs (same counts as the D2 gate run):

  | Check | Command | Result |
  |---|---|---|
  | backend | in `backend`: `.\mvnw.cmd -q verify` | exit 0; reports 19:50: surefire `tests=124 failures=0 errors=0 skipped=0`, failsafe `tests=46 failures=0 errors=0 skipped=0` (`AuthLoginIT` 9, `AuthSessionIT` 5, `SetupRunnersIT` 3, `ClientIpTest` 15, all 0 failures) |
  | AI lint | in `ai-service`: `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` |
  | AI tests | `.\.venv\Scripts\python.exe -m pytest -q` | `311 passed, 1 warning in 28.29s` (`tests/unit/test_authenticity.py` alone: `74 passed`) |
  | frontend | in `frontend`: `npm run lint` · `npm run typecheck` · `npm test -- --run` | exit 0 · exit 0 · `Test Files 14 passed (14)` `Tests 69 passed (69)` |
  | ID grep | `git grep -l -w <ID>` over backend/AI/frontend tests | FR-01, FR-02, FR-03, FR-04, FR-10, FR-20, FR-21, FR-60, NFR-01 each found (FR-22 / FR-25 via the Step 12 / Step 11 docstrings, unchanged) |

### 2026-10-03 — D2 gate (`/phase-gate D2`, "after P09") — PASSED (human yes 2026-10-03 19:47, tag `d2-done`; gate run 19:34-19:43)
- Gate items: `prompts/README.md` "Day gates" D2 row + the 09_BUILD_PLAN_7DAY §4 tests that exist after P09 (DB SQL tests;
  backend IT context/Flyway, register → OTP → login, generic 401, refresh rotation/reuse; AI priority golden, duplicate repro,
  YOLO smoke `pothole_1.jpg`; frontend login form validation, `CameraCapture` fallback; smoke `auth`) + the 09_7DAY §5
  "Gate D2" extras (admin exists, YOLO ONNX detects on 3 test images, `yolo_metrics.json` saved). Every command was run again
  in this session; no earlier result reused. One run, no fix needed.

  | Gate item | Evidence (command → result) | Result |
  |---|---|---|
  | `verify-all.ps1 -SkipE2E` | `pwsh -NoProfile -File scripts\dev\verify-all.ps1 -SkipE2E` → `VERIFY-ALL: GREEN (SKIP = component not built yet)` - DB PASS 1 s · Backend PASS 58 s · AI PASS 37 s · Frontend PASS 32 s · E2E SKIP; log `logs/verify-all_20261003_193442.txt` | PASS |
  | §4 DB SQL tests | (verify-all DB step) `ROLE TESTS PASSED: 7 / 7` · `NEGATIVE TESTS PASSED: 6 / 6` · `V4 TESTS PASSED: 11 / 11` · `V5 TESTS PASSED: 11 / 11` | PASS |
  | §4 backend IT (context + Flyway, register → OTP → login, generic 401, refresh rotation + reuse → 401) | (verify-all backend step) reports 19:34:52-19:35:38: surefire `tests=124 failures=0 errors=0 skipped=0`, failsafe `tests=46 failures=0 errors=0 skipped=0`; `SchemaIT` 5 · `AuthRegistrationIT` 9 (`registerThenOtpMailThenVerifyThenLoginAndMe`, Mailpit container) · `AuthLoginIT` 9 (`wrongPasswordAndUnknownAccountGiveTheSame401Body`) · `AuthSessionIT` 5 (`refreshRotatesTheCookieAndReuseRevokesTheWholeFamily`), all 0 failures | PASS |
  | `SMOKE AUTH PASSED` (fresh E2E stack) | `start-all.ps1 -Stop` → `seed-e2e.ps1 -MinAccounts 3` (`E2E RESET DONE: 48 tables emptied, 27 reference tables kept` · `5 accounts created, 0 already present` · `PASS E2E database civicbrain_e2e ready with 3 fixed accounts`) → `start-all.ps1 -E2E` (`PASS stack 'e2e' is up`) → `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage auth` → **`SMOKE AUTH PASSED: 19 / 19`** | PASS |
  | register → OTP → login in the browser | P07 human yes (2026-10-03 14:41, dev stack) + re-run now on the E2E stack, in `frontend`: `npx playwright test --config playwright.walkthrough.config.ts walkthrough/P07 --project desktop` → `1 passed (7.3s)` (register, OTP from Mailpit, verify, login, home, logout → `/`, ui.citizen login, reload keeps the session, camera fallback; desktop project only, so the approved phone screenshots were not overwritten - `git status` clean afterwards) | PASS |
  | log scan after the E2E run | `Select-String` over `logs\{backend,frontend,worker,ai-api}.log` for JWTs, `password=`, OTP codes, `__Host-cb_rt=` → `hits: 0`; `"level":"ERROR"` in `backend.log` → 0 | PASS |
  | YOLO model installed | `/health` (dev stack after `start-all.ps1 -Restart`) → `{"status":"ok","db":"ok",…,"modelsLoaded":true,"models":{"yolov8s_civicbrain.onnx":"ok","text_clf.joblib":"ok","all-MiniLM-L6-v2/":"ok"}}` (each file SHA-256 = MANIFEST) | PASS |
  | YOLO ONNX detects on 3 test images (§5) | scratchpad probe `d2_detect_fixtures.py` (read-only; `Detector.load` with the MANIFEST hash, in `ai-service`) → `pothole_1` Pothole 0.51/0.43 (+ Road Damage 0.26) · `garbage_1` Garbage Accumulation 0.66 · `waterlogging_1` Waterlogging 0.88 · `road_damage_1` Road Damage 0.53 → `FIXTURES WITH OWN CLASS: 4 / 4`, 75-83 ms each (same as P08) | PASS |
  | §4 YOLO smoke + all `models` tests | in `ai-service`: `.\.venv\Scripts\python.exe -m pytest -q -m models -rA -p no:cacheprovider` → `12 passed, 299 deselected` (0 skipped) incl. `test_pothole_fixture_gives_a_pothole_box`, `test_every_fixture_runs[×4]`, `test_three_research_pairs_are_reproduced` | PASS |
  | YOLO metrics in `docs/reports` | `docs/reports/yolo_metrics.json` (committed in P08): run `yolov8s_640_mvp_seed42`, `"evaluated_on": "existing test split … NOT a Talegaon field test set"`, overall P 0.588 / R 0.601 / mAP50 0.607 / mAP50-95 0.379 (Pothole mAP50 0.347 weakest); `docs/reports/yolo_plots/` 8 files | PASS |
  | classifier metrics | `docs/reports/text_clf_metrics.json` (committed in P08): C = 10, `sanity.label` "sanity check on 40 kit-written sentences", accuracy 0.9, macro-F1 0.8995, rows 40, model sha256 `d7b5ebf2df3a…` = MANIFEST (`/health` "ok") | PASS |
  | priority golden 0 mismatches | (verify-all AI step output) **`PRIORITY GOLDEN: 500 rows checked, 0 mismatches`** · `LOCATION RISK vs research: 500 rows checked, 0 mismatches` | PASS |
  | duplicate repro | (verify-all AI step output) `DUPLICATES REPRO:` ENG0059 DUPLICATE text 0.758436 vs 0.758436, score 0.688234 vs 0.688234 · ENG0069 UNCERTAIN 0.603463 vs 0.603463, 0.568724 vs 0.568724 · ENG0001 NOT_DUPLICATE 0.497914 vs 0.497913, 0.507758 vs 0.507758 | PASS |
  | §4 frontend tests (existing so far) | (verify-all frontend step) lint + typecheck exit 0 · `Test Files 14 passed (14)` `Tests 69 passed (69)` incl. `LoginPage.test` "validates before sending…" and `CameraCapture.test` "shows the explanation and the capture=\"environment\" file fallback when getUserMedia rejects" (wizard test comes with P11) | PASS |
  | admin exists (§5) | Not in the README D2 row; the P06 prompt moves the real first admin to P24 ("bootstrap-admin for the real demo admin is done in P24", human-only script). Capability proven: `SetupRunnersIT` 3/3 (`adminBootstrapCreatesAVerifiedAdminWithoutTotpOrForcedChange`, `adminBootstrapRefusesWhenAnAdminExists`) | PASS (live admin = P24) |
  | `git status` clean, pushed | `git status -sb` → `## main...origin/main`, no changes before this record; clean after the commit | PASS |
  | no new TODO/FIXME without issue link | `git diff d1-done..HEAD -U0` (code, not docs/lock files), added lines matching `TODO\|FIXME` → 0 hits | PASS |
  | PROGRESS entry per task | Task log has P06, P07, P08, P09 (each DONE with human yes) | PASS |
  | requirement IDs covered by tests | ID found in test names/comments: FR-01 (`PasswordPolicyTest`), FR-03 (`PasswordResetIT`), FR-21 (`test_classify.py`), FR-60 (`MeIT`); FR-22 / FR-25 via the "Step 12" / "Step 11" docstrings (`test_duplicates*.py`, `test_priority*.py`; both FRs are defined as the frozen Step 12 / Step 11 method). **Covered by named tests but without the ID in the test:** FR-02 → `AuthLoginIT` (generic 401, 10-failure lockout) + `LoginPage.test`; FR-10 camera part → `CameraCapture.test`; FR-20 → `test_authenticity.py` (74 cases); NFR-01 core → `AuthSessionIT`, `ClientIpTest`, `AuthLoginIT.tamperedOrWrongTypeTokensAreRejected`; FR-04 first-admin part → `SetupRunnersIT`. Out of D2: FR-04 officer management (P14), FR-11 server rejects (P10) | PASS (by mapping, as at D1) |
- Note: tagging the five IDs into the existing test files would be a comment-only change, but it changes tests that already
  passed (ASK-FIRST), so it was not done; asked as Q2.
- Note: one read-only Bash listing of mine used `cd backend/target`, which moved the shared working directory (same slip as
  D1); noticed at once, `Set-Location C:\dev\civicbrain` before the next command, nothing ran in the wrong folder.
- Dev stack back: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` → `PASS stack 'dev' is up` (5 services healthy).
- Human answer (2026-10-03 19:47): **Approve D2: yes** → D2 PASSED, commit, push, tag `d2-done`. **Q2 yes** - add the five
  missing requirement IDs as comments to the existing tests (comments only), re-run the affected suites → "D2 follow-up".
- Next: `/run-prompt P10`.

### 2026-10-03 — P09 — Priority (FROZEN Step 11) + duplicates (FROZEN Step 12) + MiniLM (DONE, human yes 2026-10-03 19:32)
- Requirement(s): FR-25 (priority + per-factor explanation), FR-22 duplicates part (Step 12); docs/06 §1 (daily 02:00 IST
  recompute), §2 steps 7-8, §2.6, §2.7, §5; 02-frozen-rules (Step 11, Step 12); 09_7DAY §4 (priority golden 0 mismatches,
  duplicate scoring reproduces 3 pairs).
**Plan** (Claude Code, Auto mode; estimate 2 h → time box 3 h):
1. `download_models.py` → `models/all-MiniLM-L6-v2/` + MANIFEST entry (done: commit 1110a243fdf4, 384-dim check ok).
2. `pipeline/priority.py`: rules loaded from `data/priority/*.csv` (weights + the factor rule CSVs, engine validations kept),
   engine combination ported 1:1 (range check, weighted sum, clamp, round 2, level, reasons), the 7 live factor rules as
   pure functions, explanation JSON, DB loader (PostGIS: ward, road type, POIs ≤ 1 km, frequency/historical counts) and
   writer (`priority_assessments` is_current switch + `complaints.current_priority_*`).
3. `pipeline/duplicates.py`: MiniLM embedder (SHA-256 of every folder file vs MANIFEST before loading, offline), pure
   pair score/decision (research arithmetic order), complaint decision (two masters / COMPLETED-CLOSED master / not
   SUBMITTED → UNCERTAIN), DB part (`fn_duplicate_candidates`, upsert into `duplicate_relation`, `complaints.duplicate_*`).
4. Worker: daily 02:00 IST priority recompute for open non-synthetic complaints (catch-up after a missed 02:00).
Tests first: `tests/unit/test_priority_golden.py` (500 rows, 0 mismatches + per-factor rules vs research CSVs),
`test_priority.py`, `test_duplicates.py` (edges 0.55/0.59, clamps, masters), `test_duplicates_repro.py` (`models`),
`tests/it/test_priority_it.py`, `tests/it/test_duplicates_it.py` (40 m, same day, similar text → DUPLICATE, would MERGE),
worker schedule tests. Verify: ruff, pytest (models tests run), `start-all.ps1 -Only worker,ai-api -Restart`, `/health`.
- Pre-check (read-only probe on the seeded dev DB as `civicbrain_ai`, scratchpad script, 500 research complaints): the
  live factor rules reproduce the research factor CSVs - location risk = max over POIs of importance × distance band
  (0 mismatches; the "nearest POI only" reading: 60), frequency = same category ≤ 300 m in the previous 30 days
  (0; any category: 240), historical = same ward + same category, earlier ≤ 180 days (0 with the research ward mapping;
  13 complaints changed ward in V3), wait = days since submit / 179.2729 d (dataset span) × 100 (0), road type and ward
  population (0).

**Results** (2026-10-03, verified 19:25; no ASK-FIRST stop, no human step)
1. Files: `ai-service/pipeline/priority.py` (rules loader + engine port + 7 factor rules + explanation + PostGIS loader +
   is_current writer + daily recompute) · `ai-service/pipeline/duplicates.py` (pair score, complaint decision, MiniLM
   embedder with MANIFEST check, candidates/upsert/complaint fields) · `app/config.py` (FROZEN `DUP_*`/`PRIORITY_*`
   constants, ASSUMPTION severity mapping, `IST`, `REPO_ROOT_DIR`) · `worker/run.py` (daily 02:00 IST step) ·
   `ai-service/models/MANIFEST.json` (MiniLM entry: revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 11 files with
   SHA-256). Tests (all new): `tests/unit/test_priority_golden.py` (10), `test_priority.py` (49), `test_duplicates.py` (32),
   `test_duplicates_repro.py` (3, `models`), `tests/it/test_priority_it.py` (4), `tests/it/test_duplicates_it.py` (3, one
   `models`), `tests/unit/test_worker_loop.py` +7 (the 2 existing tests unchanged). 202 → 310.
2. Runs (in `ai-service` unless noted):

   | Check | Command | Result | |
   |---|---|---|---|
   | MiniLM (repo root) | `ai-service\.venv\Scripts\python.exe ai-service\training\download_models.py` | `CHECK ok: 384 dimensions, similarity of two pothole sentences = 0.897` · `INSTALLED …\all-MiniLM-L6-v2 (commit 1110a243fdf4, 11 files)` | PASS |
   | factor probe (repo root, read-only, scratchpad) | `ai-service\.venv\Scripts\python.exe <scratchpad>\probe_factors.py` + `probe_hist.py` | see pre-check above (0 mismatches for every factor rule) | PASS |
   | priority tests | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_priority_golden.py tests/unit/test_priority.py` | `PRIORITY GOLDEN: 500 rows checked, 0 mismatches` · `59 passed` | PASS |
   | location rule, shipped code (repo root, read-only, after the human asked; my report said "matched 0/500" and meant 0 mismatches) | `ai-service\.venv\Scripts\python.exe <scratchpad>\probe_location_live.py` (`pipeline.priority.load_inputs` + `location_risk_score` on the seeded dev DB) | `complaints compared: 500 … mismatches: 0` · all 18 distinct research values reproduced, e.g. #8 hospital 76.1 m → 100 × 1.00 = 100 · #9 hospital 126.1 m → 100 × 0.75 = 75 · #131 police station 210.0 m → 95 × 0.75 = 71.25 · #5 government office 650.4 m → 65 × 0.25 = 16.25 · #1 no POI within 1 km → 0 | PASS |
   | duplicate tests, 1st run | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_duplicates.py tests/unit/test_duplicates_repro.py -rA` | `1 failed, 34 passed`: my new test expected 1.0 for a perfect pair, but 0.70+0.20+0.10 = 0.9999999999999999 in floating point (the research np.clip gives the same) → test fixed (`<= 1.0`, approx 1.0), code unchanged | FAIL→test fixed |
   | first ruff | `.\.venv\Scripts\python.exe -m ruff check .` | 10 × E501 → wrapped by hand → `All checks passed!` | FAIL→fixed |
   | IT, 1st run | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_duplicates.py tests/unit/test_worker_loop.py tests/it/test_priority_it.py tests/it/test_duplicates_it.py -rA` | `1 failed, 47 passed`: jsonb keeps no key order, my test compared the stored `factors` keys as a list → compared as a set | FAIL→test fixed |
   | lint | `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` | PASS |
   | tests | `.\.venv\Scripts\python.exe -m pytest -q` | `310 passed, 1 warning in 27.76s` (warning = Starlette `httpx` deprecation, existed before) | PASS |
   | models tests | `.\.venv\Scripts\python.exe -m pytest -q -m models -rA` | `12 passed, 298 deselected` (0 skipped: classifier 1, detector 7, duplicates repro 3, duplicates IT 1) | PASS |
   | restart (repo root) | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only worker,ai-api -Restart` | `PASS worker healthy` · `PASS ai-api healthy` · `PASS stack 'dev' is up` | PASS |
   | /health (repo root) | `ai-service\.venv\Scripts\python.exe -c "import urllib.request … /health …"` | `{"status":"ok","db":"ok","osrm":"not used (haversine)","modelsLoaded":true,"models":{"yolov8s_civicbrain.onnx":"ok","text_clf.joblib":"ok","all-MiniLM-L6-v2/":"ok"}}` | PASS |
   | worker log | `Get-Content logs\worker.log -Tail 8` | no model warning any more; `daily priority recompute: 0 complaint(s) updated, 0 skipped` (catch-up at start; the dev DB has only synthetic complaints) | PASS |
3. Duplicate reproduction (`test_duplicates_repro.py`, texts from `data/complaints/synthetic_complaints_500.csv`, research
   distance/hours): ENG0059 DUPLICATE text 0.758436 vs 0.758436, score 0.688234 vs 0.688234 · ENG0069 UNCERTAIN 0.603463 vs
   0.603463, 0.568724 vs 0.568724 · ENG0001 NOT_DUPLICATE 0.497914 vs 0.497913, 0.507758 vs 0.507758 (all < 1e-6, limit 0.001).
   The pure formula reproduces all 109 research pairs (score, sub-scores < 1e-12, decision) from their recorded inputs.
- DECISION: rule files read from `data/priority/` (constant `PRIORITY_DATA_DIR`, like `priority_engine.py`'s repo-relative
  paths) - no copy, so there is one frozen source; the loader keeps the engine's checks and refuses weights that differ
  from the FROZEN ones in `app/config.py`.
- DECISION: live factor rules = the research rule files, proven 0-mismatch on the 500 research complaints (pre-check):
  Rloc max over POIs (bands `[min, max)`; both readings fit the data), F same category ≤ 300 m in the 30 days before
  submission, H same ward + same category in the 180 days before submission / 14, Twait / 179.2729 days, Iinfra by
  road type, Ipop by ward NUMBER (`wards.ward_number`, docs/INVENTORY.md). The dataset-derived maxima (179.2729 d, 14)
  are constants in `app/config.py`, checked against the research files by the golden test.
- DECISION (ASSUMPTION in `app/config.py`, written into every explanation): live severity level from the depth answer
  SHALLOW → LOW 25, FINGER → MEDIUM 50, DEEP → HIGH 75; no answer / other categories → MEDIUM 50; CRITICAL never set
  automatically (the Step 11 levels were synthetic, no live rule exists).
- DECISION: counts (F, H) use only complaints of the same kind (real vs synthetic) and never REJECTED ones; duplicates
  never compare real with synthetic complaints (02-frozen-rules "Honesty"; the demo complaints must not pull a phone
  complaint into a synthetic master). Missing ward or unknown road type → DataError (06 sec. 2 step 8 "factor data missing
  → job fails"); a row without ward/road gets them from `fn_locate_point`.
- DECISION: reasons use the wording of `calculate_priority_scores.py` (it wrote `priority_scores.csv`; `priority_engine.py`
  words two reasons differently) - the golden test compares the reasons too.
- DECISION: duplicate text = title + " " + description (docs/06); the research joined with a newline - proven identical
  embeddings (`test_title_and_description_joined_by_space_or_newline_embed_the_same`).
- DECISION: duplicates writer sets `duplicate_status`, `matched_complaint_id`, `duplicate_checked_at`,
  `duplicate_review_required`, and `master_complaint_id` only when the decision merges (an officer's earlier merge is never
  cleared); stale AI pairs of the complaint are deleted, officer-reviewed rows are never overwritten (upsert `WHERE
  review_decision IS NULL`).
- DECISION: daily recompute = open statuses (SUBMITTED … REOPENED, not REJECTED/MERGED/COMPLETED/CLOSED), non-synthetic,
  with a current assessment; one transaction per complaint; IST as fixed UTC+05:30; a worker that missed 02:00 catches up
  once (last run = latest `explanation.trigger = DAILY_RECOMPUTE` row); a missing rule file is logged and retried the next day.
- Note: the scratchpad probe and the earlier shell call that named the test env template (blocked by the deny rule, my
  mistake, not retried) did not change anything. A stray `python -` waited on stdin for 10 min and was stopped (no effect).
- Human answer (2026-10-03 19:32): asked first what "location risk matched 0/500" meant - it was my wording for "0 mismatches
  out of 500"; re-checked through the shipped loader (row above), no bug, nothing relabelled. **Q1 yes.** Asked for:
  (a) a permanent test → `tests/it/test_priority_it.py::test_live_location_rule_reproduces_all_500_research_location_scores`
  (the 500 research complaints at their seed locations - EWKB read from `db/seed/seed_synthetic_demo_data.sql` - inserted
  into `civicbrain_test` as synthetic rows, `load_inputs` + `location_risk_score` vs `location_risk_scores.csv`):
  `.\.venv\Scripts\python.exe -m pytest -q tests/it/test_priority_it.py -k location_rule_reproduces` →
  `LOCATION RISK vs research: 500 rows checked, 0 mismatches` · `1 passed`; then `ruff check .` → `All checks passed!` ·
  `pytest -q` → `311 passed, 1 warning in 34.82s`; (b) the POI limitation in the known limitations → `docs/13_DEMO_AND_DEPLOY.md`
  §5 (25 POIs: 8 hospitals, 6 bus stops, 5 schools, 3 colleges, 2 government offices, 1 police station; no fire stations,
  railway stations or markets; 213 of 500 research complaints score 0 for location risk) - for the P29 report.
- Open / hand-offs: **P12** orchestrator: step 7 `duplicates.find_duplicates(s, cid, duplicates.get_embedder(settings))`
  then step 8 `priority.assess_complaint(s, cid)`; when `decision.merge` set status MERGED (SYSTEM) in the SAME transaction
  (the writer already set `master_complaint_id`), else VERIFIED; then `REQUIRE_MODELS=true` (all three models are now
  "ok"). **P15** officer UI: list the priority factors in formula order (`FACTORS`), jsonb does not keep the key order;
  show the severity "assumption" flag. **P10** intake must store `ward_id`/`road_id`/`poi_id` from `fn_locate_point`
  (historical counts match on `complaints.ward_id`).

### 2026-10-03 — P08 — Text classifier, YOLO detector, authenticity checks (DONE, human yes 2026-10-03 15:16)
- Requirement(s): FR-20 (authenticity), FR-21 (text classification + mismatch badge), FR-22 (YOLO detection); docs/06 §2,
  §2.1, §2.2, §2.3, §5; docs/03 §3-§4; rule 30; 02-frozen-rules (YOLO classes); 09_7DAY §4 (YOLO smoke `pothole_1.jpg`).
- Human step: `kaggle_download\civicbrain_yolo_outputs.zip` (38.9 MB, 2 Oct 21:21) was already in place → no wait.
**Plan** (Claude Code, Auto mode; estimate 2.5 h → time box 3.75 h):
1. Install YOLO: `install_kaggle_model.py --check` → `models/yolov8s_civicbrain.onnx` + MANIFEST + `docs/reports/yolo_metrics.json`, plots.
2. `training/train_text_clf.py` (recipe of the prompt: TF-IDF word 1-2 + `char_wb` 2-5 → LR balanced, C by 5-fold stratified CV
   over [1, 2, 5, 10]) → `models/text_clf.joblib` + metrics json (+ `docs/reports/` copy) + MANIFEST entry `kind: text-classifier`.
3. `pipeline/classify.py`: SHA-256-checked load once, `predict` top-3, mismatch rule (p ≥ 0.70) → `is_accepted`, TEXT row writer.
4. `pipeline/detect.py`: Ultralytics on the ONNX (640, 0.25, 0.5, cpu), loaded once, pixel boxes, `model_version` = sha[:12],
   primary detection, `yolo_detections` + IMAGE row writer, CPU ms per image.
5. `pipeline/authenticity.py`: pure check functions for the 10 MVP checks + score/clamp/FLAGGED, `phash` signed int64,
   DB helpers (facts query with PostGIS edge distance + `fn_similar_images`), delete-then-insert writer + `complaints.authenticity_*`.
Tests first: `tests/unit/test_text_clf.py`, `test_classify.py`, `test_authenticity.py` (one per table row), `test_detect.py`
(`@pytest.mark.models`), model-manifest start-up test (`REQUIRE_MODELS`); `tests/it/test_pipeline_it.py` (writers idempotent,
facts from PostGIS on `civicbrain_test`). Verify: ruff, pytest (models tests run), metrics printout, CPU ms,
`start-all.ps1 -Only worker,ai-api -Restart` → `/health` per-model status.

**Results** (2026-10-03, verified 15:10 - well inside the 2.5 h estimate; one ASK-FIRST stop, human yes at ≈ 15:00)
1. Files: `ai-service/pipeline/{__init__,classify,detect,authenticity}.py` · `ai-service/training/train_text_clf.py` ·
   `app/config.py` (TEXT_* and YOLO_* constants) · `app/models_check.py` (`expected_sha256`, `verify_file` = hash BEFORE
   joblib/Ultralytics touch a file, `model_status`) · `app/main.py` (`/health` `models`) · `ai-service/models/MANIFEST.json`
   (committed; YOLO + text-classifier entries) · `docs/reports/{yolo_metrics,dataset_report,text_clf_metrics}.json` +
   `docs/reports/yolo_plots/` (8 files, 1.4 MB) · `docs/04_API_CONTRACT.md` §10 (`/health` `models`) ·
   `tests/fixtures/images/README.md` (P08 smoke results). Tests: `tests/unit/test_{text_clf,classify,detect,authenticity,
   model_startup}.py`, `tests/it/test_pipeline_it.py`; `tests/unit/test_api.py` expected `/health` body + `"models": {}`
   (the only change to an existing test - ASK-FIRST, human yes; nothing loosened).
2. YOLO (`install_kaggle_model.py --check`): `INSTALLED …\yolov8s_civicbrain.onnx (sha256 93af36422072...)` ·
   `ONNX CHECK input images [1, 3, 640, 640], output (1, 8, 8400)` · run `yolov8s_640_mvp_seed42`, 65 of 120 epochs ran
   (48.5 min on Kaggle). **Existing test split (339 images), not a Talegaon field test:**

   | Class | Precision | Recall | mAP50 | mAP50-95 |
   |---|---|---|---|---|
   | overall | 0.588 | 0.601 | 0.607 | 0.379 |
   | Pothole | 0.384 | 0.386 | 0.347 | 0.120 |
   | Garbage Accumulation | 0.580 | 0.711 | 0.715 | 0.470 |
   | Waterlogging | 0.804 | 0.933 | 0.918 | 0.730 |
   | Road Damage | 0.583 | 0.374 | 0.448 | 0.196 |
3. Text classifier (`train_text_clf.py`): 660 train rows (500 synthetic + 160 kit; 184 distinct texts) · CV macro-F1 by C
   {1: 0.9420, 2: 0.9450, 5: 0.9466, 10: 0.9481} → **C = 10** · **sanity check on 40 kit-written sentences: accuracy 0.90,
   macro-F1 0.8995** (4 wrong: Marathi waterlogging → Road Damage p 0.31; Hinglish blocked drain → Garbage 0.58; "lamp post
   … dead" → Other 0.25; "loud speakers" (Other) → Streetlight 0.40) · `text_clf.joblib` sha256 `d7b5ebf2df3a…`.
4. Detector on the fixtures (CPU, 640): pothole_1 → Pothole 0.51 + 0.43 (+ Road Damage 0.26), garbage_1 → Garbage 0.66 (IoU
   0.77 vs label), waterlogging_1 → Waterlogging 0.88 (IoU 0.96), road_damage_1 → Road Damage 0.53 (IoU 0.73). pothole_1's
   Pothole boxes lie inside the one large labelled patch (IoU 0.02; the Road Damage box covers the patch) - the smoke test
   passes, no fixture replaced, noted in the fixtures README. **CPU time per image: median 81.6 ms (75.4-91.7, 20 runs);**
   load + warm-up ≈ 3.7 s once per process.
5. Runs (in `ai-service` unless noted):

   | Check | Command | Result | |
   |---|---|---|---|
   | YOLO install (repo root) | `ai-service\.venv\Scripts\python.exe ai-service\training\install_kaggle_model.py --check` | exit 0, metrics above | PASS |
   | classifier (repo root) | `ai-service\.venv\Scripts\python.exe ai-service\training\train_text_clf.py` | `SANITY accuracy=0.9 macro_F1=0.8995` · `SAVED … (sha256 d7b5ebf2df3a...)` | PASS |
   | first IT run | `.\.venv\Scripts\python.exe -m pytest -q tests/it/test_pipeline_it.py` | `1 failed, 4 passed`: psycopg "inconsistent types deduced for parameter" (`:category` used twice) → `CAST(:category AS varchar)` → `5 passed` | FAIL→fixed |
   | first ruff | `.\.venv\Scripts\python.exe -m ruff check .` | 17 × E501 in new files → wrapped by hand → `All checks passed!` | FAIL→fixed |
   | lint | `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` | PASS |
   | tests | `.\.venv\Scripts\python.exe -m pytest -q` | `202 passed, 1 warning in 20.01s` (warning = Starlette `httpx` deprecation, existed before) | PASS |
   | models tests | `.\.venv\Scripts\python.exe -m pytest -q -m models -rA` | `8 passed, 191 deselected` (classifier 1, detector 7; 0 skipped) - run before the last 3 tests were added | PASS |
   | restart (repo root) | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only worker,ai-api -Restart` | `PASS worker healthy` · `PASS ai-api healthy` · `PASS stack 'dev' is up` | PASS |
   | /health (repo root) | `ai-service\.venv\Scripts\python.exe -c "import urllib.request … /health …"` | `{"status":"ok","db":"ok","osrm":"not used (haversine)","modelsLoaded":false,"models":{"yolov8s_civicbrain.onnx":"ok","text_clf.joblib":"ok","all-MiniLM-L6-v2/":"folder missing"}}` | PASS |
   | worker log | `Get-Content logs\worker.log -Tail 6` | `model files not ready, REQUIRE_MODELS=false so the worker still runs: all-MiniLM-L6-v2/: folder missing` (before P08: all three missing) | PASS |
6. Tests written (all new except the one approved key): classifier training 7 (recipe, CV grid + tie rule, determinism, sanity
   guard ≥ 0.80, metrics label, MANIFEST entry) · classify 12 (mismatch rule 5 cases, top-3, checksum before unpickling,
   missing model, empty text, loaded once, installed model `models`) · detect 13 (xyxy → pixel boxes, primary detection,
   IMAGE summary, checksum, unreadable image, Ultralytics config dir, 7 `models`) · authenticity 74 (every table row incl.
   boundaries, clamp, FLAGGED < 40, duplicate hint, worst match, signed int64 pHash = `fn_phash_distance`) · start-up 9
   (`REQUIRE_MODELS=true` + wrong hash / missing file → worker exit 2 with the file name, API ConfigError; false → warning;
   `/health` per-model; pipeline imports no model library) · IT 5 on `civicbrain_test` (facts from PostGIS +
   `fn_similar_images`, writers run twice → same rows, REJECTED kept, near-edge WARN, rate/travel). New: 120 (82 → 202).
- DECISION: "API already rejects" cases that still reach the worker → FAIL with the row's WARN delta (GPS_ACCURACY −10,
  GPS_FRESHNESS −10, BOUNDARY outside −5); CAPTURE_SESSION has no delta in the table → FAIL 0. No new numbers.
- DECISION: missing input → SKIPPED 0 (no accuracy / capture time / boundary row); missing or unreadable photo → both
  IMAGE_REUSE checks WARN 0 (06 §2 step 1 "authenticity WARN"), CATEGORY_IMAGE_MISMATCH SKIPPED.
- DECISION: IMAGE_REUSE_PHASH 5-10 bits **nearby & recent** → PASS with duplicate hint (the table only names ≤ 4 bits; same
  place + same week is the duplicate step's job); the worst of several matches decides. SUBMISSION_RATE > 5 in 24 h stays
  WARN −10 (the table has no FAIL). IMPOSSIBLE_TRAVEL uses the two GPS fix times when both exist, else submit times; 0 s
  apart with any distance = WARN. CATEGORY_IMAGE_MISMATCH own class < 0.4 and no other class ≥ 0.5 (or no box) → PASS
  ("no evidence").
- DECISION: an officer's `authenticity_status = REJECTED` is never overwritten by a re-analysis (score still updated).
  Delete-then-insert removes only this analysis' rows (image_id NULL or the citizen photo), so later ANALYZE_IMAGE rows of
  contractor photos stay.
- DECISION: IMAGE `ai_classifications` row = best class over all boxes, `top_k` = best confidence per class,
  `is_accepted` = the CATEGORY_IMAGE_MISMATCH evidence (own class ≥ 0.4 → true, only other classes ≥ 0.5 → false, else NULL);
  no row when nothing is detected. TEXT row: `top_k` = top-3 `[{category, p}]`, `is_accepted` NULL for a complaint
  without a category. `model_version` = SHA-256[:12] for both models; names `text_clf_tfidf_lr`, `yolov8s_civicbrain`.
- DECISION: C chosen by macro-F1 (the reported metric), ties → smallest C. Note: the CV scores are optimistic - the 500
  synthetic rows have only 24 distinct texts, so identical texts fall into training and validation folds; the sanity
  set (never trained on, overlap checked) is the honest number.
- DECISION: `/health` `models` = per required file "ok" (present + SHA-256 = MANIFEST, checked once at API start) or the
  problem; nothing is loaded into the API process (it runs no inference). docs/04 §10 updated (human yes).
- FIX (found while verifying): Ultralytics wrote its `settings.json` to **`C:\tmp\Ultralytics\`** (drive root, outside the
  workspace) because `YOLO_CONFIG_DIR` (`ai-service\.ultralytics`) did not exist yet and it silently falls back to `/tmp`.
  `detect._ultralytics_env()` now creates the folder before the import; regression test
  `test_ultralytics_keeps_its_settings_in_yolo_config_dir`; now `USER_CONFIG_DIR = …\ai-service\.ultralytics\Ultralytics`.
  **Human: please delete the folder `C:\tmp\Ultralytics`** (only a settings file; I may not delete or work outside the repo).
- Note: `docs/reports/dataset_report.json` (from the Kaggle zip) contains the Kaggle input path with the account name
  (`/kaggle/input/datasets/<account>/civicbrain-yolo/...`) - not a secret, committed as the installer intends.
- Human answer (2026-10-03 15:16): **Q1 yes** - use the YOLO numbers as they are, stated as "existing test split, not a
  Talegaon field test". **Q2 yes** - 0.90 accuracy on the 40 kit-written sanity sentences is OK. The human deletes the stray
  `C:\tmp\Ultralytics` settings folder.
- Open / hand-offs: **P09** MiniLM (`/health` then all "ok"). **P12** wires the three modules into ANALYZE_COMPLAINT
  (step 1 computes `phash` with `authenticity.phash_int64` and stores it before `load_facts`; YOLO only for categories with a
  `yolo_class_id`; `write_detections` returns the primary `detection_id` for `defect_measurements`), then
  `REQUIRE_MODELS=true`. **Phase 2:** YOLO golden test (IoU ≥ 0.5) needs a better pothole fixture; Pothole mAP50 0.35 is
  the weakest class (more/cleaner pothole labels).

### 2026-10-03 — P07 — Auth screens + CameraCapture (DONE, human yes 2026-10-03 14:41)
- Requirement(s): FR-01, FR-02, FR-60 (register + notice + consents), FR-10/FR-11 (in-app camera + GPS); NFR-01; docs/05 §2,
  §3, §4 step 2, §7, §8; docs/04 §1-§3; docs/07 §1 (cookie/CSRF), §7; docs/12 §6; rule 20; 09_7DAY §4 (login form validation,
  `CameraCapture` fallback when the camera is denied).
**Plan** (Claude Code, Auto mode):
0. Pre-check (human request): `RefreshCookie` hard-codes `secure(true)`, `path("/")`, no Domain and never reads the request →
   already independent of `request.isSecure()`. Add unit test `RefreshCookieTest` (issue + clear) + DECISION line; backend verify.
1. `lib/api.ts`: `ApiError.extensions` (RFC 9457 members, e.g. `otpId`); 401 → ONE shared refresh → retry once (`auth/session.ts`).
2. `AuthProvider`: status loading/signed-in/signed-out, silent refresh on load (refresh → GET /me, `mcp` claim), login, logout
   (+ `BroadcastChannel('cb-auth')`), guards wait while loading, `mustChangePassword` → `/change-password`, role → portal.
3. Screens (react-hook-form + zod, `features/auth`): Login, Register (notice from `/public/privacy-notice`), OTP (6 boxes, paste,
   resend 60 s), Change password, Privacy page, citizen Profile (opt-ins/consents), citizen Home (greeting + Report button).
4. `components/camera/CameraCapture` (+ orientation/geolocation hooks); `/citizen/new` hosts it until the P11 wizard.
5. `components/ProtectedImage` (bearer fetch → blob URL, revoked on unmount).
Tests first (Vitest + MSW): the prompt's 6 + api refresh/retry + camera happy path (tracks stopped on unmount).
Verify: `npm run lint` / `typecheck` / `test -- --run` / `build` → E2E walkthrough `walkthrough/P07_auth.spec.ts` (stop → seed-e2e
-MinAccounts 3 → -E2E → 4 screenshots → -Restart).

**Results** (2026-10-03, verified 14:24 - inside the 2.5 h estimate; one stop for the human at 14:10, plan B approved 14:15)
1. Task 0 (human request): `RefreshCookie.base()` = `ResponseCookie.from("__Host-cb_rt").httpOnly(true).secure(true).sameSite("Strict")
   .path("/")`, no `domain(...)`; `issue`/`clear` take no request → never depended on `request.isSecure()`. Nothing changed in
   main code; new unit test `RefreshCookieTest` (2). `AuthSessionIT` already asserted the same attributes over plain-HTTP MockMvc.
2. Files (`frontend/src/`): `api/{auth,me,publicApi}.ts` (zod schemas per docs/04) · `auth/AuthProvider.tsx` (silent refresh on
   load → GET /me, ONE shared refresh promise, Web Locks across tabs, `BroadcastChannel('cb-auth')` logout, query cache cleared on
   sign-out) · `auth/{RequireAuth,authContext,jwt}.ts(x)` (loading skeleton, `mustChangePassword` → `/change-password`,
   `pathAfterLogin` = safe local `returnTo` of the own portal) · `lib/api.ts` (`ApiError.extensions` = RFC 9457 members such as
   `otpId`; 401 → registered refresh handler → retry once; no refresh for login/register/otp/refresh/logout/forgot/reset; the
   planned `auth/session.ts` was not needed) · `components/form/{fields,validation}` · `components/camera/{CameraCapture,capture,
   sensors}` · `components/ProtectedImage.tsx` · `features/auth/{LoginPage,RegisterPage,OtpPage,OtpInput,ChangePasswordPage,
   PasswordStrength,PrivacyNoticeBox,AuthCard,verifyEmailPath}` · `features/citizen/{CitizenHomePage,ProfilePage,NewComplaintPage}`
   · `features/public/PrivacyPage` · `lib/format.ts` · routes (`/verify-email`, `/change-password`, `/citizen/profile`) · `en.json`
   (auth, profile, validation, citizenHome, newComplaint, camera) · `App.tsx` (`RouterProvider` from `react-router/dom`) ·
   `components/MobileLayout.tsx` + `features/officer/OfficerLayout.tsx` (logout order) · `vitest.config.ts` (React Router alias) ·
   `test/{handlers,renderApp}` · `walkthrough/P07_auth.spec.ts`. Backend: `unit/auth/RefreshCookieTest.java`.
3. Tests (all new; no existing assertion changed): `AuthProvider.test` 5 (two parallel 401s → ONE refresh with `X-CB-CSRF: 1`, both
   retried; failed refresh → signed out, no second retry; load restores session + `mcp`; no cookie → signed out; BroadcastChannel
   logout) · `LoginPage.test` 5 (empty / bad e-mail / short password never sent; phone identifier + generic 401 keeps input;
   returnTo; one-time password → change screen; EMAIL_NOT_VERIFIED → OTP screen with `otpId`) · `RegisterPage.test` 3 (privacy
   checkbox required, nothing sent; body with `+91`, notice version, consents; PASSWORD_POLICY field error) · `OtpPage.test` 4 (pasted
   code fills 6 boxes → verify → login prefilled; incomplete code not sent; OTP_INVALID message + resend disabled 60 s; no otpId) ·
   `ChangePasswordPage.test` 3 · `CameraCapture.test` 6 (NotAllowedError → fallback `accept="image/*" capture="environment"`, only
   one file input; location denied blocks "Use this photo"; > 150 m blocks; shutter → JPEG 0.9 + fix (`enableHighAccuracy`,
   `maximumAge 0`, `timeout 20000`) + beta/gamma, tracks stopped, result `IN_APP_CAMERA`; tracks stopped on unmount; http → secure
   address text) · `ProtectedImage.test` 2 · `MobileLayout.test` 2 (logout from citizen/officer portal ends on `/`, CSRF header).
4. Runs (in `frontend` unless noted):

   | Check | Command | Result | |
   |---|---|---|---|
   | backend (Task 0) | in `backend`: `.\mvnw.cmd -q verify` | exit 0; reports surefire `tests=124 failures=0 errors=0`, failsafe `tests=46 failures=0 errors=0` (170; `RefreshCookieTest tests="2" failures="0"`) | PASS |
   | first frontend run | lint · typecheck · `npm test -- --run` · build | exit 0 · 2 TS errors in my new tests (`noUncheckedIndexedAccess`) → fixed · `Tests 67 passed (67)` · built | FAIL→fixed |
   | E2E seed (repo root) | `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` | `E2E RESET DONE: 48 tables emptied` · `5 accounts created, 0 already present` · `PASS E2E database civicbrain_e2e ready with 3 fixed accounts` | PASS |
   | E2E stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E` | `PASS stack 'e2e' is up` | PASS |
   | walkthrough 1 | `npx playwright test --config playwright.walkthrough.config.ts walkthrough/P07` | my test password contained the name → server PASSWORD_POLICY shown on the field (correct); desktop: first register after the backend start > 5 s | FAIL→test fixed |
   | walkthrough 2-4 | same | register → Mailpit OTP → verify → login → home PASS; **Log out → `/login?returnTo=%2Fcitizen`** instead of `/` (fix 1: await navigate then logout; fix 2: `flushSync: true`, ignored - Vite warning "not using the `<RouterProvider>` from `react-router/dom`") → STOP, asked the human | FAIL |
   | plan B (human yes 14:15) | `App.tsx` `RouterProvider` from `react-router/dom`; Vitest then loaded two React Router copies (CJS + ESM, "useContext(...) is null" in 11 tests) → `vitest.config.ts` aliases both entries to the ESM files | `npx vitest run src/components/MobileLayout.test.tsx src/App.test.tsx` → `Tests 11 passed (11)` | PASS |
   | walkthrough 5 | `pwsh … start-all.ps1 -E2E -Restart`, then the walkthrough | `2 passed (11.4s)` (desktop + phone: register, OTP, verify, login, home, logout → `/`, `/citizen` → login, ui.citizen login, **reload keeps the session (refresh cookie through the Vite proxy)**, camera fallback) | PASS |
   | screenshots | opened all 4 PNGs | fallback button text touched the edge when wrapped → `py-2.5 text-center` on the shared button classes, re-shot (walkthrough 6: `2 passed (8.4s)`, 7 after a spec-only lint fix: `2 passed (10.4s)`) | PASS |
   | lint | `npm run lint` | exit 0 (after replacing a literal BOM character in the spec regex by `.trim()`) | PASS |
   | typecheck | `npm run typecheck` | exit 0 | PASS |
   | tests | `npm test -- --run` | `Test Files 14 passed (14)` · `Tests 69 passed (69)` | PASS |
   | build | `npm run build` | `✓ 255 modules transformed` · `✓ built in 505ms` (warning: chunk 601 kB > 500 kB) | PASS |
   | log scan (repo root) | `Select-String -Path logs\backend.log, logs\frontend.log -Pattern 'eyJ…\|password=\|verification code is\|otp.{0,20}\d{6}\|__Host-cb_rt='` | `hits: 0` | PASS |
   | dev stack back | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` | `PASS stack 'dev' is up` (5 services healthy) | PASS |
5. Screenshots (phone 390 px, opened and checked: readable, nothing overlapping or cut off, no horizontal scroll - asserted in the
   spec too): `docs/screenshots/P07_register.png` (filled form, notice v2026-10-v1 in the scroll box, strength "Strong"),
   `P07_otp.png` (6 empty boxes, "Send a new code in 60 s" disabled; taken before the code is typed), `P07_citizen_home.png`
   ("Hello, P07 Walkthrough", Report button, empty recent list, bottom nav), `P07_camera_fallback.png` (headless browser without
   camera: "The camera could not be opened" + "Take a photo with the phone camera" + "Try the in-app camera again").
- DECISION: the refresh cookie stays unconditionally `Secure; HttpOnly; SameSite=Strict; Path=/` without Domain, independent of
  `request.isSecure()` (forward headers are off since P06, so behind the HTTPS tunnel the request looks like http; the `__Host-`
  prefix needs Secure + Path=/ + no Domain; Chrome also accepts Secure cookies on http://localhost). Locked by `RefreshCookieTest`.
- DECISION (logout): `RouterProvider` from `react-router/dom` + the layouts `await navigate('/', { replace: true, flushSync: true })`
  BEFORE `await logout()`. Both parts are needed: React Router's `startNavigation` always passes `await handleLoaders(...)` before
  `completeNavigation`, so a sign-out started in the same click would render first and the portal guard would send the user to
  its login page; `flushSync` commits the landing page before the sign-out render. Test: `MobileLayout.test.tsx`.
- DECISION: login redirect parameter stays `returnTo` (P05 routes, tests and walkthrough use it; docs/05 only says "return URL");
  the prompt's `next` is the same thing. Only a local path of the user's own portal is followed (no open redirect).
- DECISION: after a refresh the user comes from GET /me (the refresh body has no user) and `mustChangePassword` from the JWT claim
  `mcp` (UX only, unsigned decode; the server enforces PASSWORD_CHANGE_REQUIRED). Network/5xx refresh failures during a session
  keep the user signed in (the call fails); 401/403 sign out.
- DECISION: cross-tab refreshes are serialised with the Web Locks API (`navigator.locks`, lock `cb-auth-refresh`) - refresh tokens
  rotate and reuse revokes the family (07 §1), so two tabs must not send the same cookie at once. Without Web Locks: tab-local only.
- DECISION: `CameraCapture` returns `pitchDeg` = DeviceOrientation `beta` and `rollDeg` = `gamma` raw (docs/06 Tier B computes
  θ = 90° − β); tilt indicator green for 45–70° down (90 − β) and |γ| < 5°. `capturedAt` = timestamp of the fresh fix (the API
  checks LOCATION_STALE on it). Fallback accepts JPEG/PNG only (server magic-byte rule). Camera stops at the shutter and on unmount.
- DECISION: `/citizen/new` hosts only the photo step (05 §4 step 2) until P11 builds the wizard; minimal profile at
  `/citizen/profile` (opt-ins via PUT /me, PUBLIC_PHOTO / AI_TRAINING via POST /me/consents; language/export/delete later).
- DECISION: `vitest.config.ts` aliases `react-router` and `react-router/dom` to the package's ESM files (one router copy in
  tests; Node and the browser build already resolve to these files).
- Human answer (2026-10-03 14:41): **Q1 yes** - register → OTP from Mailpit → verify → login → logout worked on the laptop (dev
  stack); after logout the start page with "Report a problem" was shown. **Q2 yes** - all 4 P07 screenshots look right.
- Open / hand-offs: **P21/P27** production bundle is 601 kB (> 500 kB Vite warning, human: ignore for now) - route-level
  `import()` splitting later. **P11** wizard wraps `CameraCapture` + capture session; P11/P13 show the real camera on the phone.
  **P13** HTTPS tunnel: the cookie is already Secure/Path=/ (Task 0). Known: the first register after a backend start can take
  > 5 s (synchronous SMTP + Argon2, cold JVM).

### 2026-10-03 — P06 — Auth backend, E2E seed runner, smoke auth (DONE, human yes 2026-10-03 13:31)
- Requirement(s): FR-01, FR-02, FR-04 (first admin), FR-60, NFR-01; docs/04 §1, §2, §3 (privacy notice), §11; docs/07 §1, §2,
  §6, §7; docs/12 §2; rule 10, rule 50; 09_7DAY §4 (register → OTP → login, generic 401, refresh rotation/reuse).
**Plan** (Claude Code, Auto mode):
1. Error code `PASSWORD_CHANGE_REQUIRED` (403) → docs/12 §2 first, then `ErrorCode` + `en.json`; RFC 9457 extension members
   (`otpId` on 403 EMAIL_NOT_VERIFIED).
2. Config: `RateLimitProperties` (`app.rate-limits.*`; `e2e` per-IP ×100, 100 complaints/24 h), `JwtConfig` (HS256 encoder/decoder;
   validators iss, aud, `typ=at+jwt`, exp ±60 s, `iat ≥ token_valid_after`), `SecurityConfig` role areas + resource server +
   filters (PASSWORD_CHANGE_REQUIRED, 300/min per user).
3. `auth`: AuthController + DTOs · AuthService (register/decoy, verify/resend OTP, login/lockout, logout-all, password change) ·
   OtpService (HMAC, synchronous mail) · RefreshTokenService (`__Host-cb_rt`, rotation, reuse → family revoked) · AccessTokens ·
   PasswordPolicy (+ small blocklist) · AuthEvents · RateLimiter (Bucket4j, in memory).
4. `users`: UserAccounts (create user + consents; used by register, seed, bootstrap) + MeController (GET/PUT /me, POST /me/consents);
   `privacy`: GET /public/privacy-notice; `common/AuditLog`.
5. Runners: AdminBootstrapRunner (`bootstrap-admin`, no TOTP while mfa-required=false), E2eSeedRunner (`e2e-seed`, `_e2e` guard).
Tests first: ITs on Testcontainers PostGIS + Mailpit (`axllent/mailpit:v1.31.3`) for the prompt's list; unit tests for policy,
rate limiter, JWT, OTP codes. Verify: `.\mvnw.cmd -q verify` → E2E smoke (stop → seed-e2e -MinAccounts 3 → -E2E → smoke auth →
-Restart) → log scan. Forgot/reset (FR-03) last, only inside the time box.


**Results** (2026-10-03, verified 13:18 - well inside the 3 h estimate)
1. Files (`backend/`): `auth/` (`api/AuthController`, `AuthDtos`, `RefreshCookie`, `CurrentUser`; `service/AuthService`, `OtpService`,
   `AuthMailer`, `AccessTokens`, `RefreshTokens`, `TokenRevocationValidator`, `PasswordPolicy`, `AuthEvents`; `repo/OtpRepository`,
   `RefreshTokenRepository`) · `users/` (`model/Role`, `UserAccount`; `repo/UserRepository`; `service/UserAccounts`, `MeService`;
   `api/MeController`; `setup/AdminBootstrapRunner`, `E2eSeedRunner`) · `privacy/` (`PrivacyNoticeController`, `PrivacyRepository`,
   `ConsentType`) · `common/` (`RateLimiter`, `RateLimitedException`, `AuditLog`, `Db`, `Masking`, `Times`; `ApiException`/`ApiProblem`
   RFC 9457 extension members; Retry-After in the advice and `ProblemWriter`) · `config/` (`JwtConfig`, `PasswordConfig`,
   `RateLimitProperties`, `PasswordChangeRequiredFilter`, `UserRateLimitFilter`, `SecurityConfig` role areas + resource server,
   `SecurityProblemHandler` → SESSION_REVOKED) · `CivicbrainApplication` (exits after the one-shot profiles) · `application.yml`
   (`app.rate-limits.*`, `server.forward-headers-strategy: native`), `application-e2e.yml` (per-IP ×100, 100 complaints/24 h) ·
   `resources/security/common-passwords.txt`. Docs: `docs/12_ERROR_HANDLING.md` §2 + `PASSWORD_CHANGE_REQUIRED` (403), also in
   `ErrorCode` and `frontend/src/i18n/en.json`.
2. Endpoints: POST `/auth/register` (202; decoy otpId + owner mail for an existing e-mail/phone), `/auth/verify-otp`, `/auth/resend-otp`,
   `/auth/login` (+ `__Host-cb_rt`), `/auth/refresh`, `/auth/logout`, `/auth/logout-all` (bearer), `/auth/password/change` (bearer),
   `/auth/password/forgot` + `/auth/password/reset` (FR-03, built last, inside the time box); GET/PUT `/me`, POST `/me/consents`;
   GET `/public/privacy-notice` (Cache-Control 60 s).
3. Tests (all new): ITs `AuthRegistrationIT` 8 (register → OTP mail in the Mailpit container → verify → login → /me; decoy for e-mail and
   phone with owner mail; OTP code absent from `notification_outbox`/`notifications`/`auth_events`; OTP_EXPIRED; 5 attempts →
   OTP_ATTEMPTS_EXCEEDED; resend 1/60 s → 429 + Retry-After; PASSWORD_POLICY; validation; register 5/h per IP → 429; privacy notice) ·
   `AuthLoginIT` 9 (same 401 body for wrong password/unknown account; 10 failures → 423, wrong while locked → 401, unlock; phone login
   forms; JWT header/claims; tampered/typ JWT/other audience → 401; role areas; must_change_password → 403 PASSWORD_CHANGE_REQUIRED
   then change → old token SESSION_REVOKED, refresh works; logout-all kills existing token + every family; login 30/identifier → 429) ·
   `AuthSessionIT` 5 (rotation + reuse → family dead + REFRESH_REUSE_DETECTED; no CSRF header/wrong/missing Origin → 403; logout
   clears cookie; missing/unknown/expired → 401; officer 1 h vs citizen 7 d idle) · `MeIT` 3 · `PasswordResetIT` 4 ·
   `SetupRunnersIT` 3 (E2eSeedRunner refuses DB `test`; bootstrap refuses when an ADMIN exists; creates a verified Argon2id ADMIN
   without TOTP/forced change, rolled back). Unit: `AccessTokensTest` 7, `PasswordPolicyTest` 12, `RateLimiterTest` 3, `MaskingTest` 10,
   `ProblemExtensionsTest` 5. Honest note: the test classes were written after most of the main code (not one-by-one test-first);
   PasswordResetIT was written before its code. Test infra: `MailpitContainerConfig` + `MailpitClient` (in `@IntegrationTest`),
   `AuthItSupport`; `WebSliceTest` imports `RateLimiter` + a rejecting JwtDecoder (slice has no user table); 2 endpoints added to
   `TestController`. No existing test assertion changed.
4. Runs (in `backend` unless noted):

   | Check | Command | Result | |
   |---|---|---|---|
   | backend run 1 | `.\mvnw.cmd -q verify` | 1 error in my new `AccessTokensTest` (`Jwt.getIssuer()` converts "civicbrain" to a URL) → test reads the claim as a string | FAIL→fixed |
   | backend run 2 | same | unit all green; IT 1 failure: owner "someone tried to register" mail skipped - it shared the 1/60 s OTP bucket with the owner's own code mail → own bucket key (`registration-attempt:<e-mail>`, same limits) | FAIL→fixed |
   | backend run 3 | same | exit 0, 148 tests 0 failures | PASS |
   | seed run 1-2 (repo root) | `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` | `e2e-seed run failed (exit 1)`: non-web profile has no `HttpSecurity` bean → `SecurityConfig` `@ConditionalOnWebApplication(SERVLET)` | FAIL→fixed |
   | backend run 4 (after FR-03) | `.\mvnw.cmd -q verify` | exit 0, **`TOTAL tests=152 failures=0 errors=0 skipped=0`** (surefire 107 + failsafe 45); test log scanned: 0 tokens/passwords/OTPs | PASS |
   | seed (final jar) | `pwsh -NoProfile -File scripts\dev\seed-e2e.ps1 -MinAccounts 3` | `E2E RESET DONE: 48 tables emptied, 27 reference tables kept` · `E2E seed on civicbrain_e2e: 5 accounts created, 0 already present` · `PASS E2E database civicbrain_e2e ready with 3 fixed accounts` | PASS |
   | E2E stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -E2E` | `PASS stack 'e2e' is up`; backend log `Started CivicbrainApplication`, `DB check: 23 wards visible to civicbrain_app` | PASS |
   | smoke | `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage auth` | **`SMOKE AUTH PASSED: 19 / 19`** (run before and again after FR-03) | PASS |
   | log scan | `Select-String -Path logs\backend.log -Pattern 'eyJ[A-Za-z0-9_-]{10,}\|password=\|otp.{0,20}\d{6}'` | no output (0 hits); frontend/worker/ai-api/seed logs 0 hits; 0 ERROR lines | PASS |
   | Mailpit | API search `to:@smoke.local` | `smoke-0a093976@smoke.local \| Your CivicBrain verification code` (first run) | PASS |
   | dev stack back | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` | 5 services healthy; GET `:5173/api/v1/public/privacy-notice` → `200 2026-10-v1 …+05:30 max-age=60, public` | PASS |
   | frontend (en.json) | in `frontend`: `npm run lint` · `npm run typecheck` · `npm test -- --run` | exit 0 · exit 0 · `Tests 39 passed (39)` | PASS |
- DECISION: auth tables through `JdbcClient` (explicit SQL, `CAST(:ip AS inet)`), no JPA entities yet: avoids `ddl-auto=validate`
  type pitfalls (`char(64)`, `inet`) and JPA/JDBC flush ordering. Timestamps are bound as UTC `OffsetDateTime` from the app `Clock`.
- DECISION: `must_change_password` travels as the JWT claim `mcp=true`; the filter allows only GET `/me`, POST `/auth/password/change`,
  `/auth/logout`, `/auth/logout-all`, `/auth/refresh` (PUT `/me` is blocked too - stricter reading of "except /me").
- DECISION: `token_valid_after` arithmetic in whole seconds (JWT `iat` has no fraction): revocation sets
  `greatest(now, trunc(old)+1 s) + 1 s`; tokens get `iat = max(trunc(now), ceil(token_valid_after))` (≤ 2 s in the future right after a
  revocation). The validator compares `iat >= ceil(token_valid_after)` and also rejects inactive users → 401 SESSION_REVOKED.
- DECISION: wrong current password on `/auth/password/change` → 400 VALIDATION_FAILED (field `currentPassword`), not 401 (a 401 would
  trigger the client's silent refresh); it counts towards the 10-failure lockout. `POST /me/consents` → 200 with the `/me` body.
- DECISION: 403 EMAIL_NOT_VERIFIED carries `otpId` (+ `expiresInSec`) as RFC 9457 extension members; inside the 60-s resend limit it
  returns the newest code already sent. Decoy register writes `auth_events` OTP_SENT with `details.decoy=true` (no better V5 type).
- ~~DECISION: `server.forward-headers-strategy: native`~~ - SUPERSEDED by the X-Forwarded-For fix below (Tomcat's default trusted
  list was too wide).
- DECISION: forgot-password has its own 5/h per-IP bucket (`forgot:<ip>`), the owner notice its own per-destination bucket.
  Rate-limit buckets are in memory with a 100,000-bucket safety reset. `mfa-required=true` without TOTP flows fails closed (403
  MFA_REQUIRED for OFFICER/ADMIN) until P25. E2eSeedRunner/AdminBootstrapRunner never set TOTP while `mfa-required=false`.
- **Follow-up (human request with the Q1 answer, 13:20-13:31): X-Forwarded-For check.** Finding: the app did not parse the
  header; `forward-headers-strategy: native` let Tomcat's RemoteIpValve do it. The valve walks from the right, but per Tomcat's
  documented defaults it trusts every private-range address (10/8, 172.16/12, 192.168/16, 100.64/10) as a proxy, not only
  loopback: `1.2.3.4, 10.0.0.5` from the proxy would be keyed on the forged `1.2.3.4`, and a LAN device calling :8080 directly
  could choose its own key (from the documented defaults; the old valve path was not tested).
  DECISION: new `common/ClientIp` is the only reader of X-Forwarded-For: only a loopback peer (Vite proxy / Cloudflare tunnel) is
  trusted; the header (all lines, in order) is walked from the RIGHT, loopback hops are skipped, the first other address is the
  rate-limit/audit IP; an entry that is not an IP literal ends the walk (peer used); literals via `InetAddress.ofLiteral` (no DNS).
  The left-most entry is never used unless it is the right-most non-loopback one. Tomcat rewriting off
  (`server.forward-headers-strategy: none`); `CurrentUser.client` and `MeController` use `ClientIp.of`. Side effect: over the
  tunnel `request.isSecure()` is false again, so no HSTS header there (same as P04).
  Tests: `ClientIpTest` 15 (loopback + `1.2.3.4, 203.0.113.9` → `203.0.113.9`; other forged first entries → same key and the
  same Bucket4j bucket (3rd request 429), `…, 203.0.113.10` → own bucket; loopback hops skipped; private hop kept; broken chain
  → peer; non-loopback peer → header ignored) + `AuthRegistrationIT.behindTheLocalProxyTheLimitIsKeyedOnTheRightMostForwardedAddress`
  (register 5/h keyed on `203.0.113.9` across 5 forged first entries → 6th 429; `auth_otp_codes.request_ip` = `203.0.113.9`).

  | Check | Command | Result | |
  |---|---|---|---|
  | backend run 5 | in `backend`: `.\mvnw.cmd -q verify` | exit 0, **`TOTAL tests=168 failures=0 errors=0 skipped=0`**; test log 0 tokens/passwords/OTPs | PASS |
  | dev backend | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend -Restart` | `PASS stack 'dev' is up`; GET `:5173/api/v1/public/privacy-notice` → 200 | PASS |
  E2E smoke not re-run for this change (requests without the header are keyed exactly as before; covered by the ITs).
- Human answer (2026-10-03 13:31): **Q1 yes** - smoke OTP mails seen in Mailpit.
- Open / hand-offs: **P07** login/register/OTP/forced-change screens use `otpId` from the 403 body and refresh after a password
  change (old access token is revoked). **P14** E2eSeedRunner adds officers/contractors/staff (`SPECS` list). **P28** SPA GET permit
  (07 §2) is not added yet (the P04 test expects `GET /` → 401). Known limit: forgot-password timing differs by the SMTP send time
  for known vs unknown e-mails (real code mail is synchronous). Blocklist is a small local list (07 §1's 100k file = Phase 2).

### 2026-10-03 — D1 follow-up — SCRIPT FIX `Import-DotEnv` empty values (DONE 2026-10-03 12:16, human request)
- **SCRIPT FIX:** same root cause as the D1 gate fix (PowerShell turns `$null` into `""`; since .NET 9
  `SetEnvironmentVariable(name, "")` keeps an empty variable). `scripts/dev/_common.ps1` `Import-DotEnv`: a `.env` line
  `KEY=` (empty value) now calls `SetEnvironmentVariable($key, [NullString]::Value, 'Process')` → the variable is removed (as
  before .NET 9), so Spring defaults like `${KEY:x}` apply again; non-empty values are set as before. The returned dictionary
  is unchanged (`$vars[$key] = $val`, empty string kept), so callers that read it (e.g. verify-all's `.env` hiding) work as before.
- Checks (repo root):

  | Check | Command | Result |
  |---|---|---|
  | env | `pwsh -NoProfile -File scripts\dev\check-env.ps1` | `RESULT: all required checks PASS (8 WARN)` (same 8 WARN as the D1 gate) |
  | restart | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Restart` | stopped backend/frontend/worker/ai-api; `PASS mailpit healthy` · `PASS ai-api healthy` · `PASS worker healthy` · `PASS frontend healthy` · `PASS backend healthy` · `PASS stack 'dev' is up: http://localhost:5173   (Mailpit http://localhost:8025)` |
  | status | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Status` | mailpit, ai-api, worker, frontend, backend: Healthy `yes` (all 5) |
  | backend log (start 06:45 UTC) | `logs/backend.log` | `Successfully validated 6 migrations` · `Started CivicbrainApplication in 5.184 seconds` · `DB check: 23 wards visible to civicbrain_app`; only WARN = Thymeleaf "Cannot find template location" (also in the 10:13 start, not related) |
  | worker log (since restart) | `logs/worker.log` | `worker started: database civicbrain, polling every 2 s …`; WARNING "model files not ready, REQUIRE_MODELS=false" (expected until P08); no ERROR |
- Note: Mailpit is now healthy too (it was not running at the D1 gate; P06 needs it for OTP mails).

### 2026-10-03 — D1 gate (`/phase-gate D1`, "after P05") — PASSED (human yes 2026-10-03 12:12, tag `d1-done`)
- Gate items: `prompts/README.md` "Day gates" D1 row + the 09_BUILD_PLAN_7DAY §4 tests that exist so far (DB SQL tests,
  backend IT "context + Flyway V1-V5 (74 tables, fn_locate_point ward 1)"); 09_7DAY §5 Gate D1 extras (worker claims and
  finishes a job, Flyway history on `civicbrain`). No smoke stage exists yet (`auth` comes with P06).
- **Run 1 (11:37-11:44) - FAIL:** `pwsh -NoProfile -File scripts\dev\verify-all.ps1 -SkipE2E` → `VERIFY-ALL: FAILED`: DB PASS,
  Backend FAIL, AI/frontend NOT RUN (log `logs/verify-all_20261003_113731.txt`). All 13 ITs: `BindValidationException … field
  'baseUrl': rejected value []; … origin System Environment Property "APP_BASE_URL"`. A direct `.\mvnw.cmd -q verify` (in
  `backend`) was green (70 + 13, 0 failures) → the backend code is fine, the wrapper script was wrong. All other items passed.
  CI was not yet confirmed. The commit of the run-1 record was refused by the auto-mode check (red verify-all), so it was left
  staged and goes into this commit.
- **SCRIPT FIX (human yes 2026-10-03, Q1):** root cause (human): PowerShell turns `$null` into `""` for .NET `string`
  parameters, and since .NET 9 `[Environment]::SetEnvironmentVariable(name, "")` sets an empty value instead of deleting the
  variable. `verify-all.ps1` hid the `.env` keys from the test runs with `SetEnvironmentVariable($k, $null)` → the JVM saw
  `APP_BASE_URL=""`, the environment beats `application-test.yml` (`app.base-url: http://localhost:5173`) → `@NotBlank` failed.
  CI never defines the variable → green there. Changes (pass `[NullString]::Value`, the real null):
  1. `scripts/dev/verify-all.ps1` `Invoke-WithEnv`: set loop and restore loop (`$null` value → `[NullString]::Value`, else the value).
  2. `scripts/dev/start-backend.ps1` line 34 (E2E profile: `SMTP_USER`/`SMTP_PASSWORD` unset → no SMTP login to Mailpit).
  3. `scripts/dev/seed-e2e.ps1` line 86 (same two keys for the `e2e-seed` run).
  `scripts/` grep: no other `SetEnvironmentVariable(…, $null)` / `$env:X = $null`. Verified by run 2 (verify-all backend step
  green). Items 2-3 are verified when the E2E stack first runs (P06: `seed-e2e.ps1`, `start-all.ps1 -E2E`); `start-backend.ps1`
  is human-only, so it was edited, not run.
  Observation (not changed): `_common.ps1` `Import-DotEnv` line 55 sets every `.env` key into the process; with .NET 9 a key
  with an empty value (`KEY=`) is now an empty variable instead of an absent one, so a Spring default `${KEY:x}` would no longer
  apply for it. The dev stack starts healthy with the current `.env`.
- **Run 2 (11:57-11:59) - all PASS:**

  | Gate item | Evidence (command → result) | Result |
  |---|---|---|
  | check-env 0 FAIL | `pwsh -NoProfile -File scripts\dev\check-env.ps1` → `RESULT: all required checks PASS (8 WARN)` (long paths, `civicbrain_e2e` not yet (P06), OSRM (Phase 2), mailpit exe (Docker fallback), ffmpeg, k6, 7z, YOLO weights (P08)) | PASS |
  | `verify-all.ps1 -SkipE2E` | `VERIFY-ALL: GREEN (SKIP = component not built yet)` - DB PASS 1 s · Backend PASS 49 s · AI PASS 6 s · Frontend PASS 15 s · E2E SKIP; log `logs/verify-all_20261003_115728.txt` | PASS |
  | SQL tests 4/4 | (verify-all DB step) `ROLE TESTS PASSED: 7 / 7` · `NEGATIVE TESTS PASSED: 6 / 6` · `V4 TESTS PASSED: 11 / 11` · `V5 TESTS PASSED: 11 / 11` | PASS |
  | backend verify green | (verify-all backend step, `mvnw -q -B verify` without `.env` values) reports 11:57/11:58: surefire `tests=70 failures=0 errors=0 skipped=0`, failsafe `tests=13 failures=0 errors=0 skipped=0` | PASS |
  | §4 IT context + Flyway V1-V5, 74 tables, `fn_locate_point` ward 1 | `SchemaIT` `Tests run: 5, Failures: 0, Errors: 0` (`flywayAppliedV1ToV5AndTheGrantsMigration`, `theApplicationTablesOfTheSchemaReferenceExist` (74), `locatePointFindsWardOneInsideTheBoundary`, 23 wards, job enqueue) | PASS |
  | Flyway built `civicbrain` | `logs/backend.log`: `Successfully applied 6 migrations to schema "public", now at version v5` · `DB check: 23 wards visible to civicbrain_app`; `start-all.ps1 -Status` → backend/frontend/ai-api/worker healthy (backend runs with `ddl-auto=validate`) | PASS |
  | seed 500 complaints | `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` (read-only when data exists; checks V5 in `flyway_schema_history` first) → `PASS complaints already has 500 rows - seed skipped` | PASS |
  | AI pytest green (worker claims + finishes a job on `civicbrain_test`) | (verify-all AI step) `All checks passed!` · `82 passed, 1 warning in 4.36s` (0 skipped; `tests/it/test_worker_it.py::test_successful_job_is_succeeded`, retry/dead/stale/timeout/stop cases) | PASS |
  | dataset check passed | `…python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp` → `leakage groups: 0`, `train_mvp.txt: 3258 lines`, `label problems: 0`, exit 0 (same as P03) | PASS |
  | Kaggle run committed | P03 human yes 2026-10-02 20:29 (committed version "Running"); `kaggle_download/civicbrain_yolo_outputs.zip` present (git-ignored, installed in P08) | PASS |
  | frontend lint/typecheck/test/build green | (verify-all frontend step) lint + typecheck exit 0 · `Test Files 6 passed (6)` `Tests 39 passed (39)`; in `frontend`: `npm run build` → `✓ 224 modules transformed` `✓ built in 402ms` | PASS |
  | CI green (GitHub) | human yes 2026-10-03 (Q2): latest CI run on `main` all green; "Run workflow" on `main` (full-history gitleaks, open since P01) → every job green | PASS |
  | `git status` clean | before this commit only this gate's files changed (`docs/PROGRESS.md` + the 3 SCRIPT FIX scripts); clean after commit | PASS |
  | no new TODO/FIXME without issue link | `git grep -n -I -E "TODO\|FIXME"` (code, no docs/lock) → 0 hits | PASS |
  | PROGRESS entry per task | Task log has P01 (+ follow-up), P02, P03, P04, P05; P03b not needed (labels present) | PASS |
  | requirement IDs covered | D1 IDs: NFR-03 → `ai-service/tests/it/test_worker_it.py` (stale jobs requeued); others are doc sections, each with its tests in the P01-P05 entries | PASS |
- Notes: the D1 gate's wording "seed 500 complaints" and "Flyway built `civicbrain`" are proven on the dev DB without psql
  (script + backend log). One read-only Bash listing of mine used `cd backend/target` in run 1, which moved the PowerShell
  location; the next `npm run build` failed with `ENOENT … backend\target\package.json` (nothing written), re-run in
  `frontend` → green. A diagnostic probe of the `$null` behaviour was denied by the auto-mode check and not retried.
- Commit: the auto-mode check refused my commit of the fix + run-2 record (its message named a human-only script); the human
  committed and pushed it as `b0a5f43` "fix(infra): really unset env vars in dev scripts; D1 gate passed - awaiting approval".
  Rule from the human: commit messages never name a human-only script.
- Human answer (2026-10-03 12:12): **Approve D1: yes** → D1 PASSED, commit, push, tag `d1-done`.
- Next: `/run-prompt P06` (auth backend + E2E seed runner + smoke auth; first real run of the fixed `seed-e2e.ps1` and the
  E2E start path).

### 2026-10-03 — P05 — Frontend skeleton (DONE, human yes 2026-10-03 11:28)
- Requirement(s): docs/05_UI_SPEC.md §1, §2, §3 (landing), §7, §8; docs/12_ERROR_HANDLING.md §2, §6; rule 20; docs/09_BUILD_PLAN.md
  P0 step 5 (frontend); 09_BUILD_PLAN_7DAY §1 (Vite layout).
**Plan** (Claude Code, Auto mode):
1. In `frontend`: `npm install` (package.json unchanged) → commit `package-lock.json`; peer conflict → stop and ask.
2. Config by hand: `index.html`, `vite.config.ts` (react + tailwind plugins, 5173 strictPort, `/api` → :8080 `changeOrigin:false`,
   `allowedHosts ['.trycloudflare.com']`), `vitest.config.ts` (jsdom, setup = jest-dom + MSW server, include/exclude per prompt),
   `tsconfig.json`/`.app`/`.node` (strict), `eslint.config.js` (flat), `playwright.walkthrough.config.ts` (CLAUDE.md).
3. Tests first: `StatusBadge.test.tsx` (11 statuses: label + icon), `App.test.tsx` (landing heading, 404, `/officer` → `/login`),
   `api.test.ts` (MSW 422 problem+json → `ApiError{code, fieldErrors}`).
4. `src/lib/api.ts` + `queryClient.ts` (GET 2 retries, not 4xx; mutations 0) · `src/auth/AuthProvider.tsx` placeholder + `RequireAuth`/
   `RequireRole` · `src/i18n` (`en.json`, `errors.<CODE>` for all 38 codes) · router (`/`, `/login`, `/register`, `/citizen/*`,
   `/officer/*`, `/contractor/*`, `/c/:publicRef`, 404) · layouts (Citizen/Contractor bottom nav, Officer left nav) · components
   (`StatusBadge`, `icons/`, `EmptyState`, `ErrorState`, `PageSkeleton`, `Toast`) · landing page (05 §3).
5. Verify: `npm run lint` · `npm run typecheck` · `npm test -- --run` · `npm run build` · `start-all.ps1 -Only frontend` ·
   walkthrough `walkthrough/P05_landing.spec.ts` → `P05_landing_desktop.png` / `P05_landing_mobile.png` · GET
   `:5173/api/v1/public/categories` → backend 401/404 JSON. Record, commit, push; Q1-Q2.

**Results**
1. `npm install` (in `frontend`, Node 24.19.0 / npm 11.17.0) → `added 345 packages … found 0 vulnerabilities`, no peer conflict;
   `package.json` unchanged (0 diff lines); `package-lock.json` (lockfileVersion 3) created, contains the linux-x64 native bindings
   (`@rolldown/binding-linux-x64-gnu`, `@tailwindcss/oxide-linux-x64-gnu`, `lightningcss-linux-x64-gnu`) so CI `npm ci` works.
   `npm ls`: msw **3.0.1** top level as pinned; vitest's `@vitest/mocker` pulls a nested `msw@2.15.0` (optional peer, browser mode
   only, unused). npm 11 "allow-scripts" warning: msw's postinstall not run (it only copies the browser worker file - not needed).
2. Tests first: 5 test files written before the code → first run `Test Files 5 failed (5)` (modules missing) = red.
3. Files (`frontend/`): `index.html`, `public/favicon.svg`, `vite.config.ts`, `vitest.config.ts`, `tsconfig.json`/`.app`/`.node`,
   `eslint.config.js`, `playwright.walkthrough.config.ts`, `walkthrough/P05_landing.spec.ts`; `src/`: `main.tsx`, `App.tsx`,
   `index.css` (Tailwind 4 `@theme`: brand + `--color-status-{neutral,info,warning,success,danger}-{bg,fg,border}`, AA pairs),
   `app/` (`routes.tsx`, `TranslatedPlaceholder`), `lib/` (`api.ts`, `queryClient.ts`, `errorMessage.ts`, `complaintStatus.ts`),
   `auth/` (`authContext`, `AuthProvider` placeholder, `useAuth`, `tokenStore`, `RequireAuth`, `RequireRole`), `i18n/` (`en.json`,
   `index.ts`, typed keys `i18next.d.ts`), `components/` (`StatusBadge`, `icons/` 24 inline SVGs, `EmptyState`, `ErrorState`,
   `PageSkeleton`, `toast/` (`ToastProvider` aria-live, `useToast`), `OfflineBanner`, `PlaceholderPage`, `MobileLayout`, `Brand`,
   `SkipLink`), `features/public` (Landing, PublicShell/Layout, NotFound, Forbidden, RouteError, TrackLink, MessageCard),
   `features/citizen` (CitizenLayout, CitizenComplaintRefPage), `features/contractor/ContractorLayout`, `features/officer/OfficerLayout`,
   `test/` (`setup.ts`, MSW `server.ts`, `handlers.ts`).
   Tests (39): `StatusBadge.test.tsx` 13 (11 statuses: label + `data-icon` per 05 §1 + tone; MERGED fallback; list = DB CHECK) ·
   `App.test.tsx` 9 (landing heading + 3 links, 404, `/officer` → `/login?returnTo=%2Fofficer`, `/c/CB-000123` → login keeps ref,
   citizen at `/officer` → "No access", officer at `/officer/admin` → "No access" inside the layout, officer nav without Admin,
   admin nav with Admin, citizen bottom nav) · `api.test.ts` 8 (MSW: 422 problem → `ApiError{status, code, message=detail,
   fieldErrors, requestId}`, bearer from memory, query params, JSON vs multipart content type, 502 text → DEPENDENCY_UNAVAILABLE +
   `X-Request-Id`, 429 `Retry-After`, network → NETWORK_ERROR, schema mismatch → UNEXPECTED_RESPONSE) · `queryClient.test.ts` 3
   (2 retries, never on 4xx, mutations 0) · `ErrorState.test.tsx` 5 (en.json has all 38 codes of 12 §2, message by code + requestId +
   Try again, INTERNAL_ERROR reference once, unknown code / plain Error → generic text, RATE_LIMITED seconds) · `Toast.test.tsx` 1.
4. First green run: 37/38 - my new test `getByRole('link', 'Go to my start page')` found the header link and the card link →
   scoped to `<main>` (test never passed before). `tsc -b` then failed on `document`/`window` in the walkthrough's `page.evaluate`
   → `tsconfig.node.json` `lib: ["ES2023","DOM"]`.
5. `/verify frontend` (in `frontend`) + build + CI command:

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | frontend | `npm run lint` | `eslint .` - no problems (exit 0) | PASS |
   | frontend | `npm run typecheck` | `tsc -b --noEmit` - no errors (exit 0; 50 `src` files + 3 configs + walkthrough checked) | PASS |
   | frontend | `npm test -- --run` | `Test Files 6 passed (6)` · `Tests 39 passed (39)` | PASS |
   | frontend | `npm run build` | `✓ 224 modules transformed` · `dist/assets/index-*.js 492.49 kB │ gzip: 152.15 kB` · `✓ built` | PASS |
   | frontend | `npm run test:coverage` (CI) | `39 passed` · Lines 87.25 % · Statements 83.8 % · Branches 78.91 % | PASS |
   | stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only frontend` | `PASS frontend healthy` · `PASS stack 'dev' is up: http://localhost:5173`; log `VITE v8.3.1 ready in 390 ms` | PASS |
   | browser | `npx playwright test --config playwright.walkthrough.config.ts walkthrough/P05` | `6 passed (6.9s)` (desktop 1280 + phone 390: landing, Report → `/login?returnTo=%2Fcitizen%2Fnew`, proxy) | PASS |
   | proxy | (same spec) GET `http://localhost:5173/api/v1/public/categories` | `404 {"type":"https://civicbrain.app/errors/NOT_FOUND",…,"code":"NOT_FOUND","detail":"Not found.","requestId":"8c4d00cd-…"}` from the backend | PASS |
6. Screenshots (opened and checked: readable, nothing cut off or overlapping, no horizontal scroll at 390 px, all badges text + icon):
   `docs/screenshots/P05_landing_desktop.png` (1280×800, full page), `docs/screenshots/P05_landing_mobile.png` (390 wide, full page).
- DECISION: client in `src/lib/api.ts` + `src/lib/queryClient.ts` as the prompt says; rule 20's `src/api/` will hold the per-resource
  typed hooks (from P07). Every 2xx body goes through a zod schema (`api.get(path, schema)`), `null` schema = no body.
- DECISION: non-problem error bodies (Vite proxy error, empty) get a code by HTTP status (401 UNAUTHENTICATED, 403 FORBIDDEN, 404
  NOT_FOUND, 413 FILE_TOO_LARGE, 429 RATE_LIMITED, 502-504 DEPENDENCY_UNAVAILABLE, other 5xx INTERNAL_ERROR, other 4xx
  MALFORMED_REQUEST) and the `X-Request-Id` header. Client-only codes: `NETWORK_ERROR` (status 0), `UNEXPECTED_RESPONSE`,
  `UNKNOWN` (in `en.json`). The UI never shows the server `detail` (ErrorState/toasts use `errors.<code>`).
- DECISION: access token in module memory (`auth/tokenStore.ts`), written synchronously by AuthProvider, read by the API client
  (no effect lag); `AuthProvider initialState` is for tests only. P07 adds login, silent refresh, shared refresh promise, 401 retry,
  BroadcastChannel logout.
- DECISION: data router (`createBrowserRouter`/`RouterProvider`), one `errorElement` per portal (12 §6 "error boundary per portal":
  friendly page + Reload); reporting to `POST /client-errors` waits for that endpoint. Track link `/c/:publicRef` (must match
  `CB-\d{6,}`, else 404) → login with `returnTo` → citizen `/citizen/complaints/ref/:publicRef` (placeholder, P11), other roles → their
  start page. Wrong role → "No access" page with "Go to my start page".
- DECISION (MVP OUT): officer nav = Dashboard, Complaints, Action plans, Contractors, Admin (ADMIN only) - no Duplicates queue or
  Notifications log (09_7DAY §1 OUT). Landing has no public-map link (public map OUT); footer: privacy link (`/privacy` placeholder,
  P07 fills it from `GET /public/privacy-notice`), the limits sentence (AI estimates preliminary; wards are analytical units) and
  "Prototype · SPPU final-year project" (honesty rule). Contractor bottom nav has one item (Today) until P22.
- DECISION: i18n keys are typed (`i18n/i18next.d.ts` = `typeof en`), so a missing key fails `tsc`. ESLint also bans
  `dangerouslySetInnerHTML`, `eval`, `any`. MSW 3 renamed `onUnhandledRequest` → `onUnhandledFrame`; setup uses `'error'`.
- Note: `start-all.ps1 -Status` shows Mailpit not healthy (not used in P05; P06 needs it for OTP mails - start-all brings it up).
  Two read-only Bash listings of mine used `cd`, which moved the shell into `frontend\node_modules`; npm still found the project;
  fixed with `Set-Location`, no effect on results.
- Open / hand-offs: **P07** auth screens, `src/api/` hooks, refresh/401 flow, `/privacy` content. **P11** citizen screens incl. the
  track target. **Later** `client-errors` reporting from `RouteErrorPage`; bundle is one 492 kB chunk (route-level `lazy` when the
  portals grow).
- Human answers (2026-10-03 11:28): **Q1 yes** - landing page with "Report a problem" seen at http://localhost:5173 ·
  **Q2 yes** - both screenshots look clean (desktop and phone width).
- DoD: [x] traces (05 §1-§3/§7/§8, 12 §2/§6, rule 20, 09_7DAY §1) [x] tests written first (red run), green [x] loading/empty/error
  components + error codes in `en.json` [x] lint/type clean, no secrets [x] committed `79d097b`, pushed (`2e2f779..79d097b  main -> main`)

### 2026-10-03 — P04 — Backend skeleton, Flyway, demo seed (DONE, human yes 2026-10-03 10:24)
- Requirement(s): docs/02_ARCHITECTURE.md §3, §6; docs/03_DATABASE.md §1, §3, §5; docs/07_SECURITY.md §2, §4;
  docs/12_ERROR_HANDLING.md §1-§3; rule 10; 09_BUILD_PLAN_7DAY §4 "context + Flyway V1-V5 (74 tables, fn_locate_point ward 1)".
**Plan** (Claude Code, Auto mode):
0. Human step: Spring Initializr zip (Boot 4.1.1, Java 25) → `backend\` (`pom.xml`, `mvnw.cmd`).
1. `pom.xml`: + flyway-database-postgresql, hibernate-spatial, spring-boot-testcontainers, testcontainers-postgresql,
   spring-security-test; springdoc 3.x, bucket4j_jdk17-core 8.x, metadata-extractor 2.19.x, openpdf 3.x, bcprov-jdk18on,
   wiremock-standalone 3.x (newest per `versions:display-dependency-updates`); JaCoCo report; Failsafe for `*IT`.
2. Copy-Item `flyway\V1…V5` + `R__civicbrain_grants.sql` → `backend\src\main\resources\db\migration\` (unchanged).
3. `application.yml` + `-dev/-demo/-e2e/-e2e-seed/-bootstrap-admin` skeletons; `src/test/resources/application-test.yml` (fake).
4. `config`: `@Validated @ConfigurationProperties` records, `Clock`, Jackson, `SecurityConfig` (deny-all, 07 §4 headers).
5. `common`: `ApiException`, `ErrorCode` (12 §2), `GlobalExceptionHandler` (RFC 9457 + SQLSTATE 12 §3), `RequestIdFilter`, page record.
6. `workflow.WorkflowActor` + source-scan test for `setStatus(`. 7. `DbStartupCheck` (dev/demo/e2e) logs the ward count.
Tests first: `SchemaIT`, `ErrorAdviceTest`, `SecurityConfigTest`, `ConfigValidationTest`, SQLSTATE mapping test, setStatus scan.
Verify: `.\mvnw.cmd -q verify` · `start-all.ps1 -Only backend` (Flyway 6 migrations, `DB check: 23 wards …`) ·
`db-setup-main.ps1 -Seed` (complaints=500, wards=23) · `db-rebuild-test.ps1 -Force` · P02 hand-off: `-Only ai-api,worker`
→ `/health` 200 `db: ok`. Record, commit, push; Q1-Q2.

**Results**
1. Human step done (2026-10-03): Spring Initializr → Boot **4.1.1**, Java 25, Maven wrapper 3.3.4 / Maven 3.9.16 (`only-script`),
   10 starters + `flyway-database-postgresql` + `thymeleaf-extras-springsecurity6` (both added by Initializr). JDK: Temurin 25.0.4.1.
2. Versions (`.\mvnw.cmd versions:display-dependency-updates -DprocessDependencyManagement=false`, again with
   `-DallowMajorUpdates=false` and `-DallowMinorUpdates=false` to stay inside each named line; JaCoCo via
   `versions:display-plugin-updates`) - newest release of each line, pinned as properties in `pom.xml`:
   springdoc-openapi-starter-webmvc-ui **3.1.1** · bucket4j_jdk17-core **8.21.0** · metadata-extractor **2.19.0** (newest 2.19.x;
   2.21.0 exists, not taken) · openpdf **3.0.5** · bcprov-jdk18on **1.86** · wiremock-standalone **3.13.2** (4.0 is beta) ·
   jacoco-maven-plugin **0.8.15**. Boot-managed (no version in the pom): Flyway 12.4.0 (+ flyway-database-postgresql),
   hibernate-spatial 7.4.5.Final, Testcontainers 2.0.x (`testcontainers-postgresql`), spring-boot-testcontainers,
   spring-security-test. No Excel library (MVP OUT). Failsafe runs `*IT` in `verify`; JaCoCo report → `target/site/jacoco/`.
3. Migrations: `Copy-Item flyway\*.sql backend\src\main\resources\db\migration\` → `Get-FileHash` identical for all 6;
   `bash scripts/ci/check-migrations.sh` → `MIGRATION COPIES: CONSISTENT (6 files)`.
4. Files (`backend/`): `pom.xml`; `application.yml` + `-dev/-demo/-e2e/-e2e-seed/-bootstrap-admin.yml`; test `application-test.yml`;
   `config/` (`AppProperties`, `AuthProperties`, `WhatsAppProperties`, `Secret`, `Base64Key(+Validator)`, `ClockConfig`,
   `SchedulingConfig`, `SecurityConfig`, `SecurityProblemHandler`, `DatabaseStartupCheck`); `common/` (`ErrorCode` 38 codes,
   `ApiException`, `ApiProblem`, `FieldErrorItem`, `GlobalExceptionHandler`, `DbErrorTranslator`, `RequestIdFilter`, `ProblemWriter`,
   `PageResponse`); `workflow/` (`WorkflowActor`, `Actor`, `ActorRole`, `ComplaintStatus`). Tests: `unit/` (ConfigValidationTest 18,
   ErrorAdviceTest 11, SecurityConfigTest 7, DbErrorTranslatorTest 28, ErrorCodeTest 2, PageResponseTest 2,
   StatusChangesOnlyInWorkflowTest 2) + `it/` (SchemaIT 5, WorkflowActorIT 4, ApplicationIT 4; one shared
   `postgis/postgis:18-3.6` container via `@ServiceConnection`).
5. First runs: unit 2 failures → fixed in the code/scanner (never-passed tests): (a) the filter-level 401 sent
   `application/problem+json;charset=UTF-8`, the advice plain `application/problem+json` → `ProblemWriter` no longer adds a charset;
   (b) the `setStatus(` scan flagged `response.setStatus(...)` (servlet HTTP status, not a complaint) → scan skips `response.setStatus(`,
   self-test added for both cases. ITs: all 13 errored with `FATAL: invalid value for parameter "TimeZone": "Asia/Calcutta"` →
   DECISION below. Then 1 failure: Boot 4 health showed `"groups"` (probes on by default) → `management.endpoint.health.probes.enabled=false`.
6. `/verify backend` (in `backend`): `.\mvnw.cmd -q verify` → exit 0, **`Tests run: 83, Failures: 0, Errors: 0, Skipped: 0`**
   (surefire 70 + failsafe 13), JaCoCo report written. Log: Flyway on the container "Successfully applied 6 migrations … now at
   version v5", R__ NOTICE "roles not found - grants skipped" (expected); the weak test secret appears 0 times in the whole log.
7. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend` → `PASS backend healthy`. `logs\backend.log`: profile `dev`,
   `Migrating schema "public" to version "1 - baseline"` … `"5 - capture answers plan release"`, `with repeatable migration
   "civicbrain grants"`, **`Successfully applied 6 migrations to schema "public", now at version v5`** (no baseline row: database was
   empty), `Started CivicbrainApplication in 10.2 s`, **`DB check: 23 wards visible to civicbrain_app`**. Only WARN: Thymeleaf
   "Cannot find template location: classpath:/templates/" (the e-mail layout template comes with the outbox, P10).
   Local GET (python urllib): `/actuator/health` → `200 {"status":"UP"}` with CSP, nosniff, `X-Frame-Options: DENY`,
   Referrer-Policy, Permissions-Policy, COOP, `X-Request-Id`; `/api/v1/x` → `401 application/problem+json`
   `{"type":"https://civicbrain.app/errors/UNAUTHENTICATED",…,"code":"UNAUTHENTICATED","requestId":"…"}`.
8. `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` → **`PASS seed loaded: complaints=500 (synthetic, SUBMITTED, never
   analysed), wards=23, roads=1113`** (seed runs with triggers off → no jobs/outbox rows for demo data).
9. `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → V1-V5 + R__ + seed PASS, `application tables: 74 | wards: 23 |
   … 1/21`, `ROLE 7/7`, `NEGATIVE 6/6`, `V4 11/11`, `V5 11/11`, **`DB TESTS: ALL PASSED`**.
10. P02 hand-off: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only ai-api,worker` → `PASS ai-api healthy`, `PASS worker healthy`;
    AI `/health` → `200 {"status":"ok","db":"ok","osrm":"not used (haversine)","modelsLoaded":false}` (models = P08);
    `logs\worker.log` since the restart: `worker started: database civicbrain, polling every 2 s …`, 0 "no CivicBrain schema" lines.
    Backend, ai-api and worker left running (dev stack).

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | backend | `.\mvnw.cmd -q verify` | `Tests run: 83, Failures: 0, Errors: 0, Skipped: 0` (exit 0) | PASS |
   | migrations | `bash scripts/ci/check-migrations.sh` | `MIGRATION COPIES: CONSISTENT (6 files)` | PASS |
   | stack | `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend` | `PASS backend healthy`; log `Successfully applied 6 migrations`, `DB check: 23 wards visible to civicbrain_app` | PASS |
   | seed | `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` | `complaints=500 …, wards=23, roads=1113` | PASS |
   | db | `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` | `DB TESTS: ALL PASSED` (7/7, 6/6, 11/11, 11/11) | PASS |
   | ai hand-off | `start-all.ps1 -Only ai-api,worker` + GET `/health` | `200 … "db":"ok"` | PASS |
- DECISION: every backend JVM runs in UTC - `TimeZone.setDefault(UTC)` first thing in `main()` (dev `spring-boot:run` and the demo
  jar) and `<argLine>-Duser.timezone=UTC</argLine>` in the pom (surefire + failsafe; JaCoCo prepends its agent). Cause: Windows
  "India Standard Time" → JVM zone `Asia/Calcutta`, which pgjdbc sends as the `TimeZone` startup parameter; the Debian-based
  `postgis/postgis:18-3.6` image no longer knows that legacy name (FATAL at connect). Matches rule 10 (UTC inside, Asia/Kolkata
  only when formatting); JSON log timestamps are now UTC.
- DECISION: secrets are bound as `config.Secret` (toString `[hidden]`) and checked by `@Base64Key` (present, base64, ≥ 32 bytes;
  `TOTP_ENC_KEY` exactly 32), so a failed start says e.g. "JWT_SECRET is missing or not base64 of at least 32 random bytes" without
  echoing the value (ConfigValidationTest proves it). Spring's own keys (`DB_URL`, `DB_USER`, `DB_PASSWORD`, `SMTP_HOST`,
  `SMTP_PORT`, `PG_ADMIN_*` in the real-DB profiles) are required placeholders - Spring names the missing variable.
  `WHATSAPP_PROVIDER=twilio|meta` also requires that provider's keys.
- DECISION: `postgresql` driver moved from `runtime` to compile scope: `DbErrorTranslator` reads `PSQLException.getServerErrorMessage()`
  (SQLSTATE, primary message, constraint name) instead of parsing `getMessage()`.
- DECISION (12 §3 details): 42501 is `ROLE_NOT_ALLOWED` only for the V2 guard text "Role … may not move complaint"; any other
  42501 (missing grant) → 500 (our bug, logged). 23503 "insert or update…" → 404 NOT_FOUND, otherwise 400 VALIDATION_FAILED.
  57014 (statement timeout), class 08/53/57P → 503. `COMPLAINT_NOT_PLANNABLE` detail names the complaint as `CB-000042`.
  Spring MVC 4xx without own handler (405 …) keep their status with code MALFORMED_REQUEST. The 40001/40P01 retry (3×) belongs to the
  service transactions (P06+); the translator gives the final 503.
- DECISION: 10-s statement limit = Hikari `connection-init-sql: SET statement_timeout = '10s'` (every API connection); Flyway on the
  dev/demo/e2e databases uses its own owner connection (no limit). `server.error.include-*=never`, whitelabel off;
  `/v3/api-docs` only in dev/test (springdoc on, Swagger UI off everywhere).
- DECISION: test layout per 08 §1: unit tests in `com.civicbrain.unit.*` (MVC slice `@WebSliceTest` = real `SecurityConfig` +
  filter + advice + a `@TestComponent` test controller, no DB), integration tests in `com.civicbrain.it.*` (`@IntegrationTest`).
  The generated `CivicbrainApplicationTests` (contextLoads, never run) was moved to `it/ApplicationIT.java` (needs a DB).
  `application.properties` (only `spring.application.name`) renamed to `application.yml`.
- Human answers (2026-10-03 10:24): **Q1 yes** - Chrome shows `{"status":"UP"}` at http://localhost:8080/actuator/health ·
  **Q2 yes** - CI job "Backend (mvnw verify, Testcontainers, JaCoCo)" green for `712de71`.
- BLOCKED (not retried): one combined `git add -A; git status --short | Select-String -Pattern '<forbidden-path regex>'` -
  permission-denied (the regex contained the text `.env`, which the deny rules match, as in P01). Replaced by `git add -A` and a
  plain `git status --short` read by eye: 58 source files, no env/secret/storage/logs/target/HELP.md. `gh` is not installed,
  so the CI result (Q2) is checked by the human.
- Open / hand-offs: **P06** - JWT resource server + role areas in `SecurityConfig`, `/auth/refresh`+`/logout` Origin/CSRF check
  (`AppProperties.baseUrl/extraOrigins`), e2e rate limits, `@Retryable` for 40001/40P01. **P10** - Thymeleaf template folder
  (removes the WARN). Mockito prints "self-attaching" (JDK 25 warning only). `backend/HELP.md` (Initializr help) is git-ignored by
  `backend/.gitignore`; the human may delete it.
- DoD: [x] traces (02 §3/§6, 03 §1/§3/§5, 07 §2/§4, 12 §1-§3, 09_7DAY §4) [x] tests written first, green [x] error states
  (Problem Details for 400/401/403/404/409/413/422/500/503) [x] no secrets in yml/logs [x] committed `712de71`, pushed
  (`48dbbb8..712de71  main -> main`)

### 2026-10-02 — P03 — Dataset check, test fixtures, Kaggle package (DONE, human yes 2026-10-02 20:29)
- Requirement(s): docs/11_DATA_SOURCES.md §0, §6; docs/08_TEST_PLAN.md §2 (fixtures); frozen rule "YOLO classes (Step 9)".
**Plan** (Claude Code, Auto mode):
1. Labels present? `docs/INVENTORY.md`: 2,708/351/339 label files, classes 0-3 only → continue (P03b not needed).
2. `ai-service\.venv\Scripts\python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp`
   → exit 0 (exit 1 with < 30 bad lines → `ai-service/training/fix_labels.py`, backups in `data/yolo/backup_labels_P03/`;
   more → ask). Copy `data/yolo/mvp/dataset_report.json` → `docs/reports/dataset_report_local.json`.
3. `ai-service/training/make_test_fixtures.py` (Pillow, deterministic): per class the first TEST image (by name) whose label
   file has exactly one box, of that class, image ≥ 320 px (12 `IMAGE_TOO_SMALL`), box 5-60 % of the image → copy (never move)
   to `tests/fixtures/images/{pothole,garbage,waterlogging,road_damage}_1.jpg` + `<name>.txt` (recorded box); make
   `tiny_200px.jpg` (200×150) + `not_an_image.jpg` (text); write `README.md` (split, original name, licence). Look at each
   picked photo (no readable face / number plate).
4. `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` → zip size + file count.
5. Checks (new Python under `ai-service/`): ruff + pytest. Record, commit, push. Human step: Kaggle upload + committed run; Q1-Q2.
Test: `prepare_mvp_dataset.py` exit 0.

**Results**
1. Labels present (INVENTORY + the check below: 0 missing label files) → P03b not needed.
2. `ai-service\.venv\Scripts\python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp`
   → **exit 0**; again with `--check-images` (Pillow opens every image) → exit 0, same summary:
   ```
   train images= 2708 empty=   0 Pothole=2135 Garbage Accumulation=488 Waterlogging=352 Road Damage=2616
   val   images=  351 empty=   0 Pothole=246 Garbage Accumulation=105 Waterlogging=44 Road Damage=342
   test  images=  339 empty=   0 Pothole=299 Garbage Accumulation=38 Waterlogging=45 Road Damage=321
   leakage groups: 0  (train copies left out: 0)
   train_mvp.txt: 3258 lines, 2708 unique images
   label problems: 0
   ```
   Images per class (train/val/test): Pothole 1044/119/133 · Garbage 99/25/11 · Waterlogging 352/44/45 · Road Damage
   1743/219/218. Oversampled list: 2,708 + 99×2 (garbage ×3) + 352×1 (waterlogging ×2) = 3,258 lines. No `fix_labels.py`
   needed. Report → `docs/reports/dataset_report_local.json` (copy of `data/yolo/mvp/dataset_report.json`; local paths only).
   Weak classes in test: garbage 11 images / 38 boxes, waterlogging 45 - per-class test metrics for garbage will be noisy (P29).
3. Fixtures: `ai-service/training/make_test_fixtures.py` (dry run, then write) → `tests/fixtures/images/`:
   `pothole_1.jpg` ← `India_002154_jpg.rf.b26b…` (S1 RDD2022-India, 720x720, box 11 %) · `garbage_1.jpg` ←
   `IMG_5472_JPG.rf.4a46…` (S3 GarbagePile, 640x640, box 84 %) · `waterlogging_1.jpg` ← `image_101.jpg` (S2, 512x384, box 47 %) ·
   `road_damage_1.jpg` ← `India_000130_jpg.rf.1858…` (S1, 720x720, box 16 %), each + `<name>.txt` (label line) ·
   `tiny_200px.jpg` (200x150 crop of pothole_1, JPEG magic `FF D8 FF`) · `not_an_image.jpg` (text, starts `Civi`) · `README.md`.
   Check: `Get-FileHash` fixture = dataset original for all 4 images, label files identical, originals still in place
   (copy, not move). The 4 photos looked at by eye: no readable face or number plate (distant riders/pedestrians only).
   `git check-ignore` → not ignored (will be committed).
4. `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` → `PASS  kaggle_upload\civicbrain-yolo.zip: 6802 files,
   174.6 MB (3398 images, 3398 label files)`. Zip listing: `yolo/images` 3398 · `yolo/labels` 3398 · `yolo/data.yaml`,
   `class_definition.csv`, `dataset_sources.csv` · `training/{prepare_mvp_dataset.py, train_yolo_mvp.py, kaggle_train_mvp.ipynb}`;
   0 entries from `raw/`, `backup_*`, `archive/`, `mvp/`.
5. In `ai-service`: `.\.venv\Scripts\python.exe -m ruff check .` → `All checks passed!` (covers `training/*.py`) ·
   `.\.venv\Scripts\python.exe -m pytest -q` → `82 passed, 1 warning in 3.38s` (unchanged from P02).

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | data | `…python.exe ai-service\training\prepare_mvp_dataset.py --root data\yolo --out-dir data\yolo\mvp [--check-images]` | `label problems: 0`, `leakage groups: 0`, exit 0 | PASS |
   | package | `pwsh -NoProfile -File scripts\dev\make-kaggle-package.ps1` | `6802 files, 174.6 MB (3398 images, 3398 label files)` | PASS |
   | ai | `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` | PASS |
   | ai | `.\.venv\Scripts\python.exe -m pytest -q` | `82 passed, 1 warning` | PASS |
- DECISION: fixture pick rule = first TEST image by name whose label file has exactly one box of the class, shorter side
  ≥ 320 px (12 `IMAGE_TOO_SMALL`), no EXIF rotation, box 5-60 % of the image preferred. Garbage has no such image (the 4
  single-box garbage test images are close-ups, box 84-100 %) → fallback to the smallest box (84 %). JPEGs copied byte for
  byte, so P08's golden box needs no rescaling. The script refuses to overwrite fixtures without `--force`.
- Licence finding: `waterlogging_1.jpg` comes from S2 "Waterlogging Dataset", whose licence was "To be documented" in
  `data/yolo/dataset_sources.csv` (no licence file in `data/yolo/raw/waterlogging*`); all 45 waterlogging test images are S2
  (`image_<n>`), so `--exclude` cannot avoid it. S1/S3 are CC BY 4.0 (attribution in the fixture README).
  DECISION (human, 2026-10-02 20:29): keep the file for now, repo stays public; an interim "not yet confirmed - replace in P13"
  note went into the fixture README and the log (never committed). The CSV edit was blocked - Excel had the file open - and
  never made.
  RESOLVED (human, 2026-10-03 09:36): S2 licence confirmed - **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/),
  "Waterlogging Dataset" by yolo and car accident detection,
  https://universe.roboflow.com/yolo-and-car-accident-detection-xaltb/waterlogging. Changes: `data/yolo/dataset_sources.csv`
  S2 row only (source URL + `CC BY 4.0`; UTF-8 BOM, delimiter, quoting and line endings kept); `make_test_fixtures.py`
  writes the S2 table row + an attribution line per S2 fixture → `--force` re-run: 10 fixture files byte-identical
  (`Get-FileHash` before/after), only `README.md` changed. Attribution says "converted, not an unchanged copy": the
  downloaded `raw/waterlogging_source/Dataset/images/image_101.jpg` (28,670 B) differs from the dataset/fixture file
  (28,663 B, same 512x384) because `scripts/yolo/convert_waterlogging_masks.py` re-saves every image with Pillow and makes
  the box from the segmentation mask. P13 replacement cancelled.
- Human answers (2026-10-02 20:29): **Q1 yes** - cells 1-4 ended with `OK`, cell 4 `TIMING`: **0.9 min per epoch** ·
  **Q2 yes** - committed version shows "Running".
- Expected Kaggle finish (P08 needs it): committed ≈ 20:29 + 120 epochs × 0.9 min = 108 min + ≈ 10 min (setup, dataset check,
  test-split evaluation, ONNX export) → **≈ 22:30 on 2026-10-02 at the latest**; earlier if early stopping (patience 25)
  ends training. Then: Output tab → `civicbrain_yolo_outputs.zip` → `C:\dev\civicbrain\kaggle_download\` (P08).

### 2026-10-02 — P02 — AI service skeleton, venv and worker loop (DONE, human yes 2026-10-02 19:45)
- Requirement(s): NFR-03 (stale jobs requeued); docs/06_AI_PIPELINE.md §1, §5; docs/02_ARCHITECTURE.md §4, §6;
  docs/04_API_CONTRACT.md §10; docs/07_SECURITY.md §5; docs/12_ERROR_HANDLING.md §7; rule 30.
**Plan** (Claude Code, Auto mode):
1. Venv: `py -3.13 -m venv ai-service\.venv` + `… -m pip install -r ai-service\requirements-dev-win-py313.lock`.
2. `ai-service/pyproject.toml` (pytest markers `models`/`integration`, `testpaths`, ruff 140/py313/E,F,W,I,B,UP).
3. `app/errors.py` (ConfigError, ModelError, DataError, DependencyError), `app/logging_setup.py` (JSON lines),
   `app/config.py` (19 rule-30 keys + `REQUIRE_MODELS=false`, lazy `get_settings()`, ASSUMPTION constants 06 §2.1/§2.4).
4. `app/db.py` (SQLAlchemy 2 + psycopg3 as `civicbrain_ai`, `session_scope()`, `set_system_actor()`).
5. `app/models_check.py` (MANIFEST.json file + folder entries, SHA-256), `app/security.py` (service JWT, PyJWT HS256).
6. `app/main.py`: `GET /health` (no auth), `GET /v1/models` + `POST /v1/jobs/{id}/requeue` (service JWT).
7. `worker/jobs.py` (claim / finish / stale requeue / own-RUNNING requeue / DEAD → `ai_status=FAILED`),
   `worker/handlers.py` (dispatcher), `worker/run.py` (loop, per-job timeout, graceful stop).
8. Tests first: `tests/unit` (settings, JWT, dispatcher, manifest, API) + `tests/it` (`@pytest.mark.integration`,
   `civicbrain_test`: fail → retry, success, stale requeue, own requeue at start, stop flag, DEAD → FAILED).
9. Verify: ruff + pytest; `start-all.ps1 -Only ai-api,worker`; `/health` → `docs/screenshots/P02_health.json`
   (CLAUDE.md: P02 has no frontend); `logs\worker.log`; `start-all.ps1 -Stop -Only worker,ai-api`. Record, commit, push.

**Results**
1. `py -3.13 -m venv ai-service\.venv` → created. The agent's
   `ai-service\.venv\Scripts\python.exe -m pip install -r ai-service\requirements-dev-win-py313.lock` was permission-denied
   (not retried): `.claude/settings.json` lines 126-128 put `…python.exe -m pip install *` on the **ask** list, which wins over
   the allow rule `… -m pip install -r *` (line 63). Human ran the same line in their own window → "done";
   `ai-service\.venv\Scripts\python.exe -m pytest --version` → `pytest 9.1.1`.
2. Files: `ai-service/pyproject.toml`; `app/` (`errors`, `logging_setup`, `config`, `db`, `models_check`, `security`,
   `problems`, `main`); `worker/` (`jobs`, `handlers`, `run`); `tests/conftest.py`; `tests/unit/` (test_config,
   test_security, test_handlers, test_models_check, test_api, test_worker_loop); `tests/it/` (test_worker_it, test_api_it).
3. First pytest run: `database "civicbrain_test" does not exist` (built in P01, gone since) →
   `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → V1-V5 + R__ + seed PASS, `ROLE 7/7`, `NEGATIVE 6/6`,
   `V4 11/11`, `V5 11/11`, `DB TESTS: ALL PASSED`. Second run: a test-helper bug (`ItData._sql` read rows from UPDATE/DELETE)
   broke set-up and cleanup and left rows behind → helper fixed, `db-rebuild-test.ps1 -Force` again (same PASS lines).
4. In `ai-service`: `.\.venv\Scripts\python.exe -m ruff check .` → `All checks passed!` ·
   `.\.venv\Scripts\python.exe -m pytest -q` → `79 passed, 1 warning in 3.01s` (twice in a row: cleanup leaves nothing) ·
   `… -m pytest -q -m integration` (before the last 3 unit tests were added) → `11 passed, 65 deselected`.
   The warning is Starlette's own deprecation notice for `httpx` in its TestClient (no action; not a new dependency).
5. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only ai-api,worker` (1st try) → `PASS ai-api healthy`,
   `FAIL worker exited during start-up`: `relation "jobs" does not exist` - the dev database `civicbrain` is EMPTY until P04
   (P01 decision), and `/health` had said `db: ok` (only `SELECT 1`). Fixed (DECISION below), `start-all -Stop`, 2nd try →
   `PASS worker healthy`; `FAIL ai-api not healthy after 120 s` = `/health` now honestly answers 503 on the empty database.
   `/health` (local GET, body saved as `docs/screenshots/P02_health.json`) → `HTTP 503`
   `{"status":"degraded","db":"schema missing","osrm":"not used (haversine)","modelsLoaded":false}`.
   `logs\worker.log`: JSON lines - `model files not ready, REQUIRE_MODELS=false so the worker still runs: MANIFEST.json: not
   found in MODELS_DIR; …` · `worker started: database civicbrain, polling every 2 s, job types ANALYZE_COMPLAINT,…` ·
   every 10 s `database civicbrain has no CivicBrain schema yet (no jobs table) - the backend's Flyway migrations create it
   (P04) - retrying in 10 s`. `logs\ai-api.log`: JSON lines, `AI API ready (database civicbrain, routing haversine)`.
   `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop -Only worker,ai-api` → `PASS stopped worker` · `PASS stopped ai-api`.
   Claim → handler → finish / retry / DEAD / stale / own-requeue / graceful stop are proven by the integration tests on
   `civicbrain_test`; live polling on the dev stack can only be seen after P04 creates the schema.
6. `/verify ai` before the commit: `test_stop_flag_ends_the_loop_after_the_current_job` failed once
   (`('RUNNING', 1) == ('QUEUED', 0)`: the 2nd job was claimed but never run), then passed 4×. Root cause found and
   reproduced: V4 `fn_claim_jobs` = `UPDATE jobs … WHERE job_id IN (SELECT … LIMIT n FOR UPDATE SKIP LOCKED)`. With a
   nested-loop semi join the LIMIT subquery is re-scanned per outer row, rows already updated by the statement are skipped
   (self-modified), so LIMIT takes the next queued job - forced plan → `fn_claim_jobs(…, 1)` returned **3 rows**; the default
   plan (Hash Semi Join) returned 1. The plan depends on table statistics → intermittent. The worker processed only
   `claimed[0]` and left the extra job RUNNING (recovered only by the 15-min stale requeue).
   Fix in the worker (V1-V5 are frozen): claim rows sorted in queue order (priority, run_after, job_id), all processed;
   after a stop request the not-started ones are released with `fn_finish_job(false, 'Released: …')`; a WARNING logs the
   over-claim. Regression tests `tests/it/test_zz_probe_claim_plan.py` force the plan with planner settings (deterministic):
   V4 over-claim documented, both jobs processed in order, stop releases the second. The stop test now accepts its two
   correct outcomes (2nd job never claimed, or claimed + released) - its earlier `attempts == 0` was wrong for V4.
   Final: `.\.venv\Scripts\python.exe -m ruff check .` → `All checks passed!` · `.\.venv\Scripts\python.exe -m pytest -q`
   → `82 passed, 1 warning` **5 runs in a row** · `start-all.ps1 -Only worker` (new code) → `PASS worker healthy`, then
   `start-all.ps1 -Stop -Only worker,ai-api` → `PASS stopped worker`.

   | Component | Command | Result line | Result |
   |---|---|---|---|
   | ai | `.\.venv\Scripts\python.exe -m ruff check .` | `All checks passed!` | PASS |
   | ai | `.\.venv\Scripts\python.exe -m pytest -q` | `82 passed, 1 warning` (5× in a row; 14 integration on civicbrain_test) | PASS |
   | db | `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` | `DB TESTS: ALL PASSED` (7/7, 6/6, 11/11, 11/11) | PASS |
- DECISION (human, Q2 = no, 2026-10-02 19:45): no migration in the MVP - the worker-side handling stays. KNOWN ISSUE for
  Phase 2: fix `fn_claim_jobs` in a V6 migration with a MATERIALIZED CTE -
  `WITH picked AS MATERIALIZED (SELECT … LIMIT p_limit FOR UPDATE SKIP LOCKED) UPDATE jobs … FROM picked` (+ db test,
  three identical copies); then update `test_v4_claim_can_return_more_rows_than_the_limit` (it will fail on purpose).
- Human answers (2026-10-02 19:45): **Q1 yes** - "schema missing" is expected until P04 runs the migrations ·
  **Q2 no** - keep the worker-side handling, V6 fix in Phase 2 (above) · password shown in the terminal: the human decides
  themselves, nothing for the agent to do.
- DECISION: a missing schema is a dependency problem, not a crash: `/health` checks `jobs` + `fn_claim_jobs` exist
  (`db: ok | schema missing | unavailable`, 503 unless ok); the worker raises `DependencyError` at start-up, logs it and
  retries every 10 s, so it starts polling by itself once Flyway has run (start order does not matter).
- SECURITY NOTE: in the first pytest run (test DB missing) pytest's default long traceback printed the arguments of
  psycopg's `connect()`, i.e. the `PG_ADMIN_PASSWORD` value, to the agent's terminal (not to a file, not committed; it is in
  the Claude Code session transcript). Fix: `--tb=short` in `pyproject.toml` (never prints frame arguments; matters for
  `verify-all.ps1`, which writes pytest output to `logs/`). Human decides whether to change the local `postgres` password
  (pgAdmin + `.env` - human-only).
- DECISION: own RUNNING jobs at worker start (locked_by = WORKER_ID) are finished with `fn_finish_job(id, false,
  'Interrupted: …')` - only V4 functions touch `jobs` (03 §3.8): retry after 1 min (5 min after the 2nd attempt), the 3rd
  attempt → DEAD (same attempt counting as `fn_requeue_stale_jobs`). No direct UPDATE of `jobs`, no new migration.
- DECISION: per-job time limit = handler in a daemon thread, the main thread waits in 0.5-s steps (Windows has no
  SIGALRM; Ctrl+C stays responsive). On timeout the job fails as `JobTimeoutError` and `ctx.cancelled` is set; handlers
  (P12/P17) call `ctx.check_cancelled()` right before their commit, so a late handler never writes results.
- DECISION: service-JWT HMAC key = base64-decoded `AI_SERVICE_JWT_SECRET` (same convention as `JWT_SECRET`; check-env
  already enforces ≥ 32 bytes base64). PyJWT checks signature/HS256-only/aud/iss/required claims; exp/iat/lifetime ≤ 60 s
  are checked in our code against an injectable clock (fixed-clock tests).
- DECISION: `POST /v1/jobs/{id}/requeue` copies a finished job (SUCCEEDED/FAILED/DEAD) into a new QUEUED row
  (`INSERT … SELECT … ON CONFLICT DO NOTHING`, like the V4 triggers) → 202 `{jobId, requeuedFrom, status}`; job still active
  or another active job for the same item → 409 `ALREADY_EXISTS`; unknown → 404 `NOT_FOUND`; errors as RFC 9457 Problem
  Details with `X-Request-Id`. No OpenAPI/docs pages on the internal API.
- DECISION: `GET /health` answers 503 with `status: degraded` when the database is down or has no schema (so start-all
  reports the AI API as unhealthy); `modelsLoaded` = every required file present with the MANIFEST SHA-256.
- DECISION: after `fn_requeue_stale_jobs` (and at start) the worker also sets `ai_status = FAILED` for complaints whose
  latest ANALYZE_COMPLAINT job is DEAD but still look PENDING/PROCESSING (a stale job at max attempts becomes DEAD inside
  the DB function, which returns only a count).
- NOTE for P12: 06 §2.4 says "NULL depth answer → the class prior's depth (Tier C)" but gives no number; `config.py` does
  not invent one - P12 decides and records it.
- Open / hand-offs: **P04** - after Flyway builds `civicbrain`, start `ai-api,worker` once and check `/health` → 200
  `db: ok` and `logs\worker.log` without the "no schema" line. **P12** - set `REQUIRE_MODELS=true`; handlers call
  `ctx.check_cancelled()` before commit. `.claude/settings.json` ask rule vs `pip install -r` allow rule: human's choice.
- DoD: [x] traces (06 §1/§5, 04 §10, 07 §5, 12 §7, NFR-03) [x] tests green [x] states/errors (Problem Details, 401/404/409/503)
  [x] ruff clean [x] committed (see git log: `feat(ai): …`)

### 2026-10-02 — P01 follow-up — Full-history secret scan, `.env` example files readable
- Requirement(s): docs/07_SECURITY.md §5 (secrets only in `.env`, gitleaks 0 findings); D1 gate "CI green".
- Changed: `.claude/settings.json` (human edit, commit `579b14f`): the deny list matched `.env.*` and its `!` exceptions had
  no effect (Claude Code permission rules have no negation; deny wins), so the Read tool refused `.env.example` and
  `.env.test.example`. It now denies the real env files by name (`.env`, `.env.test`, `.env.local`, `.env.*.local`,
  prod/dev/staging/demo/e2e/backup copies, `.env.txt`); `ask`/`allow` unchanged.
- Verified: `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` → `PASS  .claude/settings.json is valid JSON (430 deny rules)` ·
  `PASS  sync-claude: .claude/ is current (10 files)`.
- Secret scan of the whole history (gitleaks/trufflehog not installed → `git grep -I -E` over `git rev-list --all` = 5 commits;
  `main` = `origin/main`, so this is what GitHub has):
  1. Tracked files: env files = only the two examples; no `*.local.json`, key/cert files, logs, `storage/`, weights, backups.
  2. Token formats (private key, AWS, GitHub, Google, Slack, Twilio SK/AC, Stripe, `sk-`, Hugging Face, SendGrid, JWT,
     URL with `user:password@`) → 0 real hits (only the P01 scan-pattern text in this file and `docs/INVENTORY.md`).
  3. `password|secret|token|api_key … = <8+ chars>` → only the CI throw-away DB passwords in `ci.yml` (`postgres`,
     `ci-*-password`), the allowlisted `dGVzdC1vbmx5…` (base64 "test-only-…") and env/`getpass` lookups in scripts.
  4. Personal data: all 24 e-mail addresses are `.local`/`example.com`/`.example`; phone-like numbers are fake
     (`+91900000000x`, `+919111100001`, `9999999999`), OpenStreetMap node IDs (POI GeoJSON) or hex WKB geometry (V1, seed).
  5. `.env.example` + `.env.test.example` (Read tool): placeholders only - `change-me-*`, `REPLACE_WITH_BASE64_32_BYTES`,
     `REPLACE_ME`/`REPLACE_ME_BASE32` (all on the `.gitleaks.toml` allowlist), empty SMTP/Meta/Twilio secrets, Twilio's public
     sandbox sender number, fake `+91900000000x` phones, `@test.local` accounts.
  Result: **0 secrets, 0 real personal data in git history.**
- Still open (D1 "CI green"): gitleaks in CI over the full history → human: Actions → CI → "Run workflow" on `main`.

### 2026-10-02 — P01 — Repo, environment check, databases (DONE, human yes 2026-10-02)
**Plan** (Claude Code, Auto mode):
1. Rules check from memory → log; `sync-claude.ps1 -Check` must end `PASS  sync-claude`.
2. `check-env.ps1` → 0 FAIL (kit-script bugs fixed with a small edit + `SCRIPT FIX:` line; install/PATH = human step).
3. `git init -b main` (no `.git` yet) + `core.autocrlf true`; check `user.name`/`user.email`.
4. Inventory (read-only) → `docs/INVENTORY.md`: research files, counts, format peek, OK / NEEDS ADAPTING / UNKNOWN + prompt;
   stray root files and non-ignored files > 20 MB → `.gitignore` under `# P01: not part of the project`.
5. Secret scan of every `.py/.sql/.json/.ipynb/.md` under `scripts/` and `data/`; literal → `os.environ[...]` (never printed).
6. First commit `chore: kit + existing research files` (`git status --short`: no `.env`, images, `storage/`).
7. `db-setup-main.ps1`, then `db-rebuild-test.ps1 -Force` → V2 6/6, V4 11/11, V5 11/11, roles 7/7.
8. `start-all.ps1 -SelfTest` twice (5 s apart) → `AGENT_CAN_START=yes|no`. 9. `docker version`.
10. Human step: GitHub repo URL → `git remote add origin` + `git push -u origin main`; then Q1–Q3.
Files: `docs/INVENTORY.md`, `docs/PROGRESS.md`, `.gitignore` (if needed), kit scripts only on a real bug. Tests: the SQL tests of step 7.

**Results**
1. Rules loaded (from memory, no file opened): Human-only = `install-all.ps1`, `new-env.ps1`, `new-secret.ps1`, `bootstrap-admin.ps1`,
   `start-all.ps1 -Tunnel`/`-Demo`, every single `start-*.ps1` (`start-e2e`, `start-tunnel`, `start-osrm` …), `prepare-osrm.ps1`, `cloudflared`,
   editing `.env`/`.env.test`, Kaggle/GitHub/Twilio/Gmail web consoles, anything on a phone. Skills: `/run-prompt`, `/start-phase`,
   `/verify`, `/phase-gate`, `/commit-step`.
   `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` → `PASS  sync-claude: .claude/ is current (10 files)`.
2. `pwsh -NoProfile -File scripts\dev\check-env.ps1` → `RESULT: all required checks PASS (13 WARN)` (0 FAIL; no SCRIPT FIX needed).
   WARNs, all expected for later prompts / optional: long paths off (optional), `.venv` (P02), `uv` (only to change deps),
   `civicbrain_test`/`civicbrain_e2e`/login roles (step 7, P06), OSRM data (Phase 2), mailpit binary (Docker fallback), ffmpeg, k6, 7z,
   `storage/` folder, YOLO weights (P08). Note: database `civicbrain` already exists.
3. Inventory → `docs/INVENTORY.md`: every research file the prompts use is present (YOLO 2708/351/339 images + labels, classes 0-3 only;
   priority 500/500 rows; duplicates 109 pairs; Step 10 XGBoost 3.4.1 models; Step 13 routing). No fallback prompt needed (P03b not needed).
   NEEDS ADAPTING: P09 research `ward_id` = ward **number**; P09 duplicate loader uses psycopg2; P17 routing scripts call the public OSRM server.
4. Git: no `.git` existed → `git init -b main`; `git config core.autocrlf true`; identity set (user.name `siddgh123`).
   DECISION: `.gitignore` section `# P01: not part of the project` ignores `data/yolo/archive/backup_before_final_merge/` (2,822 images, 147 MB)
   and `data/yolo/visual_validation/` (20 dataset photos). GIS sources (PDF 5.1 MB, tif, reference png, gpkg) stay committed (≤ 5.1 MB, map
   sources, kit keeps the tif tracked). `KIT_FIXES.md` (human note) committed. No file > 20 MB exists.
5. Secret scan of 126 `.py/.sql/.json/.ipynb/.md/.yaml/.txt` files under `scripts/` + `data/` (password literal, `PGPASSWORD`,
   `postgres://u:p@`, key/token literal) → 0 hits; no edits needed. The 3 DB scripts use env `CIVICBRAIN_DB_PASSWORD` or `getpass`.
   BLOCKED: a read-only `git ls-files --others` filter that contained the text `.env` (to list would-be-committed env files) - denied by the
   `.env` deny rule; not retried. Covered instead by check-env `PASS .gitignore protects .env` and the `git status` check of step 6.
6. First commit: `git add -A` → 427 files staged; root level only `.env.example`/`.env.test.example` of the env files; no images
   (except the GIS reference map png), weights, `storage/`, `logs/`; largest 4.9 MB → `git commit` → `6c2481e chore: kit + existing research files`.
   `git ls-files --eol`: `scripts/ci/*.sh` and `flyway/*.sql` stored + checked out LF (`.gitattributes`), so CI is unaffected by `autocrlf`.
7. `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1` → `PASS roles civicbrain_app and civicbrain_ai ready` ·
   `PASS database civicbrain already exists (left unchanged)`.
   `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` → V1-V5 + R__ + seed PASS; `application tables: 74 | wards: 23 |
   fn_locate_point(18.7440,73.6760) ward_number/ward_id: 1/21`; `ROLE TESTS PASSED: 7 / 7` · `NEGATIVE TESTS PASSED: 6 / 6` ·
   `V4 TESTS PASSED: 11 / 11` · `V5 TESTS PASSED: 11 / 11` · `DB TESTS: ALL PASSED`.
8. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -SelfTest` → `selftest window started`; 5 s later the same command →
   `SELFTEST PASS: the window started by the previous command is still alive` · `PASS stopped selftest`. **AGENT_CAN_START=yes**
9. `docker version` → Server: Docker Desktop 4.93.0, Engine 29.8.1 (running) - Testcontainers can run.

**Open issues / hand-offs**
- **P04:** database `civicbrain` existed BEFORE P01 (Step 0 does not create it; `db-setup-main.ps1` left it unchanged).
  Human answer (2026-10-02): it is EMPTY (0 tables), `civicbrain_backup` was NOT restored.
  DECISION: P04 uses the normal empty-database path - Flyway builds V1-V5 + R__ from scratch (no `baseline-version` override).
- GitHub: remote `origin` = `https://github.com/siddgh123/civicbrain.git` (public). First `git push -u origin main` by the agent →
  `fatal: could not read Username for 'https://github.com': terminal prompts disabled` (Git Credential Manager cannot open its
  sign-in window from the agent's non-interactive terminal) → human step: one push from the human's own PowerShell window.
  After the human's push: `git status -sb` → `## main...origin/main`; `git log -1` → `d666bde (HEAD -> main, origin/main)`;
  agent retry `git push` → `Everything up-to-date` (stored credential works - the agent can push in later prompts).
- **CI security job, first push only (open for the D1 gate "CI green"):** the human's push (`6c2481e..d666bde`) failed the
  gitleaks step: `fatal: ambiguous argument '6c2481e…^..d666bde…': unknown revision` → `scanned ~0 bytes` → exit code 1. Cause:
  on a push, gitleaks-action scans `<first pushed commit>^..<last>`, and the root commit `6c2481e` has no parent. Not a leak
  ("no leaks found", 0 bytes scanned); happens only on a new repository's first push, so `ci.yml` stays unchanged. Later pushes
  scan normally, but the full history (incl. the 427-file root commit) has not been scanned by gitleaks yet → human: Actions →
  CI → "Run workflow" on `main` (`workflow_dispatch` makes gitleaks scan the whole history) and confirm the Security job is green.
  Local full-history scan 2026-10-02: 0 findings (entry "P01 follow-up" above); the CI run is still needed for the gate.
- Human answers: Q1 yes (files on GitHub, no `.env`) · Q2 yes (Database job green) · Q3 yes (INVENTORY complete; agent re-checked it:
  fixed 2 rounded label samples, OSRM server count 6 → 8 files, size units note - no count changed).
- P09: research `ward_id` columns are ward numbers; duplicate loader uses psycopg2 → port the scoring only (docs/INVENTORY.md).
- P17: Step 13 routing scripts call `router.project-osrm.org` → reuse solver settings only (MVP haversine).
- Optional (human): check-env WARN "Windows long paths disabled" - only if a path error ever appears:
  `git config --global core.longpaths true` (the agent never changes global git config).

<!-- Copy this block for every task -->
<!--
### YYYY-MM-DD — P<n>.<task> — <short title>
- Requirement(s): FR-xx / NFR-xx; doc: docs/<file> §<n>
- Changed: <files>
- Tests added/updated: <files>
- Verified: `<command>` → `<summary line>`
- DoD: [ ] traces  [ ] tests green  [ ] states/errors  [ ] lint/type/security clean  [ ] committed <hash>
- Notes / follow-ups:
-->

## Decisions log
| Date | Decision | Why | Who |
|---|---|---|---|
| 2026-09-30 | Requirements frozen v1.0 (docs/01) | Single source of truth before building | Team |
| 2026-09-30 | DB grants moved to repeatable migration `R__civicbrain_grants.sql`; roles template only creates the roles | Grants stay correct on every database Flyway builds (dev, e2e, Testcontainers) and after future migrations | Kit |
| 2026-09-30 | Three databases: `civicbrain` (Flyway), `civicbrain_test` (psql build, SQL + AI tests), `civicbrain_e2e` (Flyway + fixed accounts) | A psql-built DB has no Flyway history, so the backend must never use it; E2E needs resettable data | Kit |
| 2026-09-30 | OSRM image `v26.8.0-debian` pinned in `infra/osrm/docker-compose.yml` | Newest published image; the v26.9.0 release has no image | Kit |
| 2026-09-30 | CI actions pinned by commit SHA; Trivy action v0.35.0 + binary v0.69.3 | March 2026 Trivy supply-chain compromise (GHSA-69fq-xp46-6x23) | Kit |
| 2026-09-30 | `V5__capture_answers_plan_release.sql`: depth answer + A4 flag columns, image quality score, plan release trigger, TOTP/LOGOUT_ALL auth events, `audit_logs.entity_key` | Independent kit review found no storage for FR-10 answers and that reopened complaints could never be planned again | Kit |
| 2026-10-01 | 7-day MVP mode (`09_BUILD_PLAN_7DAY.md`): existing YOLO images only, haversine routing, Twilio sandbox, reduced test list | Deadline 7 Oct 2026; no time for new photos | Team |
| 2026-09-30 | Requirements v1.1: ADMIN bootstrap script, officer tabs Needs review / Rejected with accept / restore | "Officers see everything" and first-admin creation were not buildable | Kit |
| 2026-10-02 | `fn_claim_jobs` over-claim (V4): handled in the worker for the MVP; V6 migration with a MATERIALIZED CTE in Phase 2 | Reproduced in P02 tests; V1-V5 frozen, no new migration during the 7-day MVP | Human (P02 Q2) |
| 2026-10-03 | S2 "Waterlogging Dataset" (yolo and car accident detection, Roboflow) licence = CC BY 4.0: fixture `waterlogging_1.jpg` stays in the public repo with attribution; the interim plan of 2026-10-02 (replace it in P13 if unconfirmed) is cancelled | Licence confirmed by the team; CC BY 4.0 allows redistribution with attribution and a note of changes | Human (P03 follow-up) |

## ASVS L2 checklist evidence (fill in P10)
| Area | Item | Test / evidence |
|---|---|---|
| Authentication | Argon2id, lockout, OTP rules, TOTP for staff | |
| Session | refresh rotation + reuse detection, token_valid_after | |
| Access control | deny-all + matrix test complete | |
| Validation & files | magic bytes, re-encode, size/pixel limits | |
| Headers | CSP, HSTS, nosniff, frame-ancestors, Permissions-Policy | |
| Logging | no secrets/OTP/tokens/full phones in logs | |
| Privacy | notice, consents, requests, public map anonymised | |
