"""Job handlers by job_type (docs/06_AI_PIPELINE.md).

P02 placeholders: ANALYZE_COMPLAINT (real pipeline in P12) and OPTIMIZE_PLAN (P17) raise NotImplementedError,
so their jobs fail cleanly, retry and end DEAD. ANALYZE_IMAGE and BLUR_IMAGE are Phase 2 (not in the 7-day
MVP): they finish as success with a "skipped (MVP)" log line.

A handler gets a JobContext. It writes its results in ONE transaction and calls `ctx.check_cancelled()`
right before it commits, so a job that hit its time limit never writes late results.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from app.config import Settings
from app.errors import DataError, JobTimeoutError
from worker.jobs import Job

log = logging.getLogger("worker.handlers")


@dataclass
class JobContext:
    job: Job
    settings: Settings
    cancelled: threading.Event = field(default_factory=threading.Event)

    def check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise JobTimeoutError(f"job {self.job.job_id} was cancelled after its time limit")

    def log_extra(self, step: str | None = None) -> dict:
        return {"job_id": self.job.job_id, "job_type": self.job.job_type, "complaint_id": self.job.complaint_id, "step": step}


Handler = Callable[[JobContext], None]


def analyze_complaint(ctx: JobContext) -> None:
    raise NotImplementedError("ANALYZE_COMPLAINT pipeline is built in P12")


def optimize_plan(ctx: JobContext) -> None:
    raise NotImplementedError("OPTIMIZE_PLAN is built in P17")


def analyze_image(ctx: JobContext) -> None:
    log.info("ANALYZE_IMAGE skipped (MVP)", extra=ctx.log_extra("skip"))


def blur_image(ctx: JobContext) -> None:
    log.info("BLUR_IMAGE skipped (MVP)", extra=ctx.log_extra("skip"))


HANDLERS: Mapping[str, Handler] = MappingProxyType(
    {
        "ANALYZE_COMPLAINT": analyze_complaint,
        "ANALYZE_IMAGE": analyze_image,
        "OPTIMIZE_PLAN": optimize_plan,
        "BLUR_IMAGE": blur_image,
    }
)


def get_handler(job_type: str, handlers: Mapping[str, Handler] = HANDLERS) -> Handler:
    handler = handlers.get(job_type)
    if handler is None:
        raise DataError(f"no handler for job type {job_type}")
    return handler
