"""The AI worker loop (docs/06_AI_PIPELINE.md sec. 1).

    python -m worker.run        (from ai-service/, see scripts/dev/start-worker.ps1)

- No schema yet (fresh dev database before the backend's Flyway, P04) or database down: log, wait 10 s, retry.
- At start: jobs this WORKER_ID still holds as RUNNING (hard stop by start-all.ps1 -Restart) are finished as
  failed through fn_finish_job, so they retry after 1-5 min instead of waiting 15 min for the stale check.
- Every WORKER_POLL_SECONDS: claim 1 job (fn_claim_jobs), run its handler with a hard time limit, then
  fn_finish_job(id, true) or fn_finish_job(id, false, '<ExceptionType>: <message>').
- Every 5 min: fn_requeue_stale_jobs('15 minutes').
- Daily 02:00 IST: priority recompute of the open non-synthetic complaints (the wait-time factor grows). A worker that
  was not running at 02:00 (laptop off) catches up once at its next start; the last run is read from the database.
- Ctrl+C / SIGTERM / Ctrl+Break: finish the current job, then exit. A second Ctrl+C stops at once (the job is
  then recovered at the next start).
"""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.exc import InterfaceError, OperationalError

from app.config import (
    DB_RETRY_WAIT_SECONDS,
    JOB_TIMEOUT_SECONDS,
    STALE_JOB_AFTER,
    STALE_REQUEUE_EVERY_SECONDS,
    WORKER_JOB_TYPES,
    Settings,
    get_settings,
)
from app.db import get_engine, schema_ready, session_scope
from app.errors import ConfigError, DataError, DependencyError, JobTimeoutError
from app.logging_setup import configure_logging
from app.models_check import check_models
from pipeline import priority
from worker import jobs as jobstore
from worker.handlers import HANDLERS, Handler, JobContext, get_handler

log = logging.getLogger("worker")

RESTART_ERROR = "Interrupted: worker {worker_id} restarted while this job was RUNNING"
RELEASE_ERROR = "Released: worker {worker_id} stopped before this claimed job started"
DB_DOWN_ERRORS = (OperationalError, InterfaceError, DependencyError)
FINISH_TRIES = 3


def run_with_timeout(handler: Handler, ctx: JobContext, timeout_s: float, poll_s: float = 0.5) -> None:
    """Run the handler in a daemon thread; raise JobTimeoutError (and set ctx.cancelled) after timeout_s.

    Windows has no SIGALRM, so the main thread waits in short steps (Ctrl+C stays responsive). A handler that
    is still running after its limit keeps its thread until it reaches ctx.check_cancelled().
    """
    outcome: dict[str, BaseException] = {}

    def target() -> None:
        try:
            handler(ctx)
        except BaseException as exc:  # handed to the main thread below
            outcome["error"] = exc

    thread = threading.Thread(target=target, name=f"job-{ctx.job.job_id}", daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout_s
    while thread.is_alive():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            ctx.cancelled.set()
            raise JobTimeoutError(f"{ctx.job.job_type} took longer than {timeout_s:g} s")
        thread.join(min(poll_s, remaining))
    if "error" in outcome:
        raise outcome["error"]


class Worker:
    def __init__(
        self,
        settings: Settings,
        engine: Engine | None = None,
        handlers: Mapping[str, Handler] = HANDLERS,
        timeouts: Mapping[str, float] = JOB_TIMEOUT_SECONDS,
        stale_every_s: float = STALE_REQUEUE_EVERY_SECONDS,
    ) -> None:
        self.settings = settings
        self.engine = engine or get_engine()
        self.handlers = handlers
        self.timeouts = timeouts
        self.stale_every_s = stale_every_s
        self.stop_event = threading.Event()
        self._started = False
        self._next_stale_check = 0.0  # time.monotonic(); 0 = at the first iteration
        self._priority_done_at: datetime | None = None  # last daily priority recompute (UTC); None = not read yet

    @property
    def worker_id(self) -> str:
        return self.settings.worker_id

    def _extra(self, job: jobstore.Job | None = None, **context: object) -> dict:
        extra: dict[str, object] = {"worker_id": self.worker_id}
        if job is not None:
            extra.update(job_id=job.job_id, job_type=job.job_type, complaint_id=job.complaint_id, attempts=job.attempts)
        extra.update(context)
        return extra

    def request_stop(self, *_: object) -> None:
        if not self.stop_event.is_set():
            log.info("stop requested - the current job finishes first", extra=self._extra())
        self.stop_event.set()

    # ---- start-up ----
    def startup(self) -> None:
        """Recover this worker's own RUNNING jobs and mark DEAD analyses as FAILED."""
        with session_scope(self.engine) as s:
            if not schema_ready(s):
                raise DependencyError(
                    f"database {self.settings.db_name} has no CivicBrain schema yet (no jobs table) - "
                    "the backend's Flyway migrations create it (P04)"
                )
            own = jobstore.own_running_jobs(s, self.worker_id)
            for job in own:
                status = jobstore.finish_job(s, job, False, RESTART_ERROR.format(worker_id=self.worker_id))
                log.warning("job was still RUNNING from an earlier run of this worker -> %s", status, extra=self._extra(job, status=status))
            failed = jobstore.sweep_dead_analyses(s)
        if failed:
            log.warning("%d complaint(s) with a DEAD analysis marked ai_status=FAILED", len(failed), extra=self._extra(count=len(failed)))
        self._started = True

    # ---- periodic ----
    def requeue_stale_if_due(self, now: float | None = None) -> int | None:
        """fn_requeue_stale_jobs every stale_every_s seconds. Returns the count, or None when not due."""
        now = time.monotonic() if now is None else now
        if now < self._next_stale_check:
            return None
        self._next_stale_check = now + self.stale_every_s
        with session_scope(self.engine) as s:
            count = jobstore.requeue_stale(s, STALE_JOB_AFTER)
            failed = jobstore.sweep_dead_analyses(s) if count else []
        if count:
            log.warning("requeued %d stale RUNNING job(s) (locked > %s)", count, STALE_JOB_AFTER, extra=self._extra(count=count))
        if failed:
            log.warning("%d complaint(s) with a DEAD analysis marked ai_status=FAILED", len(failed), extra=self._extra(count=len(failed)))
        return count

    def recompute_priorities_if_due(self, now: datetime | None = None) -> tuple[int, int] | None:
        """The daily 02:00 IST priority recompute. Returns (done, failed), or None when it is not due."""
        now = now or datetime.now(UTC)
        due = priority.latest_recompute_time(now)
        if self._priority_done_at is None:
            with session_scope(self.engine) as s:
                self._priority_done_at = priority.last_daily_recompute(s) or datetime.min.replace(tzinfo=UTC)
        if self._priority_done_at >= due:
            return None
        try:
            done, failed = priority.recompute_open(self.engine, now)
        except (ConfigError, DataError) as exc:  # e.g. a rule file missing: report, try again tomorrow, keep the jobs running
            log.error("daily priority recompute not possible: %s", exc, extra=self._extra(step="priority"))
            self._priority_done_at = now
            return None
        self._priority_done_at = now
        log.info("daily priority recompute: %d complaint(s) updated, %d skipped", done, failed,
                 extra=self._extra(count=done, step="priority"))
        return done, failed

    # ---- one iteration ----
    def run_once(self) -> list[jobstore.Job]:
        """Claim one job and process it. Returns the claimed jobs ([] when the queue was empty).

        fn_claim_jobs(limit 1) can return more than one job (V4 re-scan effect, see worker/jobs.py). They are all
        RUNNING and locked by this worker, so all are processed in queue order; after a stop request the ones that
        have not started are released (fn_finish_job false -> retry in 1-5 min) instead of being left RUNNING.
        """
        if not self._started:
            self.startup()
        self.requeue_stale_if_due()
        self.recompute_priorities_if_due()
        with session_scope(self.engine) as s:
            claimed = jobstore.claim_jobs(s, self.worker_id, WORKER_JOB_TYPES, 1)
        if len(claimed) > 1:
            count = len(claimed)
            log.warning("fn_claim_jobs returned %d jobs for limit 1 - processing all of them", count, extra=self._extra(count=count))
        for index, job in enumerate(claimed):
            if index > 0 and self.stop_event.is_set():
                self._release(claimed[index:])
                break
            self.process(job)
        return claimed

    def _release(self, jobs: list[jobstore.Job]) -> None:
        with session_scope(self.engine) as s:
            for job in jobs:
                status = jobstore.finish_job(s, job, False, RELEASE_ERROR.format(worker_id=self.worker_id))
                log.warning("claimed job released before it started (worker stopping) -> %s", status, extra=self._extra(job, status=status))

    def process(self, job: jobstore.Job) -> str:
        """Run the job's handler with its time limit and finish the job. Returns the job's new status."""
        ctx = JobContext(job, self.settings)
        timeout_s = float(self.timeouts.get(job.job_type, 120))
        log.info("job claimed", extra=self._extra(job, step="start"))
        started = time.monotonic()
        error: str | None = None
        error_type: str | None = None
        try:
            run_with_timeout(get_handler(job.job_type, self.handlers), ctx, timeout_s)
        except Exception as exc:
            error_type = type(exc).__name__
            error = f"{error_type}: {exc}" if str(exc) else error_type
        duration_ms = int((time.monotonic() - started) * 1000)
        status = self._finish(job, error)
        if error is None:
            log.info("job finished", extra=self._extra(job, status=status, duration_ms=duration_ms))
        else:
            log.warning("job failed: %s", error, extra=self._extra(job, status=status, error_type=error_type, duration_ms=duration_ms))
            if status == "DEAD" and job.complaint_id is not None:
                log.error("analysis is DEAD - complaint ai_status=FAILED (officer: Needs review)", extra=self._extra(job, status=status))
        return status

    def _finish(self, job: jobstore.Job, error: str | None) -> str:
        """fn_finish_job with a few retries; if the database stays down the job is recovered later."""
        for attempt in range(1, FINISH_TRIES + 1):
            try:
                with session_scope(self.engine) as s:
                    return jobstore.finish_job(s, job, error is None, error)
            except DB_DOWN_ERRORS as exc:
                if attempt == FINISH_TRIES:
                    raise DependencyError(f"could not finish job {job.job_id}: database not available") from exc
                self.stop_event.wait(2.0 * attempt)
        raise AssertionError("unreachable")

    # ---- loop ----
    def run(self) -> None:
        log.info(
            "worker started: database %s, polling every %g s, job types %s",
            self.settings.db_name, self.settings.worker_poll_seconds, ",".join(WORKER_JOB_TYPES), extra=self._extra(),
        )
        while not self.stop_event.is_set():
            try:
                processed = self.run_once()
            except DB_DOWN_ERRORS as exc:
                # driver messages are not logged (they can carry connection details); our own messages are safe
                reason = str(exc) if isinstance(exc, DependencyError) else f"database not available ({type(exc).__name__})"
                log.error("%s - retrying in %g s", reason, DB_RETRY_WAIT_SECONDS, extra=self._extra())
                self.stop_event.wait(DB_RETRY_WAIT_SECONDS)
                continue
            if not processed:
                self.stop_event.wait(self.settings.worker_poll_seconds)
        log.info("worker stopped", extra=self._extra())


def install_signal_handlers(worker: Worker) -> None:
    def on_signal(signum: int, frame: object) -> None:
        if worker.stop_event.is_set():
            raise KeyboardInterrupt  # second signal: stop now
        worker.request_stop()

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):  # SIGBREAK = Ctrl+Break on Windows
        sig = getattr(signal, name, None)
        if sig is not None:
            signal.signal(sig, on_signal)


def main() -> int:
    try:
        settings = get_settings()
    except ConfigError as exc:
        configure_logging("INFO", service="worker")
        log.critical("worker not started: %s", exc)
        return 2
    configure_logging(settings.log_level, service="worker")
    model_problems = check_models(settings)
    if model_problems:
        if settings.require_models:
            log.critical("worker not started - required model files missing or changed: %s", "; ".join(model_problems))
            return 2
        log.warning("model files not ready, REQUIRE_MODELS=false so the worker still runs: %s", "; ".join(model_problems))
    worker = Worker(settings)
    install_signal_handlers(worker)
    worker.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
