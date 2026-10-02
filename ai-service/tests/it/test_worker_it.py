"""Worker loop against the test database (docs/06_AI_PIPELINE.md sec. 1, NFR-03).

Each test inserts its own user + complaint as the owner; the V4 trigger enqueues ANALYZE_COMPLAINT and
the worker under test (role civicbrain_ai) claims it. Rows are deleted again by the it_data fixture.
"""

import threading
import uuid

import pytest

from app.config import get_settings
from worker.handlers import HANDLERS
from worker.run import Worker

pytestmark = pytest.mark.integration


def _ids(jobs) -> list[int]:
    return [j.job_id for j in jobs]


def _worker(engine, handlers=HANDLERS, worker_id: str | None = None) -> Worker:
    settings = get_settings().model_copy(update={"worker_id": worker_id or f"it-worker-{uuid.uuid4().hex[:8]}"})
    return Worker(settings, engine=engine, handlers=handlers)


def test_trigger_enqueues_and_failing_handler_is_retried_after_1_then_5_minutes(it_data, ai_engine):
    complaint_id, job_id = it_data.new_complaint()
    worker = _worker(ai_engine)  # ANALYZE_COMPLAINT is not built yet (P12): the handler fails

    assert _ids(worker.run_once()) == [job_id]
    job = it_data.job(job_id)
    assert (job["status"], job["attempts"], job["locked_by"]) == ("QUEUED", 1, None)
    assert job["run_after_future"] and 50 < job["run_after_in_s"] <= 60  # retry after 1 minute
    assert job["last_error"].startswith("NotImplementedError: ANALYZE_COMPLAINT")
    assert it_data.complaint(complaint_id) == {"status": "SUBMITTED", "ai_status": "PENDING"}

    assert job_id not in _ids(worker.run_once())  # not claimable before run_after
    it_data.set_job(job_id, run_after="now")
    assert _ids(worker.run_once()) == [job_id]
    job = it_data.job(job_id)
    assert (job["status"], job["attempts"]) == ("QUEUED", 2)
    assert 290 < job["run_after_in_s"] <= 300  # retry after 5 minutes


def test_third_failure_is_dead_and_marks_the_analysis_failed(it_data, ai_engine):
    complaint_id, job_id = it_data.new_complaint()
    it_data.set_job(job_id, attempts=2)  # two earlier failed attempts
    assert _ids(_worker(ai_engine).run_once()) == [job_id]
    job = it_data.job(job_id)
    assert (job["status"], job["attempts"]) == ("DEAD", 3)
    assert job["finished_at"] is not None
    # the complaint stays SUBMITTED for the officer's "Needs review" tab
    assert it_data.complaint(complaint_id) == {"status": "SUBMITTED", "ai_status": "FAILED"}


def test_successful_job_is_succeeded(it_data, ai_engine):
    complaint_id, job_id = it_data.new_complaint()
    seen = []
    worker = _worker(ai_engine, handlers={**HANDLERS, "ANALYZE_COMPLAINT": lambda ctx: seen.append(ctx.job.complaint_id)})
    assert _ids(worker.run_once()) == [job_id]
    assert seen == [complaint_id]
    job = it_data.job(job_id)
    assert (job["status"], job["attempts"], job["last_error"], job["locked_by"]) == ("SUCCEEDED", 1, None, None)
    assert job["finished_at"] is not None


def test_handler_timeout_fails_the_job(it_data, ai_engine):
    _, job_id = it_data.new_complaint()
    release = threading.Event()
    worker = _worker(ai_engine, handlers={**HANDLERS, "ANALYZE_COMPLAINT": lambda ctx: release.wait(10)})
    worker.timeouts = {"ANALYZE_COMPLAINT": 0.3}
    assert _ids(worker.run_once()) == [job_id]
    release.set()
    job = it_data.job(job_id)
    assert job["status"] == "QUEUED"
    assert job["last_error"].startswith("JobTimeoutError: ANALYZE_COMPLAINT took longer than 0.3 s")


def test_stale_running_job_is_requeued(it_data, ai_engine):
    _, stale_id = it_data.new_complaint()
    _, fresh_id = it_data.new_complaint(priority=1)
    it_data.set_job(stale_id, status="RUNNING", attempts=1, locked_by="it-crashed-worker", locked_minutes_ago=20)
    it_data.set_job(fresh_id, status="RUNNING", attempts=1, locked_by="it-busy-worker", locked_minutes_ago=1)
    worker = _worker(ai_engine)

    assert worker.requeue_stale_if_due() >= 1
    stale = it_data.job(stale_id)
    assert (stale["status"], stale["locked_by"]) == ("QUEUED", None)
    assert "[requeued: stale lock]" in stale["last_error"]
    assert it_data.job(fresh_id)["status"] == "RUNNING"  # a job that is still being worked on is left alone
    assert worker.requeue_stale_if_due() is None  # next check only after 5 minutes


def test_stale_job_at_max_attempts_is_dead_and_marks_the_analysis_failed(it_data, ai_engine):
    complaint_id, job_id = it_data.new_complaint()
    it_data.set_job(job_id, status="RUNNING", attempts=3, locked_by="it-crashed-worker", locked_minutes_ago=20)
    _worker(ai_engine).requeue_stale_if_due()
    assert it_data.job(job_id)["status"] == "DEAD"
    assert it_data.complaint(complaint_id)["ai_status"] == "FAILED"


def test_own_running_jobs_are_recovered_at_start(it_data, ai_engine):
    worker_id = f"it-worker-{uuid.uuid4().hex[:8]}"
    _, mine_id = it_data.new_complaint()
    _, other_id = it_data.new_complaint(priority=1)
    it_data.set_job(mine_id, status="RUNNING", attempts=1, locked_by=worker_id, locked_minutes_ago=1)
    it_data.set_job(other_id, status="RUNNING", attempts=1, locked_by="it-other-worker", locked_minutes_ago=1)

    _worker(ai_engine, worker_id=worker_id).startup()

    mine = it_data.job(mine_id)
    assert (mine["status"], mine["locked_by"]) == ("QUEUED", None)
    assert mine["last_error"] == f"Interrupted: worker {worker_id} restarted while this job was RUNNING"
    assert 0 < mine["run_after_in_s"] <= 60  # back in 1 minute, not after the 15-minute stale limit
    assert it_data.job(other_id)["status"] == "RUNNING"  # another worker's job is not touched


def test_stop_flag_ends_the_loop_after_the_current_job(it_data, ai_engine):
    _, first_id = it_data.new_complaint(priority=0)
    _, second_id = it_data.new_complaint(priority=1)
    seen = []

    def handler(ctx):
        seen.append(ctx.job.job_id)
        worker.request_stop()  # Ctrl+C arrives while this job runs

    worker = _worker(ai_engine, handlers={**HANDLERS, "ANALYZE_COMPLAINT": handler})
    loop = threading.Thread(target=worker.run, daemon=True)
    loop.start()
    loop.join(30)

    assert not loop.is_alive(), "the loop did not end after the stop request"
    assert seen == [first_id]
    assert it_data.job(first_id)["status"] == "SUCCEEDED"  # the current job was finished
    second = it_data.job(second_id)
    assert second["status"] == "QUEUED", f"left {second['status']}, locked by {second['locked_by']}"
    # never started: either not claimed at all, or claimed together with the first (V4 re-scan) and released
    assert second["attempts"] == 0 or second["last_error"].startswith("Released: worker")
