# P00 — Orientation (first session, read-only)
**Before P01 · Claude Code · agent ≈ 10 min · human ≈ 5 min · Model: strongest (`opus`)**

How the human starts it: open a new Claude Code session in `C:\dev\civicbrain` (Auto mode) and type
`Read prompts/P00_orientation.md and do exactly what it says.`

## Rules for this session
- **Read-only.** Do not create, edit or delete any file. Do not write to `docs/PROGRESS.md`. Do not commit.
- Run only the read-only commands listed in step 3. Do not start P01 - the human starts it in a new session.
- Never open `.env`, `.env.test` or `tests/e2e-ui-accounts.local.json`.

## The project in one page (what we are building)
**CivicBrain** - an AI decision-support web app for **Talegaon Dabhade Municipal Council (TDMC)**, Pune district,
**23 GIS wards**. SPPU final-year project, 4 students. Built in **7 days (1-7 Oct 2026)** on **one Windows 11 laptop**.
- **Citizen** (phone browser): registers (OTP), reports a civic problem with a **fresh camera photo + GPS + text**
  (no gallery), gets a complaint number, follows its status, gets **e-mail / WhatsApp** on the status changes listed in FR-50
  (SUBMITTED, MERGED, REJECTED, ASSIGNED, INSPECTED, IN_PROGRESS, COMPLETED-with-photo, CLOSED, REOPENED), rates the fix.
- **AI** (Python worker): photo authenticity checks (EXIF/GPS/freshness), text + image **classification**,
  **YOLOv8** detection of 4 classes (0 Pothole, 1 Garbage Accumulation, 2 Waterlogging, 3 Road Damage), size/area
  estimate with a confidence tier, material/cost/worker estimate, **duplicate merging** (300 m, 7 days, MiniLM text
  similarity; the earlier complaint stays master, and the merged group shows the best-quality photo per the quality score
  in `docs/06_AI_PIPELINE.md` §2.6), explainable **priority** score (frozen Step 11 formula).
- **Officer** (desktop): reviews complaints on a map, approves/rejects/merges, builds an editable **action plan** of
  GPS-grouped jobs (same work type, <= 2 km, <= 10 jobs), assigns a **contractor**; every complaint owner is notified
  with the contractor's name.
- **Contractor** (phone): sees assigned jobs, inspects, uploads **completion proof photos**; the officer closes.
- **Non-functional:** secure (Spring Security, JWT + refresh cookie, OTP, ownership checks -> 404), responsive, honest
  (synthetic data and prototype rates are labelled; AI numbers shown with confidence/range).
- **Stack (pinned):** React 19 + TypeScript + Vite + Tailwind + react-leaflet · Spring Boot 4.1 / Java 25 + Flyway ·
  PostgreSQL 18 + PostGIS 3.6 · Python 3.13 FastAPI + worker (ultralytics, onnxruntime, OR-Tools, sentence-transformers) ·
  Mailpit for test mail · Docker Desktop only for Testcontainers and Mailpit · cloudflared tunnel for the phone demo.
- **Inputs we already have:** the team's research folder copied into `data/` and `scripts/` (YOLO images + labels,
  priority CSVs, duplicate results, resource models, routing code) and the kit's `gis/` wards and `db/` V1-V5 schema.
  Nothing else will be collected. Missing research files have documented fallbacks (P08, P09, P12).
- **How we work:** 30 prompt files (`prompts/P01`…`P30`, plus `P03b` only if labels are missing), one per session,
  run with `/run-prompt P<nn>`. The agent plans without waiting, builds, tests, verifies, logs to `docs/PROGRESS.md`,
  commits, pushes, then asks the human short yes/no questions. Day gates `/phase-gate D1`…`D7`.

## Steps
1. **What loaded.** Without opening files: list the instruction files in your context (CLAUDE.md, the imported
   `AGENTS.md` and rules 01-03, any `.claude/rules/*`), the project skills you can see (expect `run-prompt`, `verify`,
   `commit-step`, `phase-gate`, `start-phase`), and quote the "Human-only" line of the safety rules.
2. **Read** (in this order): `AGENTS.md`, `docs/00_README_FIRST.md`, `prompts/README.md`,
   `docs/09_BUILD_PLAN_7DAY.md` (sections 1, 2, 3, 7), `docs/01_REQUIREMENTS.md` (sections 2, 3, 7),
   `.claude/settings.json`, `.claude/skills/run-prompt/SKILL.md`, `docs/PROGRESS.md`, `prompts/P01_repo_env_databases.md`,
   `START_HERE.md` (skim). Until 7 Oct 2026, `docs/09_BUILD_PLAN_7DAY.md` replaces `docs/09_BUILD_PLAN.md`.
3. **Read-only checks** (one command per call, PowerShell tool, repo root):
   - `pwsh -NoProfile -File scripts\dev\sync-claude.ps1 -Check` (expect `PASS  sync-claude: .claude/ is current`)
   - `git --version`, `pwsh --version`, `py -3.13 --version`, `node --version`, `java -version`, `docker version`
     (a missing tool is a WARN here; P01's `check-env.ps1` does the full check)
   - `Test-Path data\yolo\data.yaml`, `Test-Path gis\tdmc_wards_clean_v2.geojson`, `Test-Path scripts\priority\priority_engine.py`
   - `(Get-ChildItem data\yolo\images\train -File).Count` and the same for `data\yolo\labels\train`
     (expected roughly 2,700 each; only counts, P01 writes the full inventory)
   - Research folders (only `Test-Path`, each one its own call; a missing one is a WARN - P01 inventories it and P08/P09/P12
     have fallbacks): `data\priority`, `data\duplicates`, `data\resources\models`, `scripts\duplicates`, `scripts\resources`,
     `scripts\optimization\routing`
   - Setup files (only `Test-Path`, NEVER open them): `.env`, `.env.test`, `KIT_FIXES.md`.
     If `.env` or `.env.test` is False, the human must run `pwsh -NoProfile -File scripts\dev\new-env.ps1` in their own
     PowerShell 7 window before P01 - report this as NOT READY with that exact instruction.
   - `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Status -Only worker,ai-api` (read-only; it must NOT print
     "does not belong to the set" - a status table or "not built yet" is fine)
4. **Report** in this exact shape, short bullets:
   ```
   P00 ORIENTATION - READY (or: NOT READY - <reason>)
   1. Loaded: <instruction files> · skills: <names> · Human-only: "<quote>"
   2. Product: <3 lines, end to end, town + wards>
   3. AI: <4 classes> · MVP decisions (routing, WhatsApp, test mail, officer TOTP): <one line>
   4. Scope IN (5 bullets) / OUT (5 bullets)
   5. Order: P01..P30, when P03b runs, day gates
   6. I may run: <short list> · I never run/open: <short list>
   7. How one prompt runs: plan -> build -> test -> verify -> log -> commit/push -> yes/no; when I stop and ask
   8. Checks: <each command -> result>
   9. Contradictions / missing / unclear: <file + section + one line each, or "none found">
   Next: the human opens a NEW session and types /run-prompt P01
   ```
5. Do not fix anything you found in point 9. The human decides.

## Known and accepted (already decided - do NOT report these in point 9)
- `KIT_FIXES.md` lists 5 fixes on top of the Claude Code kit (comma list for `start-all.ps1 -Only`, tunnel URL regex,
  admin TOTP not forced in the MVP, P08 health expectation, Twilio 24-hour rule). They are intended.
- **Admin TOTP:** in the 7-day MVP `app.security.mfa-required=false`; the admin logs in with e-mail + password; TOTP
  (admin and officer) comes only with the optional P25. This overrides `docs/01_REQUIREMENTS.md` section 2 for the MVP.
- **"Other" / REVIEW_REQUIRED reclassify and officer estimate override (FR-32)** are not built in the 7-day MVP. Tests and
  the demo use the 4 main categories; it is Phase 2 unless the human adds it in P14/P15.
- **`docs/01_REQUIREMENTS.md` section 6, decision 8 (WhatsApp OTP for demo phones)** is not in the MVP: OTP goes by e-mail only.
- **Day gates:** use the table in `prompts/README.md` (D1 after P05 ...). The older gate texts in `docs/PROGRESS.md` and
  `docs/09_BUILD_PLAN_7DAY.md` section 5 are replaced by it.
- **Schedule:** the build started late (P01 on Fri 2 Oct). Plan: Fri P01-P05 (Kaggle training started in P03 today),
  Sat P06-P09, Sun P10-P13, Mon P14-P17, Tue P18-P23, Wed P24 + P27-P30; P25/P26 skipped unless a day ends early.
  Use the cut order of `docs/09_BUILD_PLAN_7DAY.md` section 7 when a prompt runs over.

READY means: `sync-claude -Check` PASS, `.env` and `.env.test` exist, `data\yolo` is complete, the `-Only` check is clean,
and point 9 has no blocker. Missing optional research folders are WARN, not NOT READY.
