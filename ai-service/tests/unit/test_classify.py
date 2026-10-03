"""pipeline/classify.py: checksum before load, top-3, mismatch rule (docs/06_AI_PIPELINE.md sec. 2.2, FR-21)."""

import hashlib
import json

import joblib
import pytest

from app.config import TEXT_CLF_FILE, get_settings
from app.errors import ConfigError, DataError
from app.models_check import expected_sha256, sha256_file
from pipeline import classify
from pipeline.classify import TextClassifier, complaint_text, is_accepted
from training.train_text_clf import build_pipeline


def _tiny_model(models_dir, manifest_sha: str | None = None) -> str:
    """A small classifier trained in the test + its MANIFEST entry (the real one is in the models test below)."""
    texts = ["pothole in road", "deep pothole", "garbage heap", "garbage not collected", "street light off", "light pole dark"]
    labels = ["Pothole", "Pothole", "Garbage Accumulation", "Garbage Accumulation", "Streetlight", "Streetlight"]
    path = models_dir / TEXT_CLF_FILE
    joblib.dump(build_pipeline(5.0).fit(texts, labels), path)
    digest = sha256_file(path)
    manifest = {"manifest_version": 1, "files": [{"path": TEXT_CLF_FILE, "sha256": manifest_sha or digest}]}
    (models_dir / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return digest


def test_complaint_text_is_title_dot_description():
    assert complaint_text(" Pothole near school ", " Big hole. ") == "Pothole near school. Big hole."


@pytest.mark.parametrize(
    "top,citizen,expected",
    [
        ([("Pothole", 0.95), ("Road Damage", 0.03)], "Pothole", True),  # agrees
        ([("Garbage Accumulation", 0.70), ("Pothole", 0.2)], "Pothole", False),  # disagrees with p = 0.70 -> badge
        ([("Garbage Accumulation", 0.91), ("Pothole", 0.05)], "Pothole", False),
        ([("Garbage Accumulation", 0.69), ("Pothole", 0.3)], "Pothole", True),  # disagrees but p < 0.70 -> no badge
        ([("Pothole", 0.9)], None, None),  # complaint without a category: nothing to compare
    ],
)
def test_mismatch_rule(top, citizen, expected):
    assert is_accepted(top, citizen) is expected


def test_load_and_predict_top3(tmp_path):
    digest = _tiny_model(tmp_path)
    clf = TextClassifier.load(tmp_path / TEXT_CLF_FILE, expected_sha256(tmp_path, TEXT_CLF_FILE))
    assert clf.version == digest[:12]
    top = clf.predict("there is a deep pothole")
    assert len(top) == 3
    assert top[0][0] == "Pothole"
    assert [p for _, p in top] == sorted((p for _, p in top), reverse=True)
    assert all(0 <= p <= 1 for _, p in top)


def test_wrong_checksum_is_refused_before_unpickling(tmp_path, monkeypatch):
    _tiny_model(tmp_path, manifest_sha="0" * 64)
    monkeypatch.setattr(joblib, "load", lambda *a, **k: pytest.fail("joblib.load must not run on an unverified file"))
    with pytest.raises(ConfigError, match="text_clf.joblib: SHA-256 differs from MANIFEST.json"):
        TextClassifier.load(tmp_path / TEXT_CLF_FILE, expected_sha256(tmp_path, TEXT_CLF_FILE))


def test_missing_model_is_a_config_error(tmp_path):
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"manifest_version": 1, "files": []}), encoding="utf-8")
    with pytest.raises(ConfigError, match="text_clf.joblib: not listed in MANIFEST.json"):
        expected_sha256(tmp_path, TEXT_CLF_FILE)
    with pytest.raises(ConfigError, match="text_clf.joblib: file missing"):
        TextClassifier.load(tmp_path / TEXT_CLF_FILE, "0" * 64)


def test_empty_text_is_a_data_error(tmp_path):
    _tiny_model(tmp_path)
    clf = TextClassifier.load(tmp_path / TEXT_CLF_FILE, expected_sha256(tmp_path, TEXT_CLF_FILE))
    with pytest.raises(DataError):
        clf.predict("   ")


def test_get_classifier_loads_once(tmp_path, monkeypatch):
    _tiny_model(tmp_path)
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    get_settings.cache_clear()
    classify.clear_cache()
    calls = []
    real_load = joblib.load
    monkeypatch.setattr(joblib, "load", lambda *a, **k: calls.append(1) or real_load(*a, **k))
    first = classify.get_classifier(get_settings())
    assert classify.get_classifier(get_settings()) is first
    assert len(calls) == 1
    classify.clear_cache()


@pytest.mark.models
def test_installed_classifier_predicts_with_the_manifest_version():
    settings = get_settings()
    path = settings.models_dir / TEXT_CLF_FILE
    if not path.is_file():
        pytest.skip("text_clf.joblib not installed (CI)")
    classify.clear_cache()
    clf = classify.get_classifier(settings)
    assert clf.version == hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    assert clf.predict("Big pothole in the middle of the road near the bus stand")[0][0] == "Pothole"
    assert clf.predict("Garbage has not been collected for a week, a big heap of waste near the market")[0][0] == "Garbage Accumulation"
    assert len(clf.labels) == 8
    classify.clear_cache()
