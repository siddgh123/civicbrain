"""Worker loop without a database: a missing schema or a database outage is waited out, not a crash."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from app.config import IST, get_settings
from app.errors import ConfigError, DependencyError
from pipeline import priority
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


# ---- daily 02:00 IST priority recompute (docs/06_AI_PIPELINE.md sec. 1) ----

def _ist(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=IST)


@pytest.mark.parametrize(
    ("now", "due"),
    [(_ist(3, 1, 59), _ist(2, 2)), (_ist(3, 2, 0), _ist(3, 2)), (_ist(3, 23, 59), _ist(3, 2)), (_ist(4, 0, 0), _ist(3, 2))],
)
def test_latest_recompute_time_is_the_last_02_00_ist(now, due):
    assert priority.latest_recompute_time(now) == due
    assert priority.latest_recompute_time(now.astimezone(UTC)).tzinfo == UTC


def _recompute_worker(monkeypatch, last_run=None, result=(3, 0)):
    worker = Worker(get_settings(), engine=object())
    calls = []

    def recompute(engine, as_of):
        calls.append(as_of)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(worker_run, "session_scope", _no_db)
    monkeypatch.setattr(worker_run.priority, "last_daily_recompute", lambda s: last_run)
    monkeypatch.setattr(worker_run.priority, "recompute_open", recompute)
    return worker, calls


def test_daily_recompute_runs_once_per_day_and_catches_up_after_a_missed_02_00(monkeypatch):
    worker, calls = _recompute_worker(monkeypatch)  # never ran before (no DAILY_RECOMPUTE row)
    start = _ist(3, 1, 30)
    assert worker.recompute_priorities_if_due(start) == (3, 0)  # catch-up for yesterday's 02:00
    assert worker.recompute_priorities_if_due(_ist(3, 1, 50)) is None
    assert worker.recompute_priorities_if_due(_ist(3, 2, 0)) == (3, 0)  # today's 02:00
    assert worker.recompute_priorities_if_due(_ist(3, 12, 0)) is None
    assert worker.recompute_priorities_if_due(_ist(4, 2, 1)) == (3, 0)
    assert calls == [start, _ist(3, 2, 0), _ist(4, 2, 1)]


def test_no_catch_up_when_the_database_shows_todays_run(monkeypatch):
    worker, calls = _recompute_worker(monkeypatch, last_run=_ist(3, 2, 0) + timedelta(seconds=5))
    assert worker.recompute_priorities_if_due(_ist(3, 9, 0)) is None
    assert calls == []


def test_missing_rule_files_do_not_stop_the_worker(monkeypatch, caplog):
    worker, calls = _recompute_worker(monkeypatch, result=ConfigError("priority rule file missing: priority_rules.csv (data/priority)"))
    caplog.set_level("ERROR")
    assert worker.recompute_priorities_if_due(_ist(3, 9, 0)) is None
    assert "daily priority recompute not possible" in caplog.text
    assert worker.recompute_priorities_if_due(_ist(3, 9, 5)) is None  # not retried every poll - tomorrow again
    assert len(calls) == 1
