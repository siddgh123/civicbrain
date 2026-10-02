# 00 — Read Me First (for humans and for the agent - Claude Code or Antigravity)

## What this kit is
Everything the agent needs before writing code: frozen requirements, architecture, a tested database (V1–V5), the cleaned 23-ward GIS layer, API/UI/AI/security/error specs, a phase plan with test gates, setup instructions and data sources. Built and verified on 2026-09-30 against the team's real `civicbrain_backup` and `gis.zip`.

## Human steps before the first agent prompt (single build laptop, autopilot)
The full checklist with exact commands is **`START_HERE.md`** in the project root (software: `SOFTWARE_LIST.md`); in short:
1. `install-all.ps1` (winget) → PostgreSQL password + PostGIS (Stack Builder) → restart → Docker Desktop once → `.wslconfig` 4 GB.
2. Copy only the `data/` and `scripts/` folders of your old CivicBrain folder (they hold `data/yolo/images|labels|data.yaml` and the Step 9–13 research files) to `C:\dev\civicbrain` (not OneDrive) and copy this kit's contents next to them (the kit adds files; research files used by tests keep their paths: `data/duplicates/duplicate_engine_results.csv`, `data/priority/priority_factor_dataset.csv`, `data/priority/priority_scores.csv`). Run `Get-ChildItem -Recurse C:\dev\civicbrain | Unblock-File` once.
3. `pwsh -NoProfile -File scripts\dev\new-env.ps1` → `.env` and `.env.test` with random secrets (asks only the postgres password).
4. Claude Code (default): open `C:\dev\civicbrain`, trust the folder, Auto mode, model opus (`START_HERE.md` Step 6) - rules, skills and
   permissions come from `CLAUDE.md` + `.claude/`. (Antigravity instead: settings exactly as `10_SETUP_WINDOWS.md` §5.)
5. First session: `Read prompts/P00_orientation.md and do exactly what it says.` (read-only). Then a new session: `/run-prompt P01`.
   From then on: one prompt per session, answer the yes/no questions, type the next prompt.
(The interactive alternative `/start-phase D<n>` / `P<n>` still exists for the full plan after the deadline.)

## Reading order for the agent (by task type)
| Task | Read first |
|---|---|
| Any task | `AGENTS.md` (§0 MVP mode, §0b autopilot!), `docs/PROGRESS.md` (Autopilot log), the prompt file `prompts/P<nn>_*.md`, the day in `09_BUILD_PLAN_7DAY.md` (until 7 Oct 2026), else the phase in `09_BUILD_PLAN.md` |
| Requirements question | `01_REQUIREMENTS.md` |
| Backend endpoint | `04_API_CONTRACT.md`, `12_ERROR_HANDLING.md`, `07_SECURITY.md`, `03_DATABASE.md` §3 |
| Database / SQL / entity | `03_DATABASE.md`, `db/SCHEMA_REFERENCE_after_V5.sql` |
| Frontend screen | `05_UI_SPEC.md`, `04_API_CONTRACT.md`, `12_ERROR_HANDLING.md` §6 |
| AI worker | `06_AI_PIPELINE.md`, `03_DATABASE.md` §3, `11_DATA_SOURCES.md` |
| Tests | `08_TEST_PLAN.md` |
| Security | `07_SECURITY.md` |
| Demo / deploy | `13_DEMO_AND_DEPLOY.md` |

## Kit contents
```
AGENTS.md                         always-on project instructions (§0b autopilot)
CLAUDE.md                         Claude Code entry: imports AGENTS.md + rules 01-03, maps Antigravity terms, permissions, shell, browser checks
.claude/settings.json             Claude Code permissions (allow / ask / deny), env (PowerShell tool, timeouts), auto memory off
.claude/rules/, .claude/skills/   generated copies of .agents/rules 10-50 and .agents/skills (scripts/dev/sync-claude.ps1)
prompts/                          README (Step 0 + day plan), P00 orientation (read-only) and P01..P30 (+P03b) autopilot prompts, one per session
.agents/rules/                    safety (what the agent may run), frozen rules, testing (always on); backend/frontend/ai/db (by file pattern); security (on demand)
.agents/skills/                   /run-prompt (autopilot), /start-phase, /verify, /phase-gate, /commit-step
docs/00..13, PROGRESS.md          the specification and the progress log; 09_BUILD_PLAN_7DAY.md = active 7-day MVP plan
db/V1..V5, db/R__civicbrain_grants.sql   tested SQL for pgAdmin/psql (+ SCHEMA_REFERENCE_after_V5.sql)
db/tests/                         SQL tests (V2 workflow 6/6, V4 11/11, V5 11/11, roles 7/7)
db/seed/                          optional synthetic demo data (500 Step 8 complaints, Step 12/13 results)
db/tools/                         create_roles_template.sql (login roles), e2e_reset.sql (E2E data reset)
flyway/V1..V5, flyway/R__civicbrain_grants.sql   the Flyway copies -> backend/src/main/resources/db/migration/
gis/                              cleaned 23 wards (GeoJSON), QA report, build scripts
ai-service/requirements*.txt      pinned Python deps (+ Windows py3.13 lock files); models/README.md (MANIFEST format)
frontend/package.json             pinned npm deps (peer dependencies verified, npm audit clean)
infra/osrm/                       docker-compose.yml (pinned image) + README (map data, prepare, check)
scripts/dev/                      PowerShell 7 helpers: install-all, new-env (human); check-env, db-setup-main, db-rebuild-test,
                                  seed-e2e, start-all, verify-all, backup-db, make-kaggle-package (agent may run);
                                  bootstrap-admin, new-secret, start-{backend,frontend,worker,ai-api,osrm,mailpit,tunnel,e2e},
                                  prepare-osrm (human / building blocks) (+ _common.ps1) - who runs what: 10_SETUP_WINDOWS.md §4
scripts/ci/                       db-tests.sh, check-migrations.sh (used by CI; also run on Linux/WSL)
scripts/audit/                    export_db_complaints.py (P1 step 4: re-run Steps 10/11/13 on DB complaints)
ai-service/training/              prepare_mvp_dataset.py, train_yolo_mvp.py, kaggle_train_mvp.ipynb (YOLO on the existing images, Kaggle),
                                  install_kaggle_model.py (Kaggle zip -> models/ + MANIFEST + docs/reports), download_models.py (MiniLM),
                                  model_manifest.py
data/complaints/                  synthetic_complaints_500.csv, kit_authored_train.csv, sanity_test_mvp.csv (+ README: honest labels)
tests/smoke/smoke_flow.py         API full-flow check (auth -> intake -> analysis -> officer -> plan -> contractor -> close)
.github/workflows/ci.yml          CI: db, backend, frontend, ai, security (actions pinned by SHA)
.env.example  .env.test.example  .gitignore  .gitattributes  .gitleaks.toml
```

## Verified facts (so nobody re-checks them)
- V1→V4 from an empty database gives the same data as restoring the backup and running V2→V4 (hash-compared). On a brand-new PostgreSQL server `scripts/ci/db-tests.sh` (roles → V1–V5 → R__ grants → seed → R__ again → tests) passes with both the `flyway/` and the `db/` copies: V2 6/6, V4 11/11, V5 11/11, roles 7/7, 74 application tables, 23 wards, `fn_locate_point(18.7440, 73.6760)` = ward_number 1 (ward_id 21). The upgrade path (restored backup + V2–V5 + R__) passes the same tests.
- V3 leaves 0 overlap and 0 gap between wards; every complaint lies in exactly one ward.
- `fn_cluster_jobs` is deterministic: same groups after row reordering; ≤ 10 jobs, ≤ 2 km, one work type per group.
- `db/tools/e2e_reset.sql` empties the 48 application tables, keeps the 27 reference tables, refuses any database not named `*_e2e`, and the SQL tests still pass afterwards.
- Python requirements resolve for Windows / Python 3.13 (and for Linux CI) with binary wheels only; `pip-audit` on the Windows lock: no known vulnerabilities. npm dependencies resolve without peer conflicts; `npm audit`: 0 vulnerabilities (2026-09-30).
- `ci.yml` passes actionlint; `scripts/ci/*.sh` pass shellcheck; all `scripts/dev/*.ps1` parse without syntax errors. The PowerShell scripts have NOT been executed on Windows yet — their first real run is `check-env.ps1` in P0; report any problem in `docs/PROGRESS.md`.
- Autopilot additions (2026-10-01): `tests/smoke/smoke_flow.py` passed its `auth` stage against a contract-conforming fake API (the other stages are written from `04_API_CONTRACT.md` and get their first real run in P10–P23); `install_kaggle_model.py` was tested with a fake ONNX zip (SHA check, unsafe-path refusal, ONNX shape check 1×8×8400); the Kaggle notebook cells are syntax-checked; the text classifier recipe (word 1–2 + char 2–5 TF-IDF, LogisticRegression) scores ≈ 0.90 on `sanity_test_mvp.csv`; `E2E_POINT_FAR` (18.7400, 73.6760) is inside ward 1, 445 m from `E2E_POINT_IN`, 516 m from the boundary. `start-all.ps1`, `make-kaggle-package.ps1`, `db-setup-main.ps1`, `new-env.ps1` and `install-all.ps1` parse but have not run on Windows yet - P01 is their first run.
- Known data problems and their fixes are listed in `gis/WARD_QA_REPORT.md` and `09_BUILD_PLAN.md` P1 (DB vs CSV complaint mismatch; POI ward ids were ward numbers).
