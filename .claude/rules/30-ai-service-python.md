---
paths:
  - "ai-service/**"
---
<!-- Generated from .agents/rules/30-ai-service-python.md by scripts/dev/sync-claude.ps1. Edit the source, then run the script. -->
# AI service rules (Python 3.13, FastAPI, worker)

- Use the venv `ai-service\.venv` and the pinned `requirements*.txt` (resolved for Windows cp313). Only one OpenCV package (`opencv-python` via ultralytics). New dependency = exact pin + re-run `uv pip compile` for the Windows lock file (show the command in the plan).
- Layout per `docs/02_ARCHITECTURE.md` §4. Settings via pydantic-settings from environment; fail fast on missing settings or model files (checksum from `models/MANIFEST.json`).
- DB access: SQLAlchemy 2 Core/ORM with psycopg3, role `civicbrain_ai`. Jobs only via `fn_claim_jobs`, `fn_finish_job`, `fn_requeue_stale_jobs`. Each job's writes in one transaction; idempotent (delete-then-insert per model version, or `is_current` switch).
- Status changes: `select set_config('civicbrain.actor_role','SYSTEM', true)` then UPDATE; only SUBMITTED → VERIFIED / MERGED.
- Follow `docs/06_AI_PIPELINE.md` exactly (order of steps, thresholds, formulas). Every ASSUMPTION constant lives in `app/config.py` with a comment and is written into the result's `assumptions` JSON.
- Frozen rules (`.agents/rules/02-frozen-rules.md`) for classes, priority, duplicates, grouping.
- FastAPI binds `127.0.0.1:8001`; admin endpoints verify the service JWT (PyJWT, HS256 only, `aud=civicbrain-ai`, require exp/iat/aud/iss).
- Typed exceptions (`ConfigError`, `ModelError`, `DataError`, `DependencyError`); log JSON with job_id, complaint_id, step; never log image bytes or personal data.
- External calls (OSRM) with explicit timeouts (10 s) and bounded retries.
- Settings names = `.env.example` (`DB_HOST, DB_PORT, DB_NAME, DB_AI_USER, DB_AI_PASSWORD, WORKER_ID, WORKER_POLL_SECONDS, ROUTING_MODE, OSRM_URL, YOLO_WEIGHTS, MODELS_DIR, TEXT_EMBEDDING_MODEL_DIR, AI_SERVICE_JWT_SECRET, AI_API_HOST, AI_API_PORT, STORAGE_ROOT, LABOUR_RATE_PER_HOUR, BLUR_ENABLED, LOG_LEVEL`). Settings are created lazily (`get_settings()` with `lru_cache`), never at import time; `app/config.py` uses `SettingsConfigDict(env_file=('../.env',), extra='ignore')` so uvicorn, the worker and pytest read the repo-root `.env` themselves (you still never open it). `tests/conftest.py` sets fake values for every non-DB setting and `DB_NAME = DB_TEST_NAME`; integration tests insert fixtures through a second connection as `PG_ADMIN_USER` (e-mails `it-<uuid>@it.local`, no phone) and delete them afterwards (`docs/08_TEST_PLAN.md` §2). Entry points: `python -m worker.run` and `uvicorn app.main:app` (run from `ai-service/`; used by `scripts/dev/start-worker.ps1` / `start-ai-api.ps1`).
- Tests needing model files are marked `@pytest.mark.models` and skip only if the files are missing (CI); register the marker in `pyproject.toml`.
- Tests: pytest; unit tests pure (no DB/network); integration tests against `civicbrain_test`; golden images with tolerances; fixed seeds; fake OSRM matrices. `.\.venv\Scripts\python -m pytest -q` green before commit. Lint with `ruff check`.
