# CivicBrain — Agent Instructions (always read first)

You are building **CivicBrain**, an AI decision-support web platform for **Talegaon Dabhade Municipal Council (TDMC)**, Maharashtra, India (SPPU final-year project, 4-person team; the MVP is built on ONE Windows 11 laptop). The complete specification is in `docs/` — start with `docs/00_README_FIRST.md`. This file is the short version you must always follow.

## 0. MODE: 7-DAY MVP (1–7 Oct 2026) — read this first
The team has 7 days. **`docs/09_BUILD_PLAN_7DAY.md` replaces `docs/09_BUILD_PLAN.md` for scope and schedule until the deadline.** Work prompt by prompt with `/run-prompt P01` … `P30` (§0b; `prompts/README.md` maps prompts to days) and check each day with `/phase-gate D<n>`.
- Build only what its §1 IN list contains. Anything in its OUT list must not be built now, even if another document describes it (say so if a task seems to need it).
- For every kept feature, the other documents still define HOW (API shapes, DB rules, security, error codes).
- Mandatory tests = its §4 list (never weaken or delete them). The rest of `docs/08_TEST_PLAN.md` is Phase 2.
- MVP decisions (its §2): YOLO trained on the existing images only, `ROUTING_MODE=haversine` instead of OSRM, WhatsApp via Twilio sandbox or `log`, no officer TOTP unless Day 6 is green.

## 0b. AUTOPILOT (how the human drives you)
The human gives you one prompt file at a time: `/run-prompt P01`, then `P02`, … (`prompts/README.md` has the order and the day plan). Follow `.agents/skills/run-prompt/SKILL.md`: plan **without waiting**, build, test, verify yourself (scripts you may run: `.agents/rules/01-safety.md`), record in `docs/PROGRESS.md` (Autopilot log), commit, then ask the human only the prompt's yes/no questions. Stop earlier only for the ASK-FIRST list, a human-only step, or two failed fix attempts. Everything runs on one laptop: you start/restart services only with `scripts/dev/start-all.ps1` (never with `-Tunnel`/`-Demo`).

## 1. The product in one paragraph
Citizens report civic problems (photo taken in-app + GPS + text) from a mobile website. A background AI worker checks authenticity, classifies the problem, detects the defect with YOLOv8, estimates size / material / cost with a confidence tier, finds duplicates (frozen Step 12 rules) and computes the frozen Step 11 priority. Officers see everything on a dashboard with a map of the **23 wards**, group complaints within 2 km into an optimised **action plan** (editable, versioned, PDF/Excel, officer-only) and assign it to a **contractor**. The contractor inspects (blind tape measurement), works and uploads proof. Citizens get **e-mail + WhatsApp** messages at every citizen-facing status. Flow and statuses: `docs/01_REQUIREMENTS.md` §3.

## 2. Stack (fixed — do not substitute)
| Layer | Technology | Folder |
|---|---|---|
| Frontend (citizen, officer, contractor portals in one app) | React 19.3 + TypeScript 6.0 + Vite 8 + Tailwind 4 + react-leaflet 5 / Leaflet 1.9.4 | `frontend/` |
| Backend API | Java 25 (Temurin LTS), Spring Boot 4.1.1, Spring Security 7, Flyway 12 (+ flyway-database-postgresql), Hibernate 7 (+Spatial), Maven wrapper | `backend/` |
| AI worker + small FastAPI | Python 3.13, Ultralytics YOLOv8 (ONNX on CPU), scikit-learn, sentence-transformers, OR-Tools | `ai-service/` |
| Database | PostgreSQL 18 + PostGIS 3.6; tested migrations V1–V5 | `db/` (pgAdmin versions), `backend/src/main/resources/db/migration/` (Flyway copies from `flyway/`) |
| Routing | MVP: straight-line (`ROUTING_MODE=haversine`); Phase 2: OSRM in Docker | `infra/osrm/` |
| Files | local disk `STORAGE_ROOT`, served only through the backend | `storage/` (git-ignored) |
| Background jobs | PostgreSQL `jobs` table + `fn_claim_jobs` (no Redis, no MinIO) | — |
Pinned versions: `docs/10_SETUP_WINDOWS.md`, `frontend/package.json`, `ai-service/requirements.txt`. Never change a major version on your own.

## 3. Golden rules
1. **Read before you write.** Use the reading-order table in `docs/00_README_FIRST.md`. If documents disagree with each other or with the code, STOP and ask.
2. **One prompt (or phase) at a time** (`prompts/P<nn>_*.md` via `/run-prompt` now; `docs/09_BUILD_PLAN.md` phases after the deadline; status in `docs/PROGRESS.md`). Days are checked with `/phase-gate D<n>`.
3. **Plan first.** In autopilot (`/run-prompt`) write the plan and continue without waiting, except for the ASK-FIRST list in the skill; with `/start-phase` wait for approval.
4. **Tests are part of every task** (`.agents/rules/03-testing.md`, `docs/08_TEST_PLAN.md`). Done = you ran `/verify` and saw green. Never weaken or skip a test.
5. **Database is the source of truth.** `ddl-auto=validate`; schema changes only as new Flyway migrations (three identical copies, `.agents/rules/40-database-sql.md`) with tests; never edit V1–V5; grants only in `R__civicbrain_grants.sql`. Status changes only through the DB rules (set `civicbrain.actor_*`). Use the provided SQL functions (`docs/03_DATABASE.md` §4).
6. **Frozen research rules** (`.agents/rules/02-frozen-rules.md`) never change.
7. **Every error is handled** as `docs/12_ERROR_HANDLING.md` says (codes, messages, timeouts, retries, idempotency).
8. **Security by default** (`docs/07_SECURITY.md`): deny-all, ownership in queries (404), validated input, no secrets/OTP/tokens/full phones in logs.
9. **Safety** (`.agents/rules/01-safety.md`): no deletes by shell, no destructive git/docker/db commands, no psql, only the allow-listed scripts, servers only through `start-all.ps1`, no `.env` reading.
10. **Record and commit:** update `docs/PROGRESS.md` and `/commit-step` after each green task.

## 4. Commands (Windows 11; one command per call with the working directory set - no `cd … &&` chains, so the allow lists match - Antigravity settings or `.claude/settings.json` - and nothing hangs)
Backend (in `backend`): `.\mvnw.cmd -q verify` · Frontend (in `frontend`): `npm run lint`, `npm run typecheck`, `npm test -- --run` · AI (in `ai-service`): `.\.venv\Scripts\python.exe -m ruff check .`, `.\.venv\Scripts\python.exe -m pytest -q` · Smoke (repo root): `ai-service\.venv\Scripts\python.exe tests\smoke\smoke_flow.py --stage <stage>` against the E2E stack.
Services (repo root): `pwsh -NoProfile -File scripts\dev\start-all.ps1` (dev) · `… -Only backend -Restart` after backend changes · `… -Only worker,ai-api -Restart` after Python changes (add `-E2E` to both while the E2E stack runs) · `… -E2E -Restart` to switch to the test stack · `… -Status` · logs (appended, one header per start) in `logs\<service>.log`.
Ports: backend 8080 · frontend 5173 (proxies `/api`) · AI API 127.0.0.1:8001 · PostgreSQL 5432 · Mailpit 1025/8025 · (OSRM 5000 Phase 2).
Scripts you may run and the human-only ones: `.agents/rules/01-safety.md`.

## 5. Definition of Done (every task)
Traces to FR/NFR IDs and a doc section · tests written first and green · loading/empty/error/success states and documented error codes · lint/type/security clean · command + result in PROGRESS.md · committed.

## 6. Map of the kit
`CLAUDE.md` + `.claude/` (Claude Code: imports this file and rules 01-03; generated rules/skills; permissions; `scripts/dev/sync-claude.ps1`) · `prompts/` (P00 orientation, P01…P30 autopilot prompts + README day plan) · `docs/00…13`, `docs/PROGRESS.md`, `docs/reports/` (metrics), `docs/screenshots/` · `tests/smoke/smoke_flow.py` (API full-flow check) · `data/complaints/` (text data, README) · `db/` V1–V5 + `R__civicbrain_grants.sql`, `db/tests`, `db/seed`, `db/tools` (roles template, `e2e_reset.sql`), `db/SCHEMA_REFERENCE_after_V5.sql` · `flyway/` (the copies Flyway uses) · `gis/tdmc_wards_clean_v2.geojson` + `WARD_QA_REPORT.md` · `.agents/rules`, `.agents/skills` (`/run-prompt`, `/start-phase`, `/verify`, `/phase-gate`, `/commit-step`) · `scripts/dev` (PowerShell; allowed vs human-only list in `01-safety.md`) · `scripts/ci` (CI shell) · `scripts/audit/export_db_complaints.py` · `infra/osrm` · `.github/workflows/ci.yml` · `ai-service/models/README.md` · `ai-service/training/` (dataset check, Kaggle notebook, model installers) · `.env.example`, `.env.test.example`.
