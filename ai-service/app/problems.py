"""RFC 9457 Problem Details for the internal API, same shape and codes as the backend (docs/12_ERROR_HANDLING.md).

`detail` never contains stack traces, SQL, file paths, secrets or personal data. Every response carries
X-Request-Id (taken from the request when it is well-formed, else generated).
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.api")

REQUEST_ID_HEADER = "X-Request-Id"
_REQUEST_ID_OK = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

TITLES = {
    "VALIDATION_FAILED": "Request is not valid",
    "MALFORMED_REQUEST": "Request could not be read",
    "UNAUTHENTICATED": "Authentication required",
    "NOT_FOUND": "Not found",
    "ALREADY_EXISTS": "Already exists",
    "INTERNAL_ERROR": "Something went wrong",
    "DEPENDENCY_UNAVAILABLE": "Service temporarily unavailable",
}


class ProblemError(Exception):
    def __init__(self, status: int, code: str, detail: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(detail)
        self.status, self.code, self.detail, self.headers = status, code, detail, headers or {}


def request_id_of(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid or "-"


def problem_response(request: Request, status: int, code: str, detail: str, headers: dict[str, str] | None = None) -> JSONResponse:
    body = {
        "type": f"https://civicbrain.app/errors/{code}",
        "title": TITLES.get(code, code),
        "status": status,
        "code": code,
        "detail": detail,
        "requestId": request_id_of(request),
    }
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request.state.request_id = incoming if _REQUEST_ID_OK.match(incoming) else uuid.uuid4().hex
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request.state.request_id
        return response

    @app.exception_handler(ProblemError)
    async def _problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(request, exc.status, exc.code, exc.detail, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem_response(request, 400, "VALIDATION_FAILED", "One or more request values are not valid.")

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return problem_response(request, 404, "NOT_FOUND", "Not found.")
        if exc.status_code == 405:
            return problem_response(request, 405, "MALFORMED_REQUEST", "Method not allowed.")
        return problem_response(request, exc.status_code, "MALFORMED_REQUEST", "Request could not be handled.")

    async def _db_down(request: Request, exc: DBAPIError) -> JSONResponse:
        log.error("database not available", extra={"request_id": request_id_of(request), "error_type": type(exc.orig).__name__})
        return problem_response(request, 503, "DEPENDENCY_UNAVAILABLE", "Database not available.")

    app.add_exception_handler(OperationalError, _db_down)
    app.add_exception_handler(InterfaceError, _db_down)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unexpected error", extra={"request_id": request_id_of(request), "error_type": type(exc).__name__})
        return problem_response(request, 500, "INTERNAL_ERROR", f"Something went wrong. Reference: {request_id_of(request)}")
