"""MANIFEST.json checker: missing file, wrong hash, folder entries (docs/06_AI_PIPELINE.md sec. 5)."""

import hashlib
import json
from pathlib import Path

from app.config import Settings
from app.models_check import check_manifest, check_models, describe_models, required_files, sha256_file


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _manifest(models: Path, files: list[dict]) -> None:
    (models / "MANIFEST.json").write_text(json.dumps({"manifest_version": 1, "files": files}), encoding="utf-8")


def test_sha256_file(tmp_path):
    digest = _write(tmp_path / "a.bin", b"abc")
    assert sha256_file(tmp_path / "a.bin") == digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_no_manifest_and_no_files(tmp_path):
    problems = check_manifest(tmp_path, [("y.onnx", tmp_path / "y.onnx")])
    assert problems == ["MANIFEST.json: not found in MODELS_DIR", "y.onnx: file missing"]


def test_file_with_matching_hash_is_ok(tmp_path):
    digest = _write(tmp_path / "y.onnx", b"weights")
    _manifest(tmp_path, [{"path": "y.onnx", "sha256": digest.upper()}])  # hex case does not matter
    assert check_manifest(tmp_path, [("y.onnx", tmp_path / "y.onnx")]) == []


def test_wrong_hash_is_reported(tmp_path):
    _write(tmp_path / "y.onnx", b"weights")
    _manifest(tmp_path, [{"path": "y.onnx", "sha256": "0" * 64}])
    assert check_manifest(tmp_path, [("y.onnx", tmp_path / "y.onnx")]) == ["y.onnx: SHA-256 differs from MANIFEST.json"]


def test_listed_but_missing_file_is_reported(tmp_path):
    _manifest(tmp_path, [{"path": "y.onnx", "sha256": "0" * 64}])
    assert check_manifest(tmp_path, [("y.onnx", tmp_path / "y.onnx")]) == ["y.onnx: file missing"]


def test_present_but_unlisted_file_is_reported(tmp_path):
    _write(tmp_path / "y.onnx", b"weights")
    _manifest(tmp_path, [])
    assert check_manifest(tmp_path, [("y.onnx", tmp_path / "y.onnx")]) == ["y.onnx: not listed in MANIFEST.json"]


def test_folder_entry_checks_every_file(tmp_path):
    folder = tmp_path / "mini"
    d1 = _write(folder / "config.json", b"{}")
    _write(folder / "model.safetensors", b"tensor")
    files = [{"path": "config.json", "sha256": d1}, {"path": "model.safetensors", "sha256": "1" * 64}]
    _manifest(tmp_path, [{"path": "mini/", "files": files}])
    assert check_manifest(tmp_path, [("mini/", folder)]) == ["mini/model.safetensors: SHA-256 differs from MANIFEST.json"]


def test_folder_entry_rejects_path_escape(tmp_path):
    folder = tmp_path / "mini"
    folder.mkdir()
    _manifest(tmp_path, [{"path": "mini/", "files": [{"path": "../secret.txt", "sha256": "1" * 64}]}])
    assert check_manifest(tmp_path, [("mini/", folder)]) == ["mini/: manifest lists an invalid path"]


def test_missing_folder_is_reported(tmp_path):
    _manifest(tmp_path, [])
    assert check_manifest(tmp_path, [("mini/", tmp_path / "mini")]) == ["mini/: folder missing"]


def test_broken_manifest_is_one_problem(tmp_path):
    (tmp_path / "MANIFEST.json").write_text("{ not json", encoding="utf-8")
    assert check_manifest(tmp_path, [("y.onnx", tmp_path / "y.onnx")]) == ["MANIFEST.json: cannot be read (JSONDecodeError)"]


def _settings(models: Path, blur: bool = False) -> Settings:
    return Settings.model_construct(
        models_dir=models,
        yolo_weights=models / "yolov8s_civicbrain.onnx",
        text_embedding_model_dir=models / "all-MiniLM-L6-v2",
        blur_enabled=blur,
    )


def test_required_files_follow_the_settings(tmp_path):
    names = [name for name, _ in required_files(_settings(tmp_path))]
    assert names == ["yolov8s_civicbrain.onnx", "text_clf.joblib", "all-MiniLM-L6-v2/"]
    assert [n for n, _ in required_files(_settings(tmp_path, blur=True))][-1] == "face_detection_yunet_2023mar.onnx"


CLASSES = ["Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage"]
MINILM = "sentence-transformers/all-MiniLM-L6-v2"


def test_all_models_present_gives_no_problems(tmp_path):
    y = _write(tmp_path / "yolov8s_civicbrain.onnx", b"yolo")
    c = _write(tmp_path / "text_clf.joblib", b"clf")
    m = _write(tmp_path / "all-MiniLM-L6-v2" / "config.json", b"{}")
    _manifest(
        tmp_path,
        [
            {"path": "yolov8s_civicbrain.onnx", "sha256": y, "classes": CLASSES},
            {"path": "text_clf.joblib", "sha256": c},
            {"path": "all-MiniLM-L6-v2/", "repo": MINILM, "files": [{"path": "config.json", "sha256": m}]},
        ],
    )
    settings = _settings(tmp_path)
    assert check_models(settings) == []
    info = describe_models(settings)
    assert info["yolo"] == {"file": "yolov8s_civicbrain.onnx", "sha256": y, "classes": CLASSES}
    assert info["classifier"] == {"version": c[:12]}
    assert info["embedding"] == {"name": MINILM}


def test_describe_models_without_manifest_has_nulls(tmp_path):
    info = describe_models(_settings(tmp_path))
    assert info == {
        "yolo": {"file": "yolov8s_civicbrain.onnx", "sha256": None, "classes": None},
        "classifier": {"version": None},
        "embedding": {"name": None},
    }
