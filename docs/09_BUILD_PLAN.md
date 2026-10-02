# 09 — Build Plan (P0 → P12) with gates

> **Until 7 Oct 2026 the active plan is `09_BUILD_PLAN_7DAY.md` (7-day MVP).** This full plan continues after the deadline (Phase 2).

How to use: one phase = one Antigravity conversation (start it with `/start-phase P<n>`). **Prerequisites** (a phase may start when these are PASSED and approved; two tracks run in parallel — app and ML): P1←P0 · P2←P0 · P3←P1 · P4←P3 · P5←P4 · P6←P5 + P2 · P7←P6 · P8←P7 · P9←P8 · P10←P9 · P11←P2 + P6 · P12←P10 + P11. Inside a phase the agent works task by task: plan → tests → code → run → PROGRESS.md → commit. A phase is closed only by `/phase-gate P<n>` showing every gate item green **and** a human approving. Estimates assume 4 members working part-time with the agent; the ML track (P2, P11) runs in parallel.

```
Week:  1    2    3    4    5    6    7    8    9    10   11   12   13   14   15
P0 ██
P1      ██
P2 (ML)  ████████████████                 P11 (ML) ████████████
P3           ███
P4              ███
P5                 ██
P6                   ████
P7                       ███
P8                          ████
P9                              ███
P10                                ██
P12                                    ██
```

## Git workflow (all phases)
`main` is protected; work on `phase/p<n>-<topic>` branches; open a PR when the phase gate is green; CI must be green; one teammate reviews; squash-merge. Tag each merged phase `p<n>-done`. Never let the agent `git push --force`, `reset --hard` or `clean`.

---
## P0 — Machines, repo, Antigravity (owner: all; 3–5 days)
**Goal:** every laptop can build and test an empty project; Antigravity is configured safely.
1. Install software exactly as `10_SETUP_WINDOWS.md` (versions pinned) and run `scripts/dev/check-env.ps1` (prints each tool's version and PASS/FAIL).
2. Move the project out of OneDrive to `C:\dev\civicbrain` (OneDrive locks/syncs `node_modules`, `.venv`, `target` and breaks builds). Create the GitHub repo (public is recommended: free CI, and Ultralytics AGPL-3.0 expects the code to be open).
3. Copy this kit into the repo root (it brings `.gitignore`, `.gitattributes`, `scripts/dev`, `scripts/ci`, `infra/osrm`, `.github/workflows/ci.yml`). The `.gitignore` keeps `data/yolo/images|labels|raw|backup_*`, `.env*`, `storage/`, weights out of git; `data/**/*.csv`, `scripts/`, `docs/steps/` stay in. Create `.env` and `.env.test` from the examples (`00_README_FIRST.md` steps 3–4).
4. Antigravity settings on every laptop (`10_SETUP_WINDOWS.md` §5): Request Review for terminal and files, deny list, browser allowlist localhost only, no real secrets in `.env`.
5. Create skeletons (agent, prompt below): `backend/` (start.spring.io: Boot 4.1.1, Java 25, Maven wrapper, artifactId `civicbrain`, deps from §P3; `application.yml` with env placeholders from `02_ARCHITECTURE.md` §6), `frontend/` (do **not** run `npm create vite` — the folder already holds the pinned `package.json`, which must not change; write by hand `index.html`, `src/main.tsx`, `src/App.tsx`, `src/test/setup.ts`, `vite.config.ts` (the `/api` proxy to `http://localhost:8080`, `server.allowedHosts: ['.trycloudflare.com']`), `vitest.config.ts`, `tsconfig*.json`, `eslint.config.js`, one smoke test; then ask the human to run `npm install`), `ai-service/` (venv Python 3.13 + kit `requirements-dev.txt`; `app/main.py` with `/health`, `worker/run.py` stub, `tests/`). `infra/osrm/`, `scripts/dev/`, `scripts/ci/` and the CI workflow already come with the kit — do not recreate them. The human runs `npm install` once on Windows and commits `package-lock.json` (CI needs it).
**Prompt:** `/start-phase P0` then "Create the project skeletons described in docs/09_BUILD_PLAN.md P0 step 5 and docs/02_ARCHITECTURE.md §2–4. Do not add features and do not modify the kit files (scripts/, infra/, .github/, db/, flyway/). Each skeleton must build and have one passing smoke test."
**Gate:** `check-env.ps1` without FAIL on all 4 laptops · `.\mvnw.cmd -q verify` green (1 context test on Testcontainers `postgis/postgis:18-3.6` — never the local databases; Docker Desktop running) · `npm run lint && npm run typecheck && npm test -- --run` green · `pytest -q` green (1 test) · `verify-all.ps1 -SkipE2E -SkipDb` green · CI green on GitHub (all five jobs) · Antigravity deny list screenshot in `docs/PROGRESS.md` · **rules/skills load check:** in a fresh Antigravity chat the agent, without opening files, quotes safety rule 5 and lists the four skills (screenshot in PROGRESS; if they did not load, copy `.agents/` to `.agent/` and retest; if `/start-phase` is not recognised as a command, type "use the start-phase skill for P<n>").

## P1 — Database foundation (owner: M4 + M1; 3–5 days)
**Goal:** one correct database, reproducible from scratch and by upgrade.
1. Human: `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1` → creates the login roles with the `.env` passwords, builds `civicbrain_test` from `flyway/` (+ seed) and prints `DB TESTS: ALL PASSED` (V2 6/6, V4 11/11, V5 11/11, roles 7/7).
2. Human: restore `civicbrain_backup` into a new database `civicbrain` (pgAdmin → Restore). Do **not** run V2–V5 by hand on it — Flyway applies them in step 3 (`03_DATABASE.md` §1).
3. Agent: copy `flyway/*.sql` (V1–V5 **and** `R__civicbrain_grants.sql`) into `backend/src/main/resources/db/migration/`; configure Flyway (`baseline-on-migrate: true`, `baseline-version: 1`, `placeholder-replacement: false`, `spring.flyway.user/password` = `PG_ADMIN_USER/PG_ADMIN_PASSWORD`, datasource = `DB_USER/DB_PASSWORD`), add `org.flywaydb:flyway-database-postgresql` (without it Flyway fails on PostgreSQL 18). Human then starts the backend once (`start-backend.ps1`) → Flyway applies V2–V5 + R__ to `civicbrain`; check `flyway_schema_history` in pgAdmin.
4. **Decision #1 execution (problem 1):** the human exports the DB complaints with the kit's `scripts/audit/export_db_complaints.py --like <the CSV each Step script reads>` (run with `ai-service\.venv\Scripts\python`; it reads `.env`, so the agent does not run it) (it copies that CSV's columns and stops on any column it cannot match) and re-run Step 10, 11, 13 scripts on that export with their frozen settings; reload `step13_*` from the new outputs with the existing SQL generators; record before/after in `docs/steps/STEP13_README.md`.
5. GIS check: open `gis/tdmc_wards_clean_v2.geojson` over `gis/raw/official_sources/tdmc_boundary_georeferenced.tif` in QGIS; confirm or correct the 4 large disputed areas listed in `gis/WARD_QA_REPORT.md`; if corrected, create `V6__wards_manual_fix.sql` (next free number; same pattern as V3) and re-run the ward checks.
**Prompt:** `/start-phase P1` then "Wire Flyway and the database into the backend as in docs/03_DATABASE.md; add an integration test that starts Testcontainers postgis/postgis:18-3.6, applies V1–V5 + R__civicbrain_grants (roles absent there, so it only logs a NOTICE) and asserts: the 74 application tables of db/SCHEMA_REFERENCE_after_V5.sql exist, 23 wards covering the boundary with no overlap, fn_locate_point(18.7440, 73.6760) returns ward_number 1 (ward_id 21), complaint insert enqueues one job."
**Gate:** `db-rebuild-test.ps1` → "NEGATIVE TESTS PASSED: 6 / 6", "V4 TESTS PASSED: 11 / 11", "V5 TESTS PASSED: 11 / 11", "ROLE TESTS PASSED: 7 / 7" on `civicbrain_test` · Flyway migrate + validate clean on `civicbrain` (backend starts without errors; `flyway_schema_history` shows 1 baseline, V2, V3, V4, V5, R__) · CI `db` job green · backend IT above green · Step 13 rerun report committed (jobs by work type now match DB categories: 0 mismatches).

## P2 — ML data and models (owner: M3; parallel, 3–5 weeks)
Follow `11_DATA_SOURCES.md`. Outputs, each with a reproducible script under `ai-service/training/`:
1. Dataset v2: official RDD2022 India (CC BY-SA 4.0; D40 → Pothole, D00/D10/D20 → Road Damage) + current garbage/waterlogging sets + **local Talegaon photos** (≥ 150 garbage, ≥ 150 waterlogging, ≥ 100 pothole, ≥ 100 road damage, plus 100 no-defect backgrounds); de-duplicate (imagededup), split by street/session 70/15/15, **frozen Talegaon test set**; the images live in git-ignored `data/yolo_v2/`, but `data/yolo/data_v2.yaml` and `data/yolo/DATASET_CARD.md` (sources, licences, counts) are committed.
2. Train YOLOv8s (and YOLOv8n) on Kaggle/Colab with the recipe in `11_DATA_SOURCES.md` §2.4; export ONNX; `yolo_metrics.json` (P, R, mAP50, mAP50-95 overall + per class, on both test sets) + confusion matrix PNG; CPU latency measured in the worker.
3. Text classifier on synthetic + real multilingual complaints; `text_clf_metrics.json` (macro-F1 on the real test set).
4. Record everything in `ai-service/models/MANIFEST.json` (file, SHA-256, dataset version, metrics).
**Gate:** model files + MANIFEST checksums verified by `pytest tests/unit/test_models_present.py` · metrics JSON exist and are reported honestly (no threshold is invented; the report states them) · golden images recorded for P6 tests.

## P3 — Backend foundation & security (owner: M1; 1.5 weeks)
Dependencies: webmvc, validation, data-jpa, security, oauth2-resource-server (JWT), flyway + flyway-database-postgresql, postgresql, hibernate-spatial, mail, thymeleaf, actuator, springdoc-openapi 3.x (Boot-4 line), bucket4j_jdk17-core 8.20.x, metadata-extractor, openpdf 3.x + openpdf-html, poi-ooxml, bcprov-jdk18on (BouncyCastle, needed by `Argon2PasswordEncoder`; explicit version), db-scheduler (optional); test: Boot 4 test starters, spring-security-test, testcontainers-postgresql 2.0.x (+ a generic container for Mailpit), WireMock.
Tasks: config properties + fail-fast env validation · error model (`12_ERROR_HANDLING.md`) · request-id filter + JSON logging · security chain (deny-all), JWT issue/verify with `token_valid_after`, refresh rotation + reuse detection, CSRF header/origin check, headers · register/OTP/login/lockout/forgot/reset/change · TOTP setup/verify · rate limits · audit service · `/me` · admin officers & scopes · officer contractors/workers/equipment · WorkflowActor helper · authorization matrix test scaffold · `application-test.yml` (fake settings, `08_TEST_PLAN.md` §1) · `AdminBootstrapRunner` (profile `bootstrap-admin`, rule `10-backend-spring.md`) + human runs `scripts/dev/bootstrap-admin.ps1` on `civicbrain`.
**Prompt:** `/start-phase P3` — read 04 §1–2, §6 (contractors), §8, §11; 07 §1–6; 12; 03 §3.
**Gate:** all auth tests in `08_TEST_PLAN.md` §3 green · authorization matrix green and complete for existing endpoints · OpenAPI snapshot committed · coverage ≥ 70 % · headers test green.

## P4 — Citizen portal + complaint intake (owner: M2 + M1; 1.5 weeks)
Frontend foundation (router, auth provider, query client, i18n, layout, components from `05_UI_SPEC.md` §7) · landing, register/OTP, login, profile/consents · citizen home, new complaint wizard with `CameraCapture`, my complaints, detail + timeline, feedback, public map + support · backend: capture sessions, complaint create (validation order in `04` §5), file pipeline + `/files/{id}`, citizen queries, feedback/reopen (upsert), votes, public endpoints; store `depth_answer`/`a4_in_frame` (V5); enqueue BLUR_IMAGE for consenting owners once P7 enables it · E2E infrastructure: `E2eSeedRunner` (`@Profile("e2e-seed")`, non-web, refuses unless the JDBC database name ends with `_e2e`, creates the fixed accounts of `08_TEST_PLAN.md` §2 from `.env.test` through the real services, then exits) and profile `e2e` settings; `frontend/playwright.config.ts` per `08_TEST_PLAN.md` §4; human runs `seed-e2e.ps1` + `start-e2e.ps1`.
**Gate:** intake tests (§3) green · E2E-01 passes up to "Received" (worker not yet built: job row exists) · axe on citizen pages · manual check on one Android and one iPhone over the Cloudflare tunnel (camera opens, GPS accuracy shown, submit works) recorded in PROGRESS.

## P5 — Notifications (owner: M1; 1 week)
Outbox dispatcher per the 10 rules in `02_ARCHITECTURE.md` §5 (FOR UPDATE SKIP LOCKED, batch 50, every 10 s, recipients, `{{name}}` replacer + Thymeleaf e-mail layout with inline photo, provider mapping, WhatsApp photo handling), channels `log`/SMTP/Meta/Twilio behind one interface, retries, webhooks with signature checks, `/me/notifications`, officer notification log.
**Gate:** notification tests green (Mailpit + WireMock) · dedupe proven · with `WHATSAPP_PROVIDER=meta` one real template message received on a team phone (screenshot in PROGRESS).

## P6 — AI worker v1 (owner: M3 + M4; 2 weeks)
Worker loop, config/model loading with checksum, pipeline steps 1–9 of `06_AI_PIPELINE.md` §2 incl. 4b/4c (quality score → best photo), re-analysis rules, DEAD → `ai_status = FAILED` (measurement Tier B/C now, Tier A in P11), daily priority recompute, FastAPI health/models/requeue with service JWT.
**Gate:** AI unit + integration tests green (golden images, priority 0 mismatches, duplicate reproduction, idempotency, retry/DEAD) · E2E-01 fully green (status "Under review" within 60 s) · E2E-02 green · analysis of one complaint < 60 s on the slowest team laptop.

## P7 — Officer dashboard (owner: M2 + M1; 1.5 weeks)
Queue tabs (New / Needs review / In progress / Completed / Rejected) + filters + table/map, complaint detail tabs, actions (reject/merge/unmerge/reclassify/override/reanalyze/accept/restore/remove-from-plan), duplicates review, contractor management UI, public-photo approval with blur preview (BLUR_IMAGE job with officer rectangles, `BLUR_ENABLED=true`, YuNet file in MODELS_DIR), stats cards, admin pages (officers, jobs, audit, rates, privacy requests).
**Gate:** officer API tests + matrix rows green · officer out-of-scope sees nothing (tested) · E2E-06 green · axe on officer pages.

## P8 — Action plans (owner: M4 + M2; 2 weeks)
OSRM running (human: download the extract, `prepare-osrm.ps1`, `start-osrm.ps1` → PASS; `infra/osrm/README.md`), optimizer job (group → OSRM → OR-Tools → plans), RETIME, plan APIs, plan builder UI (map, drag reorder, dropped jobs, versions), approve/assign via DB functions, PDF (OpenPDF, route drawn with Java2D on a plain background — no map tiles) and XLSX (Apache POI) exports.
**Gate:** optimizer tests green (determinism, 17:00 limit, reasons, 10 s) · E2E-03 and E2E-07 green · a plan for 10 real DB complaints generated in < 15 s end to end.

## P9 — Contractor portal & closure (owner: M2 + M1; 1.5 weeks)
Worklist, stop detail, inspection (blind measurement), start, completion with proof and reuse check (backend enqueues ANALYZE_IMAGE per proof/inspection photo; worker `06_AI_PIPELINE.md` §2.8), plan status IN_PROGRESS/COMPLETED updates, officer verification, citizen confirm/rate/reopen (reopened complaints are plannable again — V5), trust-score updates.
**Gate:** field tests green · E2E-04, E2E-05 and E2E-08 (contractor pages) green · **full lifecycle E2E (01→05) green in three consecutive `verify-all.ps1` runs** (each reseeds `civicbrain_e2e`).

## P10 — Privacy & hardening (owner: M1 + all; 1 week)
Data requests (export/erasure/correction), consent withdrawal effects, retention job, ALTCHA flag, CSP/headers final, dependency + secret scans, ZAP baseline, k6 smoke, backup/restore drill, ASVS L2 checklist ticked with evidence.
**Gate:** security gates in `07_SECURITY.md` §9 all green · k6 thresholds met · restore drill done.

## P11 — Measurement v2 & evaluation (owner: M3; parallel, 2 weeks)
A4 Tier A, optional YOLOv8n-seg (masks via SAM auto-annotation offline), **field validation:** 20–30 Talegaon potholes + 5–10 garbage piles tape-measured using the app protocol → MAPE per tier; classifier and YOLO final metrics; FIFO vs optimised plan comparison re-run on DB data; `docs/EVALUATION_REPORT.md`.
**Gate:** evaluation report generated by scripts from committed data; every number in the report reproducible by one command.

## P12 — Demo readiness (owner: all; 1 week)
Demo accounts (first ADMIN with `bootstrap-admin.ps1`, then officers/contractors through the UI), demo data (seed + 10–15 real complaints captured around Talegaon), Cloudflare tunnel, Meta test numbers registered (5 phones), Gmail/Brevo sender, runbook rehearsal twice, backup taken, known limitations slide.
**Gate:** `13_DEMO_AND_DEPLOY.md` §4 script run twice on the demo laptop with no error; `verify-all.ps1` green on `main`.

## When something fails (protocol for the agent)
1. Stop. Paste the exact error. 2. Reproduce with the smallest command. 3. Write/adjust a failing test that shows the bug. 4. Fix the cause, not the test. 5. Re-run the whole component's tests. 6. Record cause + fix in PROGRESS.md. After two failed fix attempts on the same error, stop and ask the human (switch to a stronger model for the analysis).
