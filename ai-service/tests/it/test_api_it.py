"""Internal API against the test database: /health and the requeue endpoint (docs/04_API_CONTRACT.md sec. 10)."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.security import make_service_jwt

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    return TestClient(app)


def _auth() -> dict:
    return {"Authorization": f"Bearer {make_service_jwt(get_settings().jwt_key)}"}


def test_health_with_the_real_database(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"
    assert r.json()["status"] == "ok"


def test_requeue_a_dead_job(client, it_data):
    complaint_id, job_id = it_data.new_complaint()

    r = client.post(f"/v1/jobs/{job_id}/requeue", headers=_auth())
    assert r.status_code == 409 and r.json()["code"] == "ALREADY_EXISTS"  # still QUEUED

    it_data.set_job(job_id, status="DEAD", attempts=3)
    r = client.post(f"/v1/jobs/{job_id}/requeue", headers=_auth())
    assert r.status_code == 202
    body = r.json()
    assert body["requeuedFrom"] == job_id and body["status"] == "QUEUED" and body["jobId"] != job_id
    assert [j["status"] for j in it_data.jobs_of(complaint_id)] == ["DEAD", "QUEUED"]
    assert it_data.job(body["jobId"])["attempts"] == 0

    r = client.post(f"/v1/jobs/{job_id}/requeue", headers=_auth())
    assert r.status_code == 409  # one active job per (type, ref)


def test_requeue_unknown_job_is_404(client):
    r = client.post(f"/v1/jobs/{2**63 - 1}/requeue", headers=_auth())
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"
