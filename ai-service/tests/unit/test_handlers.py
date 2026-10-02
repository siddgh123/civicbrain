"""Dispatcher by job_type and the per-job time limit (docs/06_AI_PIPELINE.md sec. 1)."""

import threading
import time

import pytest

from app.config import WORKER_JOB_TYPES, Settings
from app.errors import DataError, JobTimeoutError
from worker.handlers import HANDLERS, JobContext, analyze_complaint, analyze_image, blur_image, get_handler, optimize_plan
from worker.jobs import Job
from worker.run import run_with_timeout


def _ctx(job_type: str = "ANALYZE_COMPLAINT") -> JobContext:
    return JobContext(Job(job_id=7, job_type=job_type, ref_id=42), Settings.model_construct(worker_id="unit"))


def test_the_four_job_types_have_handlers():
    assert set(HANDLERS) == set(WORKER_JOB_TYPES) == {"ANALYZE_COMPLAINT", "ANALYZE_IMAGE", "OPTIMIZE_PLAN", "BLUR_IMAGE"}


@pytest.mark.parametrize(
    ("job_type", "handler"),
    [
        ("ANALYZE_COMPLAINT", analyze_complaint),
        ("ANALYZE_IMAGE", analyze_image),
        ("OPTIMIZE_PLAN", optimize_plan),
        ("BLUR_IMAGE", blur_image),
    ],
)
def test_dispatcher_maps_each_job_type(job_type, handler):
    assert get_handler(job_type) is handler


def test_unknown_job_type_is_a_data_error():
    with pytest.raises(DataError, match="RENDER_EXPORT"):
        get_handler("RENDER_EXPORT")


@pytest.mark.parametrize("job_type", ["ANALYZE_COMPLAINT", "OPTIMIZE_PLAN"])
def test_not_built_yet_handlers_fail_cleanly(job_type):
    with pytest.raises(NotImplementedError, match=job_type):
        get_handler(job_type)(_ctx(job_type))


@pytest.mark.parametrize("job_type", ["ANALYZE_IMAGE", "BLUR_IMAGE"])
def test_phase2_handlers_are_skipped_as_success(job_type, caplog):
    caplog.set_level("INFO")
    assert get_handler(job_type)(_ctx(job_type)) is None
    assert "skipped (MVP)" in caplog.text


def test_complaint_id_only_for_analyze_complaint():
    assert Job(1, "ANALYZE_COMPLAINT", 42).complaint_id == 42
    assert Job(2, "OPTIMIZE_PLAN", 42).complaint_id is None


def test_run_with_timeout_returns_when_the_handler_finishes():
    done = []
    run_with_timeout(lambda ctx: done.append(ctx.job.job_id), _ctx(), timeout_s=5)
    assert done == [7]


def test_run_with_timeout_passes_the_handler_error_on():
    def boom(ctx):
        raise DataError("broken image")

    with pytest.raises(DataError, match="broken image"):
        run_with_timeout(boom, _ctx(), timeout_s=5)


def test_run_with_timeout_stops_waiting_and_cancels():
    release = threading.Event()
    ctx = _ctx()
    started = time.monotonic()
    with pytest.raises(JobTimeoutError, match="ANALYZE_COMPLAINT took longer than 0.2 s"):
        run_with_timeout(lambda c: release.wait(10), ctx, timeout_s=0.2, poll_s=0.05)
    assert time.monotonic() - started < 2
    assert ctx.cancelled.is_set()
    with pytest.raises(JobTimeoutError):
        ctx.check_cancelled()  # a late handler may not commit its results
    release.set()
