# P02 — AI service skeleton, venv and worker loop
**Day 1 (Thu 1 Oct) · agent ≈ 1.5 h (venv install ≈ 15 min) · human 0 min · Needs: P01 · Model: any**

## Goal
`ai-service/` exists with the pinned venv, settings, a FastAPI `/health`, and a worker loop that claims jobs
from PostgreSQL with `fn_claim_jobs`, finishes them with `fn_finish_job`, requeues stale ones and stops
gracefully. The real pipeline steps come in P08–P12 (here: a dispatcher with "not implemented yet" handlers
that fail the job cleanly).

## Read first
`docs/02_ARCHITECTURE.md` §4 and §6 · `docs/06_AI_PIPELINE.md` §1 and §5 · `docs/12_ERROR_HANDLING.md` §7 ·
`.agents/rules/30-ai-service-python.md` · `docs/03_DATABASE.md` §3–§4 · `db/SCHEMA_REFERENCE_after_V5.sql` (jobs, fn_claim_jobs, fn_finish_job, fn_requeue_stale_jobs)

## Build
1. Venv (repo root): `py -3.13 -m venv ai-service\.venv`, then
   `ai-service\.venv\Scripts\python.exe -m pip install -r ai-service\requirements-dev-win-py313.lock` (exact pins; ≈ 10–15 min).
2. `ai-service/pyproject.toml`: project metadata, pytest config (markers `models`, `integration`; `testpaths = ["tests"]`),
   ruff (`line-length = 140`, `target-version = "py313"`, select E,F,W,I,B,UP; `extend-exclude = ["training/*.ipynb"]`).
3. `app/config.py`: pydantic-settings `Settings` with every key of rule 30 (names = `.env.example`),
   `SettingsConfigDict(env_file=('../.env',), extra='ignore')`, `get_settings()` with `lru_cache` (never at import).
   ASSUMPTION constants (thresholds, Tier C priors, depths) live here with comments (fill the ones from 06 §2.1/§2.4 now).
4. `app/db.py`: SQLAlchemy 2 engine (psycopg3) as `civicbrain_ai`, `session_scope()` helper, `set_system_actor(conn)`
   (`select set_config('civicbrain.actor_role','SYSTEM', true)`).
5. `app/main.py`: FastAPI with `GET /health` → `{status, db, osrm:"not used (haversine)", modelsLoaded}` (no auth, 127.0.0.1);
   `GET /v1/models` + `POST /v1/jobs/{id}/requeue` with the service JWT check (04 §10; PyJWT HS256, aud/iss/exp/iat required).
6. `app/models_check.py`: reads `models/MANIFEST.json`, verifies SHA-256 of the files the worker needs; returns a list of
   problems. Until P08/P09 the files do not exist: `/health` shows `modelsLoaded: false`; the worker logs a WARN and still
   runs (handlers that need models fail their job with `ModelError`). From P12 on the worker refuses to start if a required
   file is missing (06 §5) - put that switch in config as `REQUIRE_MODELS` (default **false** until P12 sets it true; tests set false).
7. `worker/run.py` (`python -m worker.run`): loop per 06 §1 - claim 1 job of the 4 types every `WORKER_POLL_SECONDS`,
   dispatch by `job_type` to `worker/handlers.py`, `fn_finish_job(id, true)` or `(id, false, '<Type>: <msg>')`,
   `fn_requeue_stale_jobs('15 minutes')` every 5 min, SIGINT/CTRL+C → finish the current job then exit, per-job timeout
   (analyze 120 s, optimize 60 s). DEAD ANALYZE_COMPLAINT → `complaints.ai_status = 'FAILED'` (06 §1).
   At start the worker requeues its OWN jobs still marked RUNNING (`locked_by = WORKER_ID`, left by a hard stop of
   `start-all.ps1 -Restart`) so a restart never leaves a complaint waiting 15 minutes.
   Handlers now: `ANALYZE_COMPLAINT`, `OPTIMIZE_PLAN` raise `NotImplementedError` (→ job fails, retries, DEAD) -
   replaced in P12/P17; `ANALYZE_IMAGE`, `BLUR_IMAGE` are Phase 2: finish them as success with a log line "skipped (MVP)".
8. JSON logging (job_id, complaint_id, step), typed exceptions (`ConfigError`, `ModelError`, `DataError`, `DependencyError`).
9. `tests/conftest.py`: fake values for every non-DB setting, `DB_NAME = DB_TEST_NAME`, admin connection fixture for
   integration tests (inserts as `PG_ADMIN_USER`, deletes in a finalizer; 08 §2 rules); before anything imports ultralytics:
   `YOLO_AUTOINSTALL=false`, `YOLO_OFFLINE=true`, `YOLO_CONFIG_DIR=<repo>/ai-service/.ultralytics` (same values as `.env.example`;
   Ultralytics must never pip-install or write to %APPDATA%).

## Tests (write first)
- unit: settings load lazily and fail with a clear message when a key is missing; JWT check rejects wrong aud/iss/alg/expired;
  dispatcher maps the 4 job types; manifest checker reports missing file and wrong hash.
- integration (`@pytest.mark.integration`, `civicbrain_test`): insert a user + complaint as admin → the DB trigger
  enqueues ANALYZE_COMPLAINT → one worker iteration claims it, the handler fails → `jobs.attempts = 1`, status QUEUED with
  `run_after` in the future (retry schedule of `fn_finish_job`); a job finished as success → status SUCCEEDED;
  `fn_requeue_stale_jobs` path with a fake old RUNNING row; own RUNNING jobs requeued at start; graceful stop flag ends the
  loop after the current job.

## Verify (agent)
- in `ai-service`: `.\.venv\Scripts\python.exe -m ruff check .` and `.\.venv\Scripts\python.exe -m pytest -q` → green.
- `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only ai-api,worker` → healthy; open http://127.0.0.1:8001/health in
  the browser tool, screenshot `docs/screenshots/P02_health.png`; read `logs\worker.log` (worker started, polling).
- `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop -Only worker,ai-api` (keep the laptop quiet for P03).

## Human step
None.

## Ask the human (yes/no)
- Q1. The screenshot `docs/screenshots/P02_health.png` shows `"status"` and `"db": "ok"` (or similar) - does it look right?

## Done when
venv installed from the lock file · ruff + pytest green (unit + integration) · `/health` answers · committed and pushed.

## Next
`/run-prompt P03` — dataset check + Kaggle package; YOLO training starts tonight (≈ 30 min + your upload)
