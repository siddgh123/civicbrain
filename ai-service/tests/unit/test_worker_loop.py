"""Worker loop without a database: a missing schema or a database outage is waited out, not a crash."""

from contextlib import contextmanager

import pytest

from app.config import get_settings
from app.errors import DependencyError
from worker import run as worker_run
from worker.run import Worker


@contextmanager
def _no_db(engine=None):
    yield None


def test_missing_schema_is_a_dependency_error(monkeypatch):
    monkeypatch.setattr(worker_run, "session_scope", _no_db)
    monkeypatch.setattr(worker_run, "schema_ready", lambda s: False)
    worker = Worker(get_settings(), engine=object())
    with pytest.raises(DependencyError, match="no CivicBrain schema yet"):
        worker.run_once()


def test_loop_waits_and_retries_when_the_schema_is_missing(monkeypatch, caplog):
    worker = Worker(get_settings(), engine=object())
    calls = []

    def not_ready(s):
        calls.append(1)
        if len(calls) == 2:
            worker.request_stop()  # end the test after the second check
        return False

    monkeypatch.setattr(worker_run, "session_scope", _no_db)
    monkeypatch.setattr(worker_run, "schema_ready", not_ready)
    monkeypatch.setattr(worker_run, "DB_RETRY_WAIT_SECONDS", 0.01)
    caplog.set_level("INFO")
    worker.run()  # returns instead of raising
    assert len(calls) == 2
    assert "no CivicBrain schema yet" in caplog.text
    assert "retrying in 0.01 s" in caplog.text
