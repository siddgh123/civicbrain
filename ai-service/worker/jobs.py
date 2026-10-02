"""Job table access for the worker (docs/03_DATABASE.md sec. 3.8, docs/06_AI_PIPELINE.md sec. 1).

Job state changes go only through the V4 functions: fn_claim_jobs, fn_finish_job, fn_requeue_stale_jobs.
fn_claim_jobs counts the attempt when it claims; fn_finish_job(false) re-queues after 1 and 5 minutes and
makes the 3rd failure DEAD (max_attempts = 3). A DEAD ANALYZE_COMPLAINT sets complaints.ai_status = FAILED,
so the officer sees it in "Needs review" (the complaint stays SUBMITTED).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import set_system_actor

ANALYZE_COMPLAINT = "ANALYZE_COMPLAINT"

# NOTE: V4's fn_claim_jobs is `UPDATE … WHERE job_id IN (SELECT … LIMIT n FOR UPDATE SKIP LOCKED)`. When the planner
# re-scans that subquery (nested-loop semi join), rows the statement already updated are skipped and the LIMIT picks the
# next ones, so it can claim MORE than n jobs (reproduced in tests/it/test_zz_probe_claim_plan.py). Every returned row is
# RUNNING and locked by this worker, so the caller must process or release all of them (worker/run.py).
CLAIM_SQL = text(
    "SELECT job_id, job_type, ref_id, payload, attempts, max_attempts, priority, run_after "
    "FROM fn_claim_jobs(CAST(:worker_id AS text), CAST(:job_types AS text[]), CAST(:limit AS integer))"
)
FINISH_SQL = text("SELECT fn_finish_job(CAST(:job_id AS bigint), CAST(:success AS boolean), CAST(:error AS text))")
REQUEUE_STALE_SQL = text("SELECT fn_requeue_stale_jobs(CAST(:stale AS interval))")
OWN_RUNNING_SQL = text("SELECT job_id, job_type, ref_id FROM jobs WHERE status = 'RUNNING' AND locked_by = :worker_id ORDER BY job_id")
MARK_AI_FAILED_SQL = text("UPDATE complaints SET ai_status = 'FAILED' WHERE complaint_id = :complaint_id AND ai_status <> 'FAILED'")
# Complaints whose latest analysis job is DEAD but still look pending (DEAD made by fn_requeue_stale_jobs).
SWEEP_DEAD_ANALYSES_SQL = text(
    """
    UPDATE complaints c
       SET ai_status = 'FAILED'
      FROM (SELECT DISTINCT ON (ref_id) ref_id, status
              FROM jobs
             WHERE job_type = 'ANALYZE_COMPLAINT'
             ORDER BY ref_id, job_id DESC) j
     WHERE j.ref_id = c.complaint_id
       AND j.status = 'DEAD'
       AND c.ai_status IN ('PENDING', 'PROCESSING')
    RETURNING c.complaint_id
    """
)


@dataclass(frozen=True)
class Job:
    job_id: int
    job_type: str
    ref_id: int
    payload: dict = field(default_factory=dict)
    attempts: int = 1
    max_attempts: int = 3

    @property
    def complaint_id(self) -> int | None:
        return self.ref_id if self.job_type == ANALYZE_COMPLAINT else None


def _payload(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        return json.loads(value)
    return {}


def claim_jobs(s: Session, worker_id: str, job_types: Sequence[str], limit: int = 1) -> list[Job]:
    """fn_claim_jobs, in queue order (priority, run_after, job_id). May return more than `limit` jobs (see CLAIM_SQL)."""
    rows = s.execute(CLAIM_SQL, {"worker_id": worker_id, "job_types": list(job_types), "limit": limit}).mappings().all()
    rows = sorted(rows, key=lambda r: (r["priority"], r["run_after"], r["job_id"]))
    return [
        Job(int(r["job_id"]), r["job_type"], int(r["ref_id"]), _payload(r["payload"]), int(r["attempts"]), int(r["max_attempts"]))
        for r in rows
    ]


def finish_job(s: Session, job: Job, success: bool, error: str | None = None) -> str:
    """fn_finish_job + the DEAD rule, in the caller's transaction. Returns SUCCEEDED, QUEUED or DEAD."""
    params = {"job_id": job.job_id, "success": success, "error": None if success else (error or "")[:4000]}
    status = s.execute(FINISH_SQL, params).scalar_one()
    if status == "DEAD" and job.complaint_id is not None:
        mark_analysis_failed(s, job.complaint_id)
    return str(status)


def mark_analysis_failed(s: Session, complaint_id: int) -> None:
    set_system_actor(s)
    s.execute(MARK_AI_FAILED_SQL, {"complaint_id": complaint_id})


def requeue_stale(s: Session, stale: str) -> int:
    """fn_requeue_stale_jobs: RUNNING rows locked longer than `stale` -> QUEUED (or DEAD at max attempts)."""
    return int(s.execute(REQUEUE_STALE_SQL, {"stale": stale}).scalar_one())


def sweep_dead_analyses(s: Session) -> list[int]:
    """ai_status = FAILED for complaints whose latest ANALYZE_COMPLAINT job is DEAD. Returns their ids."""
    set_system_actor(s)
    return [int(r[0]) for r in s.execute(SWEEP_DEAD_ANALYSES_SQL).all()]


def own_running_jobs(s: Session, worker_id: str) -> list[Job]:
    """Jobs this WORKER_ID still holds as RUNNING - left behind by a hard stop (start-all.ps1 -Restart)."""
    return [Job(int(r[0]), r[1], int(r[2])) for r in s.execute(OWN_RUNNING_SQL, {"worker_id": worker_id}).all()]
