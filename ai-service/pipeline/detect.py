"""YOLO detection - ANALYZE_COMPLAINT step 4 (docs/06_AI_PIPELINE.md sec. 2.3, FR-22).

Model `models/yolov8s_civicbrain.onnx` (FROZEN classes 0 Pothole, 1 Garbage Accumulation, 2 Waterlogging,
3 Road Damage), loaded once per process with Ultralytics `YOLO(path, task='detect')` after its SHA-256 matches
models/MANIFEST.json; inference `imgsz=640, conf=0.25, iou=0.5, device='cpu'`. All boxes are stored in pixels of the
(EXIF-upright) image, `model_version` = file SHA-256[:12]. Primary detection = the most confident box of the
category's `yolo_class_id`. The orchestrator (P12) runs this step only for categories with a YOLO class.
Ultralytics is imported lazily (never at import time) and never installs packages or writes outside ai-service/.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import YOLO_CLASSES, YOLO_CONF, YOLO_DEVICE, YOLO_IMGSZ, YOLO_IOU, YOLO_MODEL_NAME, Settings
from app.errors import DataError, ModelError
from app.models_check import expected_sha256, verify_file
from pipeline.authenticity import category_image_evidence

AI_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    x: float  # top-left corner, pixels
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class DetectionResult:
    detections: list[Detection]
    width_px: int
    height_px: int
    elapsed_ms: float  # CPU inference time incl. pre/post-processing
    model_name: str
    model_version: str


@dataclass(frozen=True)
class ImageSummary:
    """The image-level ai_classifications row (model_type IMAGE)."""

    predicted_class_id: int
    confidence: float
    top_k: list[dict]
    is_accepted: bool | None


def _ultralytics_env() -> None:
    """Offline, no auto-install, settings inside ai-service/ (the worker's .env sets the same values).

    The folder must exist before Ultralytics is imported: if it does not, Ultralytics silently falls back to
    /tmp (on Windows the drive root, e.g. C:\\tmp\\Ultralytics) - outside the workspace.
    """
    os.environ.setdefault("YOLO_OFFLINE", "true")
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    os.environ.setdefault("YOLO_CONFIG_DIR", str(AI_DIR / ".ultralytics"))
    Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)


def load_rgb(image: Path | Image.Image) -> Image.Image:
    """The image as upright RGB (EXIF orientation applied). DataError when it cannot be decoded."""
    try:
        if isinstance(image, Path):
            with Image.open(image) as img:
                img.load()
                return ImageOps.exif_transpose(img).convert("RGB")
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise DataError(f"image cannot be read ({type(exc).__name__})") from None


def to_detections(xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray, width: int, height: int) -> list[Detection]:
    """Ultralytics xyxy boxes -> pixel boxes (x, y, w, h) clamped to the image; empty boxes dropped; sorted."""
    out = []
    for (x1, y1, x2, y2), c, k in zip(xyxy.tolist(), conf.tolist(), cls.tolist(), strict=True):
        x1, x2 = max(0.0, min(float(x1), width)), max(0.0, min(float(x2), width))
        y1, y2 = max(0.0, min(float(y1), height)), max(0.0, min(float(y2), height))
        w, h = round(x2 - x1, 2), round(y2 - y1, 2)
        if w <= 0 or h <= 0:
            continue
        cid = int(k)
        out.append(Detection(cid, YOLO_CLASSES[cid], round(float(c), 4), round(x1, 2), round(y1, 2), w, h))
    out.sort(key=lambda d: (-d.confidence, d.class_id, d.x, d.y))
    return out


def primary_detection(detections: Sequence[Detection], category_class_id: int | None) -> Detection | None:
    own = [d for d in detections if category_class_id is not None and d.class_id == category_class_id]
    return max(own, key=lambda d: d.confidence) if own else None  # list is sorted: first of the maxima wins


def image_classification(detections: Sequence[Detection], category_class_id: int | None) -> ImageSummary | None:
    """Per class the best confidence; predicted = the best overall. None when nothing was detected.

    is_accepted follows CATEGORY_IMAGE_MISMATCH (06 sec. 2.1): True when the category's own class is found with
    conf >= 0.4, False when only other classes reach >= 0.5, otherwise None (no evidence either way).
    """
    if not detections:
        return None
    best: dict[int, float] = {}
    for d in detections:
        best[d.class_id] = max(best.get(d.class_id, 0.0), d.confidence)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))
    evidence = category_image_evidence(best.items(), category_class_id)
    return ImageSummary(
        predicted_class_id=ranked[0][0],
        confidence=ranked[0][1],
        top_k=[{"category": YOLO_CLASSES[k], "classId": k, "p": p} for k, p in ranked],
        is_accepted={"MATCH": True, "OTHER_CLASS": False}.get(evidence),
    )


class Detector:
    def __init__(self, model: object, sha256: str) -> None:
        self._model = model
        self.sha256 = sha256
        self.name = YOLO_MODEL_NAME
        self.version = sha256[:12]
        self._lock = threading.Lock()  # the Ultralytics predictor is not thread-safe (a timed-out job may still run)

    @classmethod
    def load(cls, weights: Path, expected: str) -> Detector:
        digest = verify_file(weights, expected, weights.name)
        _ultralytics_env()
        try:
            from ultralytics import YOLO

            logging.getLogger("ultralytics").setLevel(logging.WARNING)  # its info lines are not JSON log lines
            detector = cls(YOLO(str(weights), task="detect"), digest)
            # warm-up on a blank image: builds the predictor (the ONNX session is created once, here) so the first
            # job is not slower; the class names are read from that predictor afterwards
            detector.detect(Image.new("RGB", (YOLO_IMGSZ, YOLO_IMGSZ)))
            found = detector.class_names
        except Exception as exc:  # any loader problem is a model problem
            raise ModelError(f"{weights.name}: cannot be loaded ({type(exc).__name__})") from exc
        if found != list(YOLO_CLASSES):
            raise ModelError(f"{weights.name}: classes {found} differ from the FROZEN list {list(YOLO_CLASSES)}")
        return detector

    @property
    def class_names(self) -> list[str]:
        names = self._model.names  # type: ignore[attr-defined]
        return [names[i] for i in sorted(names)]

    def detect(self, image: Path | Image.Image) -> DetectionResult:
        img = load_rgb(image)
        width, height = img.size
        started = time.perf_counter()
        with self._lock:
            result = self._model.predict(  # type: ignore[attr-defined]
                img, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, iou=YOLO_IOU, device=YOLO_DEVICE, verbose=False
            )[0]
        elapsed_ms = (time.perf_counter() - started) * 1000
        boxes = result.boxes
        detections = to_detections(boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy(), boxes.cls.cpu().numpy(), width, height)
        return DetectionResult(detections, width, height, round(elapsed_ms, 1), self.name, self.version)


_cache: dict[tuple[str, str], Detector] = {}
_cache_lock = threading.Lock()


def get_detector(settings: Settings) -> Detector:
    """The process-wide detector (loaded on first use; a new MANIFEST hash loads the new file)."""
    weights = settings.yolo_weights
    expected = expected_sha256(settings.models_dir, weights.name)
    key = (str(weights), expected)
    with _cache_lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = Detector.load(weights, expected)
        return _cache[key]


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------------------------------------------
# Database (role civicbrain_ai; the caller owns the transaction)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class StoredDetections:
    detection_ids: list[int]  # same order as result.detections
    primary: Detection | None
    primary_detection_id: int | None
    summary: ImageSummary | None


DELETE_BOXES_SQL = text("DELETE FROM yolo_detections WHERE image_id = :image_id AND model_name = :name AND model_version = :version")
INSERT_BOX_SQL = text(
    """
    INSERT INTO yolo_detections (image_id, detected_class, confidence, bbox_x, bbox_y, bbox_width, bbox_height, model_name, model_version)
    VALUES (:image_id, :cls, :conf, :x, :y, :w, :h, :name, :version)
    RETURNING detection_id
    """
)
DELETE_IMAGE_ROW_SQL = text(
    "DELETE FROM ai_classifications WHERE complaint_id = :cid AND model_type = 'IMAGE' AND model_name = :name AND model_version = :version"
)
INSERT_IMAGE_ROW_SQL = text(
    """
    INSERT INTO ai_classifications (complaint_id, model_type, predicted_category, predicted_category_id, confidence,
                                    model_name, model_version, top_k, is_accepted)
    VALUES (:cid, 'IMAGE', :category,
            (SELECT category_id FROM complaint_categories WHERE yolo_class_id = :class_id ORDER BY category_id LIMIT 1),
            :conf, :name, :version, CAST(:top_k AS jsonb), :accepted)
    """
)


def write_detections(
    session: Session, complaint_id: int, image_id: int, result: DetectionResult, category_class_id: int | None
) -> StoredDetections:
    """Delete-then-insert this model version's boxes of the image and the complaint's IMAGE classification row."""
    version = {"name": result.model_name, "version": result.model_version}
    session.execute(DELETE_BOXES_SQL, {"image_id": image_id, **version})
    ids = [
        session.execute(
            INSERT_BOX_SQL,
            {"image_id": image_id, "cls": d.class_name, "conf": d.confidence, "x": d.x, "y": d.y, "w": d.width, "h": d.height, **version},
        ).scalar_one()
        for d in result.detections
    ]
    session.execute(DELETE_IMAGE_ROW_SQL, {"cid": complaint_id, **version})
    summary = image_classification(result.detections, category_class_id)
    if summary is not None:
        session.execute(
            INSERT_IMAGE_ROW_SQL,
            {
                "cid": complaint_id,
                "category": YOLO_CLASSES[summary.predicted_class_id],
                "class_id": summary.predicted_class_id,
                "conf": summary.confidence,
                "top_k": json.dumps(summary.top_k),
                "accepted": summary.is_accepted,
                **version,
            },
        )
    primary = primary_detection(result.detections, category_class_id)
    primary_id = ids[result.detections.index(primary)] if primary is not None else None
    return StoredDetections(ids, primary, primary_id, summary)
