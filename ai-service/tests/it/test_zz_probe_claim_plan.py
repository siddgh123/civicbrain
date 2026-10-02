"""V4 fn_claim_jobs can claim MORE jobs than its limit - and the worker copes with it.

fn_claim_jobs is `UPDATE jobs … WHERE job_id IN (SELECT … LIMIT n FOR UPDATE SKIP LOCKED)`. When the planner puts that
subquery on the inner side of a nested-loop semi join it is re-scanned per outer row; rows the statement already updated
are skipped ("self-modified"), so LIMIT picks the next queued job. The plan depends on table statistics, which made a
worker test fail once in about 8 runs (P02). Here the plan is forced with planner settings, so the effect is
deterministic. V1-V5 are frozen; a fix in the database would be a new migration (asked in P02).
"""

import threading
import uuid

import pytest
from sqlalchemy import event, text

from app.config import get_settings
from app.db import make_engine
from worker.handlers import HANDLERS
from worker.run import Worker

pytestmark = pytest.mark.integration

# planner settings that produce the re-scanning plan (Nested Loop Semi Join with the LIMIT subquery inside)
RESCAN_PLAN = ("enable_hashjoin", "enable_mergejoin", "enable_hashagg", "enable_material", "enable_sort")


def _force_rescan_plan(conn) -> None:
    for knob in RESCAN_PLAN:
        conn.execute(text(f"SET LOCAL {knob} = off"))


@pytest.fixture(scope="module")
def rescan_engine():
    """A civicbrain_ai engine whose sessions use the re-scanning plan."""
    engine = make_engine(get_settings())

    @event.listens_for(engine, "connect")
    def _session_settings(dbapi_conn, _record):
        with dbapi_conn.cursor() as cur:
            for knob in RESCAN_PLAN:
                cur.execute(f"SET {knob} = off")
        dbapi_conn.commit()

    yield engine
    engine.dispose()


def _worker(engine, handlers) -> Worker:
    settings = get_settings().model_copy(update={"worker_id": f"it-worker-{uuid.uuid4().hex[:8]}"})
    return Worker(settings, engine=engine, handlers=handlers)


def test_v4_claim_can_return_more_rows_than_the_limit(it_data, admin_engine):
    for _ in range(3):
        it_data.new_complaint(priority=0)
    with admin_engine.connect() as conn:
        tx = conn.begin()
        _force_rescan_plan(conn)
        claimed = conn.execute(text("SELECT job_id FROM fn_claim_jobs('it-probe', ARRAY['ANALYZE_COMPLAINT'], 1)")).all()
        tx.rollback()
    assert len(claimed) > 1, "fn_claim_jobs now honours its limit - the worker's extra-row handling can be simplified"


def test_over_claimed_jobs_are_all_processed_in_queue_order(it_data, rescan_engine):
    _, first_id = it_data.new_complaint(priority=0)
    _, second_id = it_data.new_complaint(priority=1)
    seen = []
    worker = _worker(rescan_engine, {**HANDLERS, "ANALYZE_COMPLAINT": lambda ctx: seen.append(ctx.job.job_id)})

    claimed = worker.run_once()

    assert [j.job_id for j in claimed] == [first_id, second_id]  # two jobs for limit 1, in queue order
    assert seen == [first_id, second_id]
    assert {it_data.job(first_id)["status"], it_data.job(second_id)["status"]} == {"SUCCEEDED"}  # nothing left RUNNING


def test_stop_releases_over_claimed_jobs_that_did_not_start(it_data, rescan_engine):
    _, first_id = it_data.new_complaint(priority=0)
    _, second_id = it_data.new_complaint(priority=1)
    seen = []

    def handler(ctx):
        seen.append(ctx.job.job_id)
        worker.request_stop()

    worker = _worker(rescan_engine, {**HANDLERS, "ANALYZE_COMPLAINT": handler})
    loop = threading.Thread(target=worker.run, daemon=True)
    loop.start()
    loop.join(30)

    assert not loop.is_alive()
    assert seen == [first_id]
    assert it_data.job(first_id)["status"] == "SUCCEEDED"
    second = it_data.job(second_id)
    assert (second["status"], second["attempts"], second["locked_by"]) == ("QUEUED", 1, None)
    assert second["last_error"] == f"Released: worker {worker.worker_id} stopped before this claimed job started"
