"""pipeline/detect.py: YOLO on the ONNX file (docs/06_AI_PIPELINE.md sec. 2.3, 09_7DAY sec. 4 "YOLO smoke").

The `models` tests need ai-service/models/yolov8s_civicbrain.onnx (+ MANIFEST.json); they skip only when the file is
absent (CI). The fixtures are TEST-split images (tests/fixtures/images/README.md) - a smoke test, the real numbers
are docs/reports/yolo_metrics.json.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.config import YOLO_CLASSES, get_settings
from app.errors import ConfigError, DataError
from pipeline import detect
from pipeline.detect import Detection, Detector, image_classification, load_rgb, primary_detection, to_detections

AI_DIR = Path(__file__).resolve().parents[2]
FIXTURES = AI_DIR.parent / "tests" / "fixtures" / "images"


def _det(class_id: int, conf: float, x: float = 10, y: float = 10) -> Detection:
    return Detection(class_id=class_id, class_name=YOLO_CLASSES[class_id], confidence=conf, x=x, y=y, width=20, height=10)


def test_to_detections_converts_xyxy_to_pixel_boxes_clamped_and_sorted():
    xyxy = np.array([[-3.0, 5.0, 50.4, 40.0], [100.0, 100.0, 130.0, 900.0], [5.0, 5.0, 5.0, 9.0]])
    dets = to_detections(xyxy, np.array([0.31, 0.876543, 0.9]), np.array([3.0, 0.0, 1.0]), width=200, height=150)
    # third box has zero width -> dropped; second is clamped to the image; sorted by confidence
    assert dets == [
        Detection(class_id=0, class_name="Pothole", confidence=0.8765, x=100.0, y=100.0, width=30.0, height=50.0),
        Detection(class_id=3, class_name="Road Damage", confidence=0.31, x=0.0, y=5.0, width=50.4, height=35.0),
    ]


def test_primary_detection_is_the_most_confident_box_of_the_category_class():
    dets = [_det(1, 0.9), _det(0, 0.4), _det(0, 0.7, x=50), _det(0, 0.3)]
    assert primary_detection(dets, 0) == _det(0, 0.7, x=50)
    assert primary_detection(dets, 2) is None
    assert primary_detection(dets, None) is None


def test_image_classification_summarises_per_class():
    summary = image_classification([_det(0, 0.45), _det(1, 0.8), _det(0, 0.3)], category_class_id=0)
    assert summary.predicted_class_id == 1 and summary.confidence == 0.8
    assert summary.top_k == [
        {"category": "Garbage Accumulation", "classId": 1, "p": 0.8},
        {"category": "Pothole", "classId": 0, "p": 0.45},
    ]
    assert summary.is_accepted is True  # own class >= 0.4
    assert image_classification([_det(1, 0.8)], 0).is_accepted is False  # only another class >= 0.5
    assert image_classification([_det(1, 0.45)], 0).is_accepted is None  # no evidence either way
    assert image_classification([_det(1, 0.8)], None).is_accepted is None  # category without a YOLO class
    assert image_classification([], 0) is None


def test_wrong_checksum_is_refused_before_loading(tmp_path):
    weights = tmp_path / "yolov8s_civicbrain.onnx"
    weights.write_bytes(b"not a model")
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"manifest_version": 1, "files": [{"path": weights.name, "sha256": "0" * 64}]}))
    with pytest.raises(ConfigError, match="yolov8s_civicbrain.onnx: SHA-256 differs from MANIFEST.json"):
        Detector.load(weights, "0" * 64)


def test_ultralytics_keeps_its_settings_in_yolo_config_dir(tmp_path):
    """Regression (P08): with a not-yet-existing YOLO_CONFIG_DIR Ultralytics fell back to \\tmp on the drive root."""
    config_dir = tmp_path / "new" / ".ultralytics"
    code = (
        "from pipeline import detect\n"
        "detect._ultralytics_env()\n"
        "from ultralytics.utils import USER_CONFIG_DIR\n"
        "print(USER_CONFIG_DIR)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "DB_AI_PASSWORD"} | {"YOLO_CONFIG_DIR": str(config_dir)}
    result = subprocess.run([sys.executable, "-c", code], cwd=AI_DIR, env=env, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-2000:]
    assert Path(result.stdout.strip().splitlines()[-1]).resolve().is_relative_to(config_dir.resolve())


def test_unreadable_image_is_a_data_error():
    with pytest.raises(DataError, match="cannot be read"):
        load_rgb(FIXTURES / "not_an_image.jpg")


def test_unreadable_image_is_still_a_data_error_after_ultralytics_patched_pil():
    """Regression (found in the V6 run): importing Ultralytics replaces PIL.Image.open with a wrapper that tries the
    optional pi-heif plugin when a file cannot be identified; the plugin is not pinned and auto-install is off, so the
    wrapper raised ModuleNotFoundError - in the worker (detector loaded) a corrupt photo was not a DataError."""
    code = (
        "from pathlib import Path\n"
        "from pipeline import detect\n"
        "from app.errors import DataError\n"
        "detect._ultralytics_env()\n"
        "import ultralytics.utils.patches  # applies the PIL patch, as loading the detector does\n"
        f"path = Path(r'{FIXTURES / 'not_an_image.jpg'}')\n"
        "try:\n"
        "    detect.load_rgb(path)\n"
        "except DataError as exc:\n"
        "    print('DATAERROR', exc)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "DB_AI_PASSWORD"}
    result = subprocess.run([sys.executable, "-c", code], cwd=AI_DIR, env=env, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "DATAERROR image cannot be read" in result.stdout


# ------------------------------------------------------------------ models (the installed ONNX file)
@pytest.fixture(scope="module")
def detector():
    settings = get_settings()
    if not settings.yolo_weights.is_file():
        pytest.skip("yolov8s_civicbrain.onnx not installed (CI)")
    detect.clear_cache()
    yield detect.get_detector(settings)
    detect.clear_cache()


@pytest.mark.models
def test_model_version_is_the_file_hash_prefix_and_classes_are_frozen(detector):
    digest = hashlib.sha256(get_settings().yolo_weights.read_bytes()).hexdigest()
    assert detector.version == digest[:12]
    assert detector.class_names == list(YOLO_CLASSES)
    assert detect.get_detector(get_settings()) is detector  # loaded once


@pytest.mark.models
def test_pothole_fixture_gives_a_pothole_box(detector):
    result = detector.detect(FIXTURES / "pothole_1.jpg")
    potholes = [d for d in result.detections if d.class_name == "Pothole"]
    assert potholes and max(d.confidence for d in potholes) >= 0.25
    assert (result.width_px, result.height_px) == (720, 720)
    assert result.model_version == detector.version and result.model_name == "yolov8s_civicbrain"


@pytest.mark.models
@pytest.mark.parametrize("name", ["pothole_1.jpg", "garbage_1.jpg", "waterlogging_1.jpg", "road_damage_1.jpg"])
def test_every_fixture_runs(detector, name):
    result = detector.detect(FIXTURES / name)
    assert result.elapsed_ms > 0
    for d in result.detections:
        assert d.class_name in YOLO_CLASSES and 0.25 <= d.confidence <= 1
        assert 0 <= d.x and 0 <= d.y and d.width > 0 and d.height > 0
        assert d.x + d.width <= result.width_px + 0.01 and d.y + d.height <= result.height_px + 0.01


@pytest.mark.models
def test_same_image_gives_the_same_boxes(detector):
    a = detector.detect(FIXTURES / "road_damage_1.jpg").detections
    b = detector.detect(Image.open(FIXTURES / "road_damage_1.jpg")).detections
    assert a == b
