"""Settings: created lazily, clear message for a missing or bad key, secrets never in messages (rule 30)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import config
from app.config import Settings, get_settings
from app.errors import ConfigError

AI_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture
def no_env_file(monkeypatch):
    """Ignore the repo-root .env, so only the environment of the test counts."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)


def test_settings_are_not_created_at_import_time():
    """Import every module in a fresh interpreter: no Settings object may exist afterwards."""
    code = (
        "import app.db, app.models_check, app.security, app.main, worker.jobs, worker.handlers, worker.run\n"
        "from app.config import get_settings\n"
        "assert get_settings.cache_info().currsize == 0, 'settings created at import time'\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "DB_AI_PASSWORD"}
    result = subprocess.run([sys.executable, "-c", code], cwd=AI_DIR, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]


def test_missing_key_gives_clear_config_error(no_env_file, monkeypatch):
    monkeypatch.delenv("DB_AI_PASSWORD", raising=False)
    with pytest.raises(ConfigError) as err:
        get_settings()
    message = str(err.value)
    assert "DB_AI_PASSWORD" in message
    assert "Field required" in message
    assert message.startswith("Invalid or missing settings")


def test_bad_secret_is_named_but_never_shown(no_env_file, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_JWT_SECRET", "not-base64-SUPERSECRET!!")
    with pytest.raises(ConfigError) as err:
        get_settings()
    message = str(err.value)
    assert "AI_SERVICE_JWT_SECRET" in message
    assert "SUPERSECRET" not in message
    assert err.value.__cause__ is None  # the pydantic error (with the input value) is not chained


def test_short_secret_is_rejected(no_env_file, monkeypatch):
    monkeypatch.setenv("AI_SERVICE_JWT_SECRET", "c2hvcnQ=")  # base64 of "short"
    with pytest.raises(ConfigError, match="AI_SERVICE_JWT_SECRET"):
        get_settings()


def test_ai_api_must_bind_localhost(monkeypatch):
    monkeypatch.setenv("AI_API_HOST", "0.0.0.0")
    with pytest.raises(ConfigError, match="AI_API_HOST"):
        get_settings()


def test_settings_load_from_environment_and_are_cached():
    s = get_settings()
    assert s is get_settings()
    assert s.worker_id == "pytest-worker"
    assert s.db_name  # DB_NAME = DB_TEST_NAME (conftest)
    assert s.routing_mode == "haversine"
    assert s.require_models is False
    assert s.labour_rate_per_hour is None
    assert len(s.jwt_key) >= 32
    assert "dGVzdC1v" not in repr(s)  # SecretStr hides the key


def test_empty_value_means_not_set(monkeypatch):
    monkeypatch.setenv("LABOUR_RATE_PER_HOUR", "")
    assert get_settings().labour_rate_per_hour is None


def test_values_are_normalised(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("ROUTING_MODE", "OSRM")
    s = get_settings()
    assert (s.log_level, s.routing_mode) == ("DEBUG", "osrm")


def test_frozen_yolo_classes_in_order():
    assert config.YOLO_CLASSES == ("Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage")


def test_job_timeouts_match_the_pipeline_doc():
    assert config.JOB_TIMEOUT_SECONDS["ANALYZE_COMPLAINT"] == 120
    assert config.JOB_TIMEOUT_SECONDS["OPTIMIZE_PLAN"] == 60
    assert config.JOB_TIMEOUT_SECONDS["BLUR_IMAGE"] == 60
    assert set(config.JOB_TIMEOUT_SECONDS) == set(config.WORKER_JOB_TYPES)
