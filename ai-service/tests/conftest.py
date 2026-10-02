"""Shared test set-up (rule 30, docs/08_TEST_PLAN.md sec. 2).

- Fake values for every non-DB setting (the same ones CI uses), so tests never see real secrets or paths.
- DB_NAME = DB_TEST_NAME: tests never touch the main database; the code under test connects as civicbrain_ai.
- Integration tests insert their fixture rows through a second connection as PG_ADMIN_USER (e-mails
  it-<uuid>@it.local, no phone) and delete them in a finalizer.
- Ultralytics must never pip-install or write to %APPDATA%: set before anything imports it.
DB credentials come from the environment (CI, verify-all) or the repo-root .env, read by pydantic-settings
here - the values are never printed.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

AI_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_DIR.parent
MODELS_DIR = AI_DIR / "models"

# ---------- fake non-DB settings (CI sets the same values; gitleaks-allowlisted test key) ----------
FAKE_SETTINGS = {
    "WORKER_ID": "pytest-worker",
    "WORKER_POLL_SECONDS": "2",
    "REQUIRE_MODELS": "false",
    "ROUTING_MODE": "haversine",
    "OSRM_URL": "http://127.0.0.1:5000",
    "YOLO_WEIGHTS": str(MODELS_DIR / "yolov8s_civicbrain.onnx"),
    "MODELS_DIR": str(MODELS_DIR),
    "TEXT_EMBEDDING_MODEL_DIR": str(MODELS_DIR / "all-MiniLM-L6-v2"),
    "AI_SERVICE_JWT_SECRET": "dGVzdC1vbmx5LWFpLXNlcnZpY2Utand0LXNlY3JldC0zMmI=",
    "AI_API_HOST": "127.0.0.1",
    "AI_API_PORT": "8001",
    "STORAGE_ROOT": str(REPO_ROOT / "storage" / "pytest"),
    "BLUR_ENABLED": "false",
    "LOG_LEVEL": "INFO",
    "HF_HUB_OFFLINE": "1",
    "YOLO_AUTOINSTALL": "false",
    "YOLO_OFFLINE": "true",
    "YOLO_CONFIG_DIR": str(AI_DIR / ".ultralytics"),
}
os.environ.update(FAKE_SETTINGS)
os.environ.pop("LABOUR_RATE_PER_HOUR", None)


class _TestDb(BaseSettings):
    """Values only the tests need: the test database name and the owner account for fixtures."""

    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env",), env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True)

    db_test_name: str = "civicbrain_test"
    db_host: str = "localhost"
    db_port: int = 5432
    pg_admin_user: str | None = None
    pg_admin_password: SecretStr | None = None


TEST_DB = _TestDb()
if TEST_DB.db_test_name in ("", "civicbrain") or not ("test" in TEST_DB.db_test_name or "_ci" in TEST_DB.db_test_name):
    raise RuntimeError(f"DB_TEST_NAME={TEST_DB.db_test_name!r} does not look like a test database - refusing to run the tests")
os.environ["DB_NAME"] = TEST_DB.db_test_name  # rule 30: DB_NAME = DB_TEST_NAME


@pytest.fixture(autouse=True)
def _fresh_settings():
    """Each test starts with freshly created settings (tests may change the environment)."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def ai_engine():
    """The engine the code under test uses (role civicbrain_ai on the test database)."""
    from app.config import get_settings
    from app.db import make_engine

    engine = make_engine(get_settings())
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def admin_engine():
    """Owner connection for fixture rows only (the worker role cannot insert users/complaints)."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL

    if not TEST_DB.pg_admin_user or TEST_DB.pg_admin_password is None:
        pytest.fail("PG_ADMIN_USER / PG_ADMIN_PASSWORD are not set (.env or environment) - integration tests need them")
    url = URL.create(
        "postgresql+psycopg",
        username=TEST_DB.pg_admin_user,
        password=TEST_DB.pg_admin_password.get_secret_value(),
        host=TEST_DB.db_host,
        port=TEST_DB.db_port,
        database=TEST_DB.db_test_name,
    )
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5, "application_name": "civicbrain-ai pytest-admin"})
    yield engine
    engine.dispose()


class ItData:
    """Creates committed fixture rows as the owner and deletes them again (docs/08_TEST_PLAN.md sec. 2)."""

    # inside ward number 1 (docs/08_TEST_PLAN.md sec. 2 fixed points)
    LAT, LON = 18.7440, 73.6760

    def __init__(self, engine) -> None:
        self.engine = engine
        self.user_ids: list[int] = []
        self.complaint_ids: list[int] = []

    def _sql(self, sql: str, **params):
        from sqlalchemy import text

        with self.engine.begin() as conn:
            result = conn.execute(text(sql), params)
            return result.mappings().all() if result.returns_rows else []

    def new_user(self) -> int:
        rows = self._sql(
            "INSERT INTO users (full_name, email, password_hash, role, email_verified_at) "
            "VALUES ('IT Citizen', :email, 'x-not-a-hash', 'CITIZEN', now()) RETURNING user_id",
            email=f"it-{uuid.uuid4().hex}@it.local",
        )
        self.user_ids.append(int(rows[0]["user_id"]))
        return self.user_ids[-1]

    def new_complaint(self, priority: int = 0) -> tuple[int, int]:
        """A real (non-synthetic) SUBMITTED complaint; the V4 trigger enqueues ANALYZE_COMPLAINT.

        The job's priority is lowered to `priority` (0 = before anything else in the queue), so the
        worker under test claims exactly this job. Returns (complaint_id, job_id).
        """
        from sqlalchemy import text

        user_id = self.user_ids[0] if self.user_ids else self.new_user()
        with self.engine.begin() as conn:  # one transaction: actor settings are transaction-local, like the backend's
            conn.execute(
                text("SELECT set_config('civicbrain.actor_role', 'CITIZEN', true), set_config('civicbrain.actor_user_id', :uid, true)"),
                {"uid": str(user_id)},
            )
            complaint_id = conn.execute(
                text(
                    "INSERT INTO complaints (user_id, category_id, title, description, location, location_source) "
                    "VALUES (:uid, (SELECT min(category_id) FROM complaint_categories), 'IT pothole', 'integration test complaint', "
                    "        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 'BROWSER_GPS') RETURNING complaint_id"
                ),
                {"uid": user_id, "lat": self.LAT, "lon": self.LON},
            ).scalar_one()
        self.complaint_ids.append(complaint_id)
        jobs = self._sql(
            "UPDATE jobs SET priority = :p WHERE job_type = 'ANALYZE_COMPLAINT' AND ref_id = :cid AND status = 'QUEUED' RETURNING job_id",
            p=priority, cid=complaint_id,
        )
        assert len(jobs) == 1, "the V4 trigger should have enqueued exactly one ANALYZE_COMPLAINT job"
        return complaint_id, int(jobs[0]["job_id"])

    def set_job(self, job_id: int, **values) -> None:
        """Test set-up only: put a job row into a given state (as the owner)."""
        allowed = {"status", "attempts", "locked_by", "run_after", "priority"}
        assert set(values) <= allowed | {"locked_minutes_ago"}
        sets, params = [], {"job_id": job_id}
        for key, value in values.items():
            if key == "locked_minutes_ago":
                sets.append("locked_at = now() - make_interval(mins => :mins)")
                params["mins"] = value
            elif key == "run_after" and value == "now":
                sets.append("run_after = now()")
            else:
                sets.append(f"{key} = :{key}")
                params[key] = value
        self._sql(f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = :job_id", **params)

    def job(self, job_id: int) -> dict:
        rows = self._sql(
            "SELECT job_id, status, attempts, locked_by, last_error, finished_at, "
            "       run_after > now() AS run_after_future, EXTRACT(EPOCH FROM run_after - now())::float AS run_after_in_s "
            "FROM jobs WHERE job_id = :id",
            id=job_id,
        )
        return dict(rows[0])

    def complaint(self, complaint_id: int) -> dict:
        return dict(self._sql("SELECT status, ai_status FROM complaints WHERE complaint_id = :id", id=complaint_id)[0])

    def jobs_of(self, complaint_id: int) -> list[dict]:
        rows = self._sql(
            "SELECT job_id, status FROM jobs WHERE job_type = 'ANALYZE_COMPLAINT' AND ref_id = :cid ORDER BY job_id", cid=complaint_id
        )
        return [dict(r) for r in rows]

    def cleanup(self) -> None:
        if self.complaint_ids:
            self._sql("DELETE FROM jobs WHERE job_type = 'ANALYZE_COMPLAINT' AND ref_id = ANY(:ids)", ids=self.complaint_ids)
            self._sql("DELETE FROM complaints WHERE complaint_id = ANY(:ids)", ids=self.complaint_ids)  # history/outbox cascade
        if self.user_ids:
            self._sql("DELETE FROM users WHERE user_id = ANY(:ids)", ids=self.user_ids)


@pytest.fixture
def it_data(admin_engine):
    data = ItData(admin_engine)
    yield data
    data.cleanup()
