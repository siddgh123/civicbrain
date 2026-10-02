"""Database access: SQLAlchemy 2 + psycopg3 as the role `civicbrain_ai` (docs/03_DATABASE.md sec. 5).

Jobs only through fn_claim_jobs / fn_finish_job / fn_requeue_stale_jobs (worker/jobs.py). A complaint
status change by the worker always runs `set_system_actor()` first, in the same transaction.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.config import Settings, get_settings

STATEMENT_TIMEOUT_MS = 60_000  # no single statement of the worker or the API should take a minute
CONNECT_TIMEOUT_S = 5


def make_engine(settings: Settings) -> Engine:
    url = URL.create(
        "postgresql+psycopg",
        username=settings.db_ai_user,
        password=settings.db_ai_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
        hide_parameters=True,  # SQL parameters never appear in error messages or logs
        connect_args={
            "connect_timeout": CONNECT_TIMEOUT_S,
            "application_name": f"civicbrain-ai {settings.worker_id}"[:63],
            "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c TimeZone=UTC",
        },
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """The process-wide engine, created on first use (never at import time)."""
    return make_engine(get_settings())


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """One transaction: commit when the block ends normally, roll back on any exception."""
    with Session(engine or get_engine()) as session, session.begin():
        yield session


def set_system_actor(conn: Connection | Session) -> None:
    """Mark the current transaction as a SYSTEM actor for the V2 status trigger (transaction-local)."""
    conn.execute(text("SELECT set_config('civicbrain.actor_role', 'SYSTEM', true)"))


SCHEMA_READY_SQL = text(
    "SELECT to_regclass('public.jobs') IS NOT NULL AND to_regprocedure('public.fn_claim_jobs(text, text[], integer)') IS NOT NULL"
)


def schema_ready(conn: Connection | Session) -> bool:
    """True when the migrations have run (a fresh dev database stays empty until the backend's Flyway, P04)."""
    return bool(conn.execute(SCHEMA_READY_SQL).scalar_one())


def db_status(engine: Engine | None = None) -> str:
    """'ok', 'schema missing' (connected, migrations not run yet) or 'unavailable' - for /health."""
    try:
        with (engine or get_engine()).connect() as conn:
            return "ok" if schema_ready(conn) else "schema missing"
    except Exception:  # any failure means "not reachable" for /health
        return "unavailable"
