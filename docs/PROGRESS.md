# PROGRESS — CivicBrain build log

The agent updates this file in the same commit as every task. Humans approve each phase gate here.

## Current plan: 7-DAY MVP (`docs/09_BUILD_PLAN_7DAY.md`), 1–7 Oct 2026
| Day | Date | Gate (from §5) | Status | Evidence / bugs | Approved by |
|---|---|---|---|---|---|
| D1 | Thu 1 Oct | build laptop ready, backend + Flyway + seed, Vite layout, worker claims a job, YOLO training started, CI green | NOT STARTED | | |
| D2 | Fri 2 Oct | register → OTP → login, admin exists, priority 0 mismatches, duplicates test, YOLO ONNX detects | NOT STARTED | | |
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
| P02 | AI service skeleton + venv + worker loop | D1 | NOT STARTED | |
| P03 | Dataset check + fixtures + Kaggle package (YOLO training starts) | D1 | NOT STARTED | |
| P03b | Fallback: auto-label (only if labels are missing) | D1 | NOT STARTED | |
| P04 | Backend skeleton + Flyway + demo seed | D2 | NOT STARTED | |
| P05 | Frontend skeleton | D2 | NOT STARTED | |
| P06 | Auth backend + E2E seed runner + smoke auth | D2 | NOT STARTED | |
| P07 | Auth screens + CameraCapture | D2 | NOT STARTED | |
| P08 | Text classifier, YOLO detector (install Kaggle model), authenticity | D3 | NOT STARTED | |
| P09 | Priority + duplicates (FROZEN) + MiniLM | D3 | NOT STARTED | |
| P10 | Complaint intake API + e-mail outbox + smoke intake | D3 | NOT STARTED | |
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

## Full plan (after the deadline)
- **App track:** P0 — Machines, repo, Antigravity (status: covered by the MVP days; re-check its gate)
- **ML track:** P2 — ML data and models (status: NOT STARTED — MVP used the existing images only)

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
