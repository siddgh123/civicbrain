# 09-7DAY — 7-day MVP build plan (Thu 1 Oct → Wed 7 Oct 2026)

**Status: ACTIVE.** The team has 7 days. This file decides **what** gets built and **when**; for every feature it keeps, the other documents (`01`–`08`, `12`) still decide **how** (API shapes, DB rules, security, error codes). Anything in the OUT list below must not be built now, even if another document describes it. After the deadline, continue with the full plan in `09_BUILD_PLAN.md`.

**How it is built: ONE laptop, autopilot.** The agent runs the prompt files `prompts/P01…P30` one by one (`/run-prompt P<nn>`, `prompts/README.md` = order + day plan); it plans, builds, tests and verifies itself and asks the human only yes/no questions and a few hands-on steps (Kaggle upload, phone tests, Twilio/Gmail keys, demo). The member prompts in §5 below are the source the prompt files were written from; follow the prompt files.

Honest expectation: 7 days (really 6 from the evening of 1 Oct) is enough for a working, demonstrable end-to-end MVP only if the laptop works every day, no feature is added after P23 (Day 6) and the cut list (§7) is used without hesitation. It is not enough for the full specification.

---
## 1. Scope

### IN (build these)
| Area | What | Requirement IDs |
|---|---|---|
| Accounts | Citizen register + e-mail OTP, login, JWT access + rotating refresh cookie, logout, lockout, Argon2id; first ADMIN via `bootstrap-admin.ps1`; ADMIN creates officers (+ scope); OFFICER creates contractors (one-time password, must change) | FR-01, FR-02, FR-03 (reset only if time), FR-04, FR-05 |
| Citizen | Capture session, in-app camera + GPS + tilt (`CameraCapture`), complaint wizard incl. depth answer + A4 toggle (stored), server validation, my complaints, detail + timeline + contractor name, "Fixed / Not fixed" + rating | FR-10, FR-11, FR-12, FR-13, FR-15 |
| AI worker | ANALYZE_COMPLAINT: authenticity (capture session, GPS accuracy, GPS freshness, boundary, SHA-256 + pHash reuse, submission rate), text classification, **YOLO trained on the existing images**, measurement **Tier B/C**, estimate, duplicates (FROZEN Step 12), priority (FROZEN Step 11), quality score → best photo, VERIFIED / MERGED | FR-20, FR-21, FR-22, FR-23 (B/C), FR-24, FR-25 |
| Officer | Tabs New / Needs review / In progress / Completed / Rejected, filters (ward, category, priority), table + map with the 23 wards, detail (photo + YOLO box, AI numbers with tier, priority factors, duplicates, timeline), actions reject / merge / accept / restore / remove-from-plan / re-analyse, verify completion | FR-30, FR-31, FR-32, FR-36 |
| Action plan | Generate (live 2 km grouping ≤ 10 jobs with `fn_cluster_jobs` + OR-Tools order within 08:00–17:00 from depot D001, **straight-line road times**), DRAFT view on map, reorder (▲/▼) → re-time, approve, assign to an eligible contractor, cancel, PDF download | FR-33, FR-34, FR-35 (PDF only) |
| Contractor | Worklist, stop detail, inspection (blind tape values + photo + GPS), start, completion with 1–3 proof photos | FR-40, FR-41, FR-42 (without the reuse check) |
| Notifications | Outbox dispatcher; e-mail for every citizen-facing status (Mailpit in dev, Gmail app password for the demo); WhatsApp through the **Twilio sandbox** (text + link; `log` provider if Twilio is not ready); ACTION_PLAN_ASSIGNED to the contractor, COMPLETION_SUBMITTED to the officer | FR-50, FR-51, FR-52 |
| Privacy (minimum) | Privacy notice + consent checkboxes at registration (stored), no personal data outside the owner/officer/contractor views | FR-60 (partial) |
| Security (minimum) | Deny-all security chain, ownership inside queries (404), CSRF header + Origin check on refresh/logout, security headers, rate limits on login/register/complaint, no secrets/OTP/tokens in logs | NFR-01 (core) |

### OUT (after the deadline — list them in the report as "Phase 2")
OSRM road routing (MVP uses straight-line distance) · measurement Tier A (A4 detection; the flag is stored) · field validation + evaluation report (P11) · new Talegaon training photos / dataset v2 (P2 full) · public map, face blur, public-photo approval, BLUR_IMAGE · contractor proof-photo reuse check (ANALYZE_IMAGE) · DPDP data-request screens (export/erasure/correction) · officer TOTP (**stretch goal on Day 6 only if everything else is green**) · Meta WhatsApp templates · Excel export · notification log page · rates editor (rates entered in pgAdmin if needed) · audit/jobs admin pages (use pgAdmin) · duplicate review queue page (UNCERTAIN shows as a badge; officer uses merge) · votes/support · trust score · ALTCHA · ZAP, k6, nightly CI · Marathi UI · full authorization-matrix test.

## 2. MVP decisions (valid only until the deadline)
1. **YOLO uses the existing 3,398 images** (`data/yolo/images/{train,val,test}`), unchanged. `ai-service/training/prepare_mvp_dataset.py` checks labels and leakage and oversamples the weak classes (garbage ×3, waterlogging ×2); `train_yolo_mvp.py` trains on Kaggle with class weighting (`cls_pw=0.5`), evaluates on the untouched test split and exports ONNX. Metrics are reported honestly as "existing test split, not a Talegaon field test". Garbage and waterlogging are expected to be weaker — the citizen's category and the text classifier stay primary; YOLO is supporting evidence (never changes the category).
2. **Routing:** `ROUTING_MODE=haversine` — travel time = straight-line distance × 1.3 (detour factor, ASSUMPTION) at 20 km/h; OR-Tools unchanged. Route drawn as straight segments. `ROUTING_MODE=osrm` is the Phase-2 switch.
3. **WhatsApp:** Twilio sandbox (every demo phone sends `join <code>` to the sandbox number first; the join lasts 72 h, so redo it the day before the demo; free-form messages only reach a phone within 24 h of its last message to the sandbox, so each phone sends "hi" on demo morning) or `WHATSAPP_PROVIDER=log`.
4. **Tests:** only the list in §4 is mandatory (plus the DB tests that already pass). Never delete or weaken those. Everything else in `08_TEST_PLAN.md` is Phase 2.
5. **Phase gates** are replaced by the daily gates in §5 (checked every evening, human-approved in `docs/PROGRESS.md`).
6. **Text classifier:** trained on `data/complaints/synthetic_complaints_500.csv` (24 distinct synthetic texts) + `kit_authored_train.csv` (160 short English/Hinglish/Roman-Marathi sentences written for the kit); checked on `sanity_test_mvp.csv` (40 other kit-written sentences, ≈ 0.90 accuracy with the recipe in `06` §2.2). Reported honestly as "sanity check on kit-written sentences, not real complaints". The citizen's category stays primary.
7. **Single laptop:** one agent account (Claude Code; Antigravity also works), branch `main` only (commit per task, push to GitHub as backup), dev and E2E stacks switched with `start-all.ps1`; the 4 members share the human steps (yes/no answers, phone tests, report, demo).

## 3. Team, laptop, Git (single build laptop)
| Who | Does |
|---|---|
| **Operator** (one member at the build laptop, rotate per day) | types `/run-prompt P<nn>`, answers the yes/no questions, does the human steps of the prompt |
| **Phone testers** (any 2 members) | P13, P24, P30: open the tunnel URL on their phones, report what they see |
| **Report writer** (any member) | P29: report/slides from `docs/reports/` and `docs/PROGRESS.md` |
| **Everyone** | reads the agent's "Done" report; says "no" when something looks wrong |

- One agent account on the build laptop - Claude Code with the team's Claude subscription (or Antigravity) (quota is per account; a second member's account can be signed in when the quota runs out). Heavy prompts with the strongest model while quota is fresh (`10_SETUP_WINDOWS.md` §5).
- Git: branch `main` only; the agent commits after each green task and pushes (GitHub = backup + CI). Tag `d<n>-done` each evening, `mvp-v1` at the end.
- Every prompt still follows the kit: plan → tests (from §4) → code → verify → PROGRESS.md → commit.

## 4. Mandatory tests (MVP)
| Layer | Tests |
|---|---|
| DB | `db-rebuild-test.ps1` → V2 6/6, V4 11/11, V5 11/11, roles 7/7 (already green) · CI `db` job |
| Backend IT (Testcontainers) | context + Flyway V1–V5 (74 tables, `fn_locate_point` ward 1) · register → OTP (Mailpit container) → login · wrong password gives the generic 401 · refresh rotation, reuse → 401 · intake happy path (201, publicRef, job row) · intake errors `CAPTURE_SESSION_INVALID`, `GPS_ACCURACY_TOO_LOW`, `OUTSIDE_BOUNDARY`, `FILE_TYPE_NOT_ALLOWED` · other citizen's complaint → 404 · other firm's contractor → 404 · invalid status move → 409 `INVALID_TRANSITION` · approve + assign plan → complaints ASSIGNED + outbox rows · completion → verify → CLOSED; reject → REOPENED → plannable again |
| AI (pytest) | priority golden test **0 mismatches** · duplicate scoring reproduces 3 pairs of `duplicate_engine_results.csv` · estimate worked example (0.6 × 0.4 m pothole → 0.63 m², ≈ 78 kg mix) · Tier B maths with a known geometry · YOLO smoke: `pothole_1.jpg` gives a Pothole box (`@pytest.mark.models`) · analyse twice → same rows (idempotent) · optimizer: 12 fixed jobs → same order twice, nothing after 17:00 |
| Frontend (Vitest) | login form validation · complaint wizard blocks submit without photo/GPS · `CameraCapture` shows the fallback when the camera is denied |
| API smoke (mandatory) | `tests/smoke/smoke_flow.py` on the freshly seeded E2E stack: `auth` (P06), `intake` (P10), `analysis` (P12), `officer` (P14), `plan` (P18), `contractor` (P20), `close` (P23) - each stage green when its prompt finishes, `--stage all` green from gate D6 (after P23) |
| E2E (optional, Day 6–7) | one Playwright run: citizen submits with the fake camera → sees CB number (P26) |

## 5. Day by day (source of the prompt files)
**Use `prompts/README.md` (day plan, day gates) and `/run-prompt P<nn>`.** The member lines and gate lines below are kept as the source the prompt files were written from; during autopilot the gates in `prompts/README.md` "Day gates" apply (same intent, matched to the prompt order).

### Day 1 — Thu 1 Oct: machines, skeletons, database, YOLO training starts
- **All (by 13:00):** install the MVP software from `10_SETUP_WINDOWS.md` §2 (items 1–6, 8–12, 14, 15, 20; QGIS/k6/Bruno later), repo at `C:\dev\civicbrain`, kit on top, `.env` + `.env.test`, `check-env.ps1` without FAIL, Antigravity settings (`10` §5).
- **M4:** GitHub repo + first push (CI `db` job green) · `db-setup-main.ps1` (roles + empty `civicbrain`; Flyway builds V1–V5 on the first backend start, then `db-setup-main.ps1 -Seed` loads the 500 synthetic complaints - no backup restore needed) · `db-rebuild-test.ps1 -Force` → all PASS.
- **M1 prompt:** "Create the backend skeleton exactly as docs/09_BUILD_PLAN.md P0 step 5 and P1 step 3 (Spring Boot 4.1.1, Java 25, artifactId civicbrain, Flyway with the kit's flyway/*.sql, application.yml placeholders from docs/02_ARCHITECTURE.md §6, application-test.yml with fake values, error model skeleton from docs/12_ERROR_HANDLING.md). Add one Testcontainers IT that applies V1–V5 and asserts 74 tables and fn_locate_point(18.7440, 73.6760) = ward_number 1. Do not add features." → human runs `start-backend.ps1` → Flyway migrates `civicbrain`.
- **M2 prompt:** "Create the frontend skeleton as docs/09_BUILD_PLAN.md P0 step 5 describes (do not run npm create vite; keep package.json unchanged), with router, layout, Tailwind, an auth context placeholder, empty pages for citizen/officer/contractor, and one Vitest smoke test." → human `npm install`, commits `package-lock.json`.
- **M3 (human first):** zip `data/yolo` (images + labels + data.yaml) → Kaggle dataset `civicbrain-yolo` → run `prepare_mvp_dataset.py` locally, fix label problems it reports → on Kaggle: timing run, then full training (`train_yolo_mvp.py`, runs 2–4 h in the background). **Then prompt:** "Create the ai-service skeleton (docs/02_ARCHITECTURE.md §4): app/config.py (lazy pydantic settings per .agents/rules/30), app/main.py with GET /health, worker/run.py loop using fn_claim_jobs/fn_finish_job/fn_requeue_stale_jobs with graceful stop, tests/conftest.py with fake settings, one unit test."
- **Gate D1:** build laptop `check-env.ps1` without FAIL · backend starts, `flyway_schema_history` shows V1–V5 + R__ (fresh database, so no baseline row) · demo seed loaded (500 synthetic complaints) · Vite shows the layout · worker claims and finishes a job (AI integration test on `civicbrain_test`) · YOLO training running or done · CI green.

### Day 2 — Fri 2 Oct: authentication + AI building blocks
- **M1 prompt:** "Implement docs/04_API_CONTRACT.md §1 register, verify-otp, resend-otp, login (no TOTP yet), refresh, logout, logout-all and §2 GET /me, following docs/07_SECURITY.md §1–§2 (Argon2id with BouncyCastle, JWT typ/aud/iss/token_valid_after, rotating __Host-cb_rt cookie with reuse detection, CSRF header + Origin check, lockout, generic errors, rate limits from §11). OTP e-mails are sent synchronously (07 §1). Also AdminBootstrapRunner (profile bootstrap-admin). Tests: the auth rows of docs/09_BUILD_PLAN_7DAY.md §4." → human runs `bootstrap-admin.ps1`.
- **M2 prompt:** "Build register (with privacy notice + consent checkboxes), OTP, login, forced password change screens and the auth provider (token in memory, single shared refresh promise, BroadcastChannel logout) per docs/05_UI_SPEC.md §2–§3 and .agents/rules/20-frontend-react.md; then the CameraCapture component per 05 §4 step 2 and §7. Use MSW mocks until the backend is ready."
- **M3 prompt:** "Implement pipeline/detect.py (load the ONNX from YOLO_WEIGHTS with the checksum in models/MANIFEST.json; imgsz 640, conf 0.25, iou 0.5, CPU) and pipeline/classify.py (TF-IDF + LogisticRegression per docs/06_AI_PIPELINE.md §2.2, trained by ai-service/training/train_text_clf.py on the 500 synthetic complaints; evaluate on data/complaints/sanity_test_mvp.csv) and pipeline/authenticity.py (checks listed in docs/09_BUILD_PLAN_7DAY.md §1). Tests from §4." (Text data comes with the kit: `data/complaints/README.md`. M3 copies one test-split image per class into `tests/fixtures/images/` as `pothole_1.jpg`, `garbage_1.jpg`, `waterlogging_1.jpg`, `road_damage_1.jpg` — the dataset folders themselves are git-ignored.)
- **M4 prompt:** "Port scripts/priority/priority_engine.py into ai-service/pipeline/priority.py and the Step 12 duplicate engine into pipeline/duplicates.py exactly as docs/06_AI_PIPELINE.md §2.6–2.7 (FROZEN). Add the priority golden test and the duplicate reproduction test." (Human downloads all-MiniLM-L6-v2 once into `MODELS_DIR`.)
- **Gate D2:** register → OTP from Mailpit → login works in the browser · admin exists · priority 0 mismatches · duplicates test green · YOLO ONNX detects on 3 test images · `yolo_metrics.json` saved.

### Day 3 — Sat 3 Oct: complaint intake + full AI analysis
- **M1 prompt:** "Implement docs/04_API_CONTRACT.md §5 (capture sessions, complaint create with the exact validation order, multipart photo with magic-byte check, EXIF read then re-encode, storage under STORAGE_ROOT, depth_answer/a4_in_frame), citizen list/detail/timeline, feedback (upsert), GET /files/{id} with ownership 404, and the outbox dispatcher for e-mail per docs/02_ARCHITECTURE.md §5 rules 1–7 and 10. Tests from §4."
- **M2 prompt:** "Build the complaint wizard (05 §4 steps 1–5, depth question with category-specific labels), My complaints and Complaint detail with timeline, loading/empty/error states, calling the real API."
- **M3 prompt:** "Implement pipeline/measure.py (Tier B and Tier C only; Tier A stays for Phase 2), pipeline/estimate.py (06 §2.5), the image quality score (06 §2.6) and the analyze.py orchestrator in the order of 06 §2 table, writing all rows idempotently and moving SUBMITTED → VERIFIED/MERGED as SYSTEM; DEAD job → ai_status FAILED. Tests from §4."
- **M4:** take 20–30 photos of real potholes/garbage near the college **for the demo only** (not for training) · test the phone flow through `start-tunnel.ps1` · help M3 wire priority/duplicates into the orchestrator.
- **Gate D3:** on a phone over the tunnel: capture → submit → CB number → worker → "Under review" in < 60 s · SUBMITTED e-mail in Mailpit · a second report 40 m away with similar text becomes "Linked to CB-…".

### Day 4 — Sun 4 Oct: officer portal + planning engine
- **M1 prompt:** "Implement docs/04_API_CONTRACT.md §6 complaints (tabs incl. NEEDS_REVIEW and REJECTED, geojson, detail, reject/merge/unmerge/accept/restore/remove-from-plan/reanalyze), contractors (create with one-time password, work types, workers as data), §8 admin officers + scopes. Ownership/scope inside queries. Tests from §4."
- **M2 prompt:** "Build the officer portal per docs/05_UI_SPEC.md §5: layout, dashboard cards, complaints tabs with table + WardMap (23 wards from GET /public/wards, grid marker grouping), complaint detail with YOLO box overlay, measurement tier + range, priority factors, duplicates, timeline, action dialogs with reason; contractor create form with one-time password dialog; admin officer page (minimal)."
- **M3 prompt:** "Add the WhatsApp channel behind the notification channel interface: provider twilio (sandbox, text + link) and log, with the {{placeholder}} replacer and provider mapping of docs/02_ARCHITECTURE.md §5; unit tests with WireMock." (pair with M1)
- **M4 prompt:** "Implement OPTIMIZE_PLAN per docs/06_AI_PIPELINE.md §3 with ROUTING_MODE=haversine (travel minutes = haversine km × 1.3 / 20 km/h × 60; straight-line route geometry), fn_cluster_jobs grouping, OR-Tools settings as §3 step 4, DRAFT plans + items + revision 1, dropped jobs with reasons, and RETIME. Optimizer tests from docs/09_BUILD_PLAN_7DAY.md §4."
- **Gate D4:** officer logs in, sees the phone complaints on the map with YOLO box and priority, rejects/merges/accepts · contractor created · WhatsApp sandbox message on a phone for SUBMITTED · optimizer test green.

### Day 5 — Mon 5 Oct: plans end to end + contractor backend (last day for new features)
- **M1 prompt:** "Implement the plan endpoints of docs/04_API_CONTRACT.md §6 (generate → optimizer_runs, poll, get, PUT re-order → RETIME, approve/assign via fn_approve_action_plan/fn_assign_action_plan with the P0001 mapping of 12 §3, cancel, plan lifecycle IN_PROGRESS/COMPLETED) and the PDF export (OpenPDF: plan header, stop table, straight-line route sketch). ACTION_PLAN_ASSIGNED + ASSIGNED notifications to every owner incl. merged children. Tests from §4."
- **M2 prompt:** "Build the action plan builder (05 §5): filters → generate → poll → map with numbered stops and straight route lines, stop list with ▲/▼ reorder and remove, totals, dropped jobs, approve, assign (eligible contractors only), cancel, download PDF."
- **M4 prompt:** "Implement docs/04_API_CONTRACT.md §7 contractor endpoints (worklist from v_contractor_worklist, plan, complaint detail without citizen contact data, capture sessions, inspection multipart, start, completion multipart with 1–3 proof photos; access only via an ACTIVE item in an ASSIGNED/IN_PROGRESS plan of the caller's firm). Tests from §4." (M1 reviews.)
- **M3:** AI polish (re-analyse, performance < 60 s on the slowest laptop, MANIFEST + checksums), notification bodies for INSPECTED/IN_PROGRESS/COMPLETED/CLOSED/REOPENED.
- **Gate D5:** officer generates a plan for ≥ 5 verified complaints, reorders, approves, assigns → both citizens get e-mail (+ WhatsApp) "Contractor X assigned, date D" · PDF downloads · contractor API tests green. **Feature freeze tonight.**

### Day 6 — Tue 6 Oct: contractor screens, closing the loop, security pass
- **M2 prompt:** "Build the contractor mobile screens (05 §6): Today list with map and Navigate links, stop detail, inspection form (camera, tape values, no AI values shown, distance warning), start, completion form with proof photos; and the citizen Fixed/Not fixed + rating UI."
- **M1 prompt:** "Implement verify-completion (approve → CLOSED, reject → REOPENED), citizen feedback reopen, plan status updates, COMPLETION_SUBMITTED to the officer; then a security pass per docs/07_SECURITY.md §2–§4 and §6 for the MVP endpoints (deny-all check, 404 ownership tests, headers test, no secrets/OTP/tokens in logs)." Stretch only if all gates are green: officer TOTP (07 §1).
- **M3:** COMPLETED e-mail with the proof photo inline; fix bugs from the full-flow runs.
- **M4:** full-flow test on 2 phones + laptop, log every bug in PROGRESS.md; optional Playwright happy path; create demo accounts (`bootstrap-admin.ps1` → officer → contractor), demo data, `backup-db.ps1`.
- **Gate D6:** the complete flow runs on the demo laptop with 2 phones: citizen → AI → officer → plan → assign → inspect → start → complete with proof → officer verify → CLOSED → citizen rates; each citizen-facing status sends e-mail (+ WhatsApp).

### Day 7 — Wed 7 Oct: bug bash, demo readiness, freeze
- **Morning:** everyone runs the flow in another member's role; fix bugs only (no features; after 12:00 only blocker fixes).
- **Afternoon:** demo laptop per `13_DEMO_AND_DEPLOY.md` §1 (build the jar with the SPA inside, `start-backend.ps1 -Prod`, tunnel `-Demo`, Gmail app password, Twilio sandbox joins redone) · `backup-db.ps1 -CopyTo <USB>` · rehearse the demo twice · report/slides: architecture, YOLO metrics from `yolo_metrics.json` (honest, existing test split), limitations + Phase-2 list (§1 OUT).
- **Gate D7:** full flow twice without error on the demo laptop · `main` tagged `mvp-v1` · backup on USB.

## 6. Daily rhythm (one laptop)
Morning: operator checks `start-all.ps1 -Status` output in the agent's first answer, then runs the day's prompts in order (new agent chat per prompt). While a prompt runs, the others prepare the human steps of the next one (accounts, phones, report text). Evening: `/phase-gate D<n>` → yes/no → tag. A prompt stuck for 2 hours → switch model, or say yes to the agent's cut proposal (§7).

## 7. If you fall behind (cut in this order)
1. Optional Playwright test · 2. PDF route sketch (keep the table) · 3. WhatsApp (keep `log`, show e-mails) · 4. Plan re-order/re-time (approve the generated order) · 5. Contractor workers/staff data · 6. Duplicate merge UI actions (automatic MERGED still works) · 7. Needs review / Rejected tabs (keep New / In progress / Completed).
Never cut: authentication, ownership checks, the DB status rules, the AI analysis, the notifications to citizens with the contractor name, the proof-photo loop.
