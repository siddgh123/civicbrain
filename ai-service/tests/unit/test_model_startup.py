"""Start-up model check (docs/06_AI_PIPELINE.md sec. 5, rule 30): with REQUIRE_MODELS=true the worker and the API
refuse to start when a required model file or its SHA-256 is wrong, and say which file; with false they only warn."""

import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import get_settings
from app.errors import ConfigError
from app.main import app
from worker import run as worker_run

AI_DIR = Path(__file__).resolve().parents[2]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def models(tmp_path, monkeypatch):
    """A complete fake model folder (YOLO file, classifier, MiniLM folder) + MANIFEST; tests then break one thing."""
    (tmp_path / "yolov8s_civicbrain.onnx").write_bytes(b"yolo")
    (tmp_path / "text_clf.joblib").write_bytes(b"clf")
    (tmp_path / "all-MiniLM-L6-v2").mkdir()
    (tmp_path / "all-MiniLM-L6-v2" / "config.json").write_bytes(b"{}")
    manifest = {
        "manifest_version": 1,
        "files": [
            {"path": "yolov8s_civicbrain.onnx", "sha256": _sha(b"yolo")},
            {"path": "text_clf.joblib", "sha256": _sha(b"clf")},
            {"path": "all-MiniLM-L6-v2/", "files": [{"path": "config.json", "sha256": _sha(b"{}")}]},
        ],
    }
    (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    monkeypatch.setenv("YOLO_WEIGHTS", str(tmp_path / "yolov8s_civicbrain.onnx"))
    monkeypatch.setenv("TEXT_EMBEDDING_MODEL_DIR", str(tmp_path / "all-MiniLM-L6-v2"))
    monkeypatch.setenv("REQUIRE_MODELS", "true")
    get_settings.cache_clear()
    return tmp_path


@pytest.fixture
def restore_logging():
    """main() / the lifespan install the JSON log handler on the root logger; put pytest's set-up back afterwards."""
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    yield
    root.handlers[:], level = saved
    root.setLevel(level)


def test_worker_refuses_to_start_when_a_hash_is_wrong(models, monkeypatch, capsys, restore_logging):
    (models / "yolov8s_civicbrain.onnx").write_bytes(b"other weights")
    monkeypatch.setattr(worker_run, "Worker", lambda *a, **k: pytest.fail("the worker must not start"))
    assert worker_run.main() == 2
    out = capsys.readouterr().out
    assert "worker not started - required model files missing or changed" in out
    assert "yolov8s_civicbrain.onnx: SHA-256 differs from MANIFEST.json" in out


def test_worker_refuses_to_start_when_a_file_is_missing(models, monkeypatch, capsys, restore_logging):
    os.replace(models / "text_clf.joblib", models / "text_clf.joblib.moved")
    monkeypatch.setattr(worker_run, "Worker", lambda *a, **k: pytest.fail("the worker must not start"))
    assert worker_run.main() == 2
    assert "text_clf.joblib: file missing" in capsys.readouterr().out


def test_worker_starts_when_every_model_matches(models, monkeypatch, restore_logging):
    started = []

    class FakeWorker:
        def __init__(self, settings):
            self.stop_event = None

        def run(self):
            started.append(1)

    monkeypatch.setattr(worker_run, "Worker", FakeWorker)
    monkeypatch.setattr(worker_run, "install_signal_handlers", lambda w: None)
    assert worker_run.main() == 0
    assert started == [1]


def test_worker_only_warns_when_models_are_not_required(models, monkeypatch, capsys, restore_logging):
    monkeypatch.setenv("REQUIRE_MODELS", "false")
    get_settings.cache_clear()
    (models / "MANIFEST.json").write_text(json.dumps({"manifest_version": 1, "files": []}), encoding="utf-8")
    monkeypatch.setattr(worker_run, "Worker", lambda settings: type("W", (), {"run": lambda self: None, "stop_event": None})())
    monkeypatch.setattr(worker_run, "install_signal_handlers", lambda w: None)
    assert worker_run.main() == 0
    assert "REQUIRE_MODELS=false so the worker still runs" in capsys.readouterr().out


def test_api_refuses_to_start_when_a_hash_is_wrong(models, restore_logging):
    (models / "text_clf.joblib").write_bytes(b"changed")
    with pytest.raises(ConfigError, match="text_clf.joblib: SHA-256 differs from MANIFEST.json"), TestClient(app):
        pass


def test_api_health_reports_models_loaded_when_every_model_matches(models, monkeypatch, restore_logging):
    monkeypatch.setattr(db, "db_status", lambda: "ok")
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["modelsLoaded"] is True
    assert body["models"] == {"yolov8s_civicbrain.onnx": "ok", "text_clf.joblib": "ok", "all-MiniLM-L6-v2/": "ok"}


def test_api_health_lists_each_model_when_one_is_missing(models, monkeypatch, restore_logging):
    """The P08 state: YOLO + classifier installed, MiniLM arrives in P09 (REQUIRE_MODELS stays false until P12)."""
    monkeypatch.setenv("REQUIRE_MODELS", "false")
    get_settings.cache_clear()
    (models / "all-MiniLM-L6-v2" / "config.json").write_bytes(b"changed")
    (models / "text_clf.joblib").write_bytes(b"changed too")
    monkeypatch.setattr(db, "db_status", lambda: "ok")
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body["modelsLoaded"] is False
    assert body["models"] == {
        "yolov8s_civicbrain.onnx": "ok",
        "text_clf.joblib": "SHA-256 differs from MANIFEST.json",
        "all-MiniLM-L6-v2/": "config.json: SHA-256 differs from MANIFEST.json",
    }


def test_model_status_without_a_manifest_says_not_verified(tmp_path, monkeypatch):
    from app.models_check import check_models, model_status

    (tmp_path / "yolov8s_civicbrain.onnx").write_bytes(b"yolo")
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    monkeypatch.setenv("YOLO_WEIGHTS", str(tmp_path / "yolov8s_civicbrain.onnx"))
    monkeypatch.setenv("TEXT_EMBEDDING_MODEL_DIR", str(tmp_path / "all-MiniLM-L6-v2"))
    get_settings.cache_clear()
    settings = get_settings()
    assert model_status(settings, check_models(settings)) == {
        "yolov8s_civicbrain.onnx": "not verified (MANIFEST.json: not found in MODELS_DIR)",
        "text_clf.joblib": "file missing",
        "all-MiniLM-L6-v2/": "folder missing",
    }


def test_pipeline_modules_import_no_model_library_and_no_settings():
    """Ultralytics/torch/sklearn load lazily on first use; nothing is created at import time."""
    code = (
        "import sys, pipeline.classify, pipeline.detect, pipeline.authenticity\n"
        "from app.config import get_settings\n"
        "assert get_settings.cache_info().currsize == 0, 'settings created at import time'\n"
        "heavy = [m for m in ('ultralytics', 'torch', 'sklearn', 'onnxruntime') if m in sys.modules]\n"
        "assert not heavy, heavy\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "DB_AI_PASSWORD"}
    result = subprocess.run([sys.executable, "-c", code], cwd=AI_DIR, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
