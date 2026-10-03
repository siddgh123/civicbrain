"""Internal FastAPI of the AI service (docs/04_API_CONTRACT.md sec. 10). Bound to 127.0.0.1:8001 only.

    uvicorn app.main:app --host 127.0.0.1 --port 8001      (from ai-service/, see scripts/dev/start-ai-api.ps1)

GET /health                    no auth   {status, db, osrm, modelsLoaded, models: {<manifest name>: "ok" | problem}}
GET /v1/models                 service JWT
POST /v1/jobs/{jobId}/requeue  service JWT - a new QUEUED row for a finished job (the backend's admin page
                               inserts that row itself; this endpoint exists for manual use)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request
from fastapi import Path as PathParam
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import db, problems
from app.config import get_settings
from app.errors import ConfigError
from app.logging_setup import configure_logging
from app.models_check import check_models, describe_models, model_status
from app.problems import ProblemError
from app.security import ServiceAuthError, verify_service_jwt

log = logging.getLogger("app.api")

# Copy a finished job into a new QUEUED row; the partial unique index allows one active job per (type, ref).
REQUEUE_SQL = text(
    """
    INSERT INTO jobs (job_type, ref_id, payload, priority)
    SELECT job_type, ref_id, payload, priority
      FROM jobs
     WHERE job_id = :job_id AND status IN ('SUCCEEDED', 'FAILED', 'DEAD')
    ON CONFLICT (job_type, ref_id) WHERE status IN ('QUEUED', 'RUNNING') DO NOTHING
    RETURNING job_id
    """
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()  # ConfigError with a clear message stops the start-up
    configure_logging(settings.log_level, service="ai-api")
    model_problems = check_models(settings)
    if model_problems:
        if settings.require_models:
            raise ConfigError("required model files missing or changed: " + "; ".join(model_problems))
        log.warning("model files not ready, REQUIRE_MODELS=false so the API still starts: %s", "; ".join(model_problems))
    app.state.model_problems = model_problems
    app.state.model_status = model_status(settings, model_problems)  # checked once at start (hashing is slow)
    log.info("AI API ready (database %s, routing %s)", settings.db_name, settings.routing_mode)
    yield
    if db.get_engine.cache_info().currsize:
        db.get_engine().dispose()


app = FastAPI(title="CivicBrain AI service", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
problems.install(app)


def require_service_token(authorization: Annotated[str | None, Header()] = None) -> dict:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ProblemError(401, "UNAUTHENTICATED", "Service token missing.", {"WWW-Authenticate": "Bearer"})
    try:
        return verify_service_jwt(token.strip(), get_settings().jwt_key)
    except ServiceAuthError as exc:
        log.warning("service token rejected (%s)", exc)  # the reason only, never the token
        raise ProblemError(401, "UNAUTHENTICATED", "Service token invalid or expired.", {"WWW-Authenticate": "Bearer"}) from None


ServiceToken = Annotated[dict, Depends(require_service_token)]


@app.get("/health")
def health(request: Request) -> JSONResponse:
    settings = get_settings()
    db_state = db.db_status()
    model_problems = getattr(request.app.state, "model_problems", None)
    body = {
        "status": "ok" if db_state == "ok" else "degraded",
        "db": db_state,
        "osrm": "not used (haversine)" if settings.routing_mode == "haversine" else "not checked",
        "modelsLoaded": model_problems == [],
        "models": getattr(request.app.state, "model_status", None) or {},  # {} = start-up check has not run
    }
    return JSONResponse(body, status_code=200 if db_state == "ok" else 503)


@app.get("/v1/models")
def models(_: ServiceToken) -> dict:
    return describe_models(get_settings())


@app.post("/v1/jobs/{job_id}/requeue", status_code=202)
def requeue_job(job_id: Annotated[int, PathParam(gt=0, le=2**63 - 1)], claims: ServiceToken) -> JSONResponse:
    status = None
    with db.session_scope() as s:
        new_id = s.execute(REQUEUE_SQL, {"job_id": job_id}).scalar_one_or_none()
        if new_id is None:
            status = s.execute(text("SELECT status FROM jobs WHERE job_id = :id"), {"id": job_id}).scalar_one_or_none()
    if new_id is None:
        if status is None:
            raise ProblemError(404, "NOT_FOUND", "Not found.")
        raise ProblemError(409, "ALREADY_EXISTS", "This job, or another one for the same item, is still queued or running.")
    log.info("job requeued by %s as job %s", claims.get("sub", "service"), new_id, extra={"job_id": job_id})
    return JSONResponse({"jobId": new_id, "requeuedFrom": job_id, "status": "QUEUED"}, status_code=202)
