"""Internal API without a database: /health shape, service JWT on /v1, Problem Details (docs/04 sec. 10)."""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.main import app
from app.security import make_service_jwt


@pytest.fixture
def client():
    return TestClient(app)  # no `with`: the lifespan (model check, logging set-up) is not needed here


def _auth(**claims) -> dict:
    return {"Authorization": f"Bearer {make_service_jwt(get_settings().jwt_key, **claims)}"}


def test_health_reports_db_ok(client, monkeypatch):
    monkeypatch.setattr(db, "db_status", lambda: "ok")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok", "osrm": "not used (haversine)", "modelsLoaded": False}
    assert r.headers["X-Request-Id"]


@pytest.mark.parametrize("state", ["unavailable", "schema missing"])
def test_health_reports_db_problems_as_503(client, monkeypatch, state):
    monkeypatch.setattr(db, "db_status", lambda: state)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["db"] == state
    assert r.json()["status"] == "degraded"


def test_request_id_is_echoed_when_well_formed(client, monkeypatch):
    monkeypatch.setattr(db, "db_status", lambda: "ok")
    assert client.get("/health", headers={"X-Request-Id": "abc-123"}).headers["X-Request-Id"] == "abc-123"
    generated = client.get("/health", headers={"X-Request-Id": "bad id <script>"}).headers["X-Request-Id"]
    assert generated != "bad id <script>" and len(generated) == 32


@pytest.mark.parametrize("path,method", [("/v1/models", "get"), ("/v1/jobs/1/requeue", "post")])
def test_v1_needs_a_service_token(client, path, method):
    r = getattr(client, method)(path)
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "UNAUTHENTICATED" and body["status"] == 401 and body["requestId"]
    assert r.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("claims", [{"aud": "civicbrain-web"}, {"iss": "civicbrain"}], ids=["wrong-aud", "wrong-iss"])
def test_v1_rejects_wrong_claims(client, claims):
    assert client.get("/v1/models", headers=_auth(**claims)).status_code == 401


def test_v1_rejects_a_token_signed_with_another_key(client):
    token = make_service_jwt(b"z" * 32)
    assert client.get("/v1/models", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_models_with_a_valid_token(client):
    r = client.get("/v1/models", headers=_auth())
    assert r.status_code == 200
    assert set(r.json()) == {"yolo", "classifier", "embedding"}
    assert r.json()["yolo"]["file"] == "yolov8s_civicbrain.onnx"


def test_requeue_validates_the_job_id(client):
    r = client.post("/v1/jobs/0/requeue", headers=_auth())
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_FAILED"


def test_unknown_path_is_a_problem_404(client):
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_no_api_docs_are_published(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
