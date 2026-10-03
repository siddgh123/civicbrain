"""Complaint-text classification - ANALYZE_COMPLAINT step 3 (docs/06_AI_PIPELINE.md sec. 2.2, FR-21).

The model (training/train_text_clf.py, TF-IDF + logistic regression over the 8 categories) is loaded once per
process, and only after its SHA-256 matches models/MANIFEST.json: a joblib file is a pickle, so an unlisted or
changed file is never unpickled. Missing model / checksum -> ConfigError (the job fails as a configuration error).

predict(text) -> top-3 [(category, p)]. Mismatch rule: top-1 != citizen category with p >= 0.70 ->
is_accepted = false (the officer sees a "possible wrong category" badge). The citizen's category is never changed.
Writes one ai_classifications row (model_type TEXT) per complaint and model version (delete-then-insert).
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import TEXT_CLF_FILE, TEXT_CLF_MODEL_NAME, TEXT_MISMATCH_MIN_P, TEXT_TOP_K, Settings
from app.errors import DataError, ModelError
from app.models_check import expected_sha256, verify_file


@dataclass(frozen=True)
class TextResult:
    top: list[tuple[str, float]]
    is_accepted: bool | None
    model_name: str
    model_version: str

    @property
    def predicted(self) -> str:
        return self.top[0][0]

    @property
    def confidence(self) -> float:
        return self.top[0][1]


class TextClassifier:
    def __init__(self, pipeline: object, sha256: str) -> None:
        self._pipeline = pipeline
        self.sha256 = sha256
        self.name = TEXT_CLF_MODEL_NAME
        self.version = sha256[:12]
        self.labels = [str(c) for c in pipeline.classes_]  # type: ignore[attr-defined]
        self._lock = threading.Lock()

    @classmethod
    def load(cls, path: Path, expected: str) -> TextClassifier:
        digest = verify_file(path, expected, TEXT_CLF_FILE)  # before joblib touches the file
        import joblib

        try:
            pipeline = joblib.load(path)
        except Exception as exc:  # any unpickling problem is a model problem
            raise ModelError(f"{TEXT_CLF_FILE}: cannot be loaded ({type(exc).__name__})") from exc
        if not (hasattr(pipeline, "predict_proba") and hasattr(pipeline, "classes_")):
            raise ModelError(f"{TEXT_CLF_FILE}: not a fitted classifier with predict_proba")
        return cls(pipeline, digest)

    def predict(self, complaint: str, k: int = TEXT_TOP_K) -> list[tuple[str, float]]:
        """Top-k (category, probability), highest first; equal probabilities in name order (deterministic)."""
        if not complaint.strip():
            raise DataError("complaint text is empty")
        with self._lock:
            proba = self._pipeline.predict_proba([complaint])[0]  # type: ignore[attr-defined]
        order = sorted(range(len(proba)), key=lambda i: (-float(proba[i]), self.labels[i]))[:k]
        return [(self.labels[i], round(float(proba[i]), 4)) for i in order]


def complaint_text(title: str, description: str) -> str:
    """Same text shape as the training data: title + ". " + description."""
    return f"{title.strip()}. {description.strip()}"


def is_accepted(top: list[tuple[str, float]], citizen_category: str | None) -> bool | None:
    """False when the model confidently disagrees with the citizen's category; None without a category."""
    if citizen_category is None:
        return None
    category, p = top[0]
    return not (category != citizen_category and p >= TEXT_MISMATCH_MIN_P)


_cache: dict[tuple[str, str], TextClassifier] = {}
_cache_lock = threading.Lock()


def get_classifier(settings: Settings) -> TextClassifier:
    """The process-wide classifier (loaded on first use; a new MANIFEST hash loads the new file)."""
    expected = expected_sha256(settings.models_dir, TEXT_CLF_FILE)
    key = (str(settings.models_dir / TEXT_CLF_FILE), expected)
    with _cache_lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = TextClassifier.load(settings.models_dir / TEXT_CLF_FILE, expected)
        return _cache[key]


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------------------------------------------
# Database (role civicbrain_ai; the caller owns the transaction)
# ---------------------------------------------------------------------------------------------------------------
COMPLAINT_SQL = text(
    """
    SELECT c.title, c.description, cc.category_name
      FROM complaints c
      LEFT JOIN complaint_categories cc ON cc.category_id = c.category_id
     WHERE c.complaint_id = :cid
    """
)
DELETE_SQL = text(
    "DELETE FROM ai_classifications WHERE complaint_id = :cid AND model_type = 'TEXT' AND model_name = :name AND model_version = :version"
)
INSERT_SQL = text(
    """
    INSERT INTO ai_classifications (complaint_id, model_type, predicted_category, predicted_category_id, confidence,
                                    model_name, model_version, top_k, is_accepted)
    VALUES (:cid, 'TEXT', CAST(:category AS varchar),
            (SELECT category_id FROM complaint_categories WHERE category_name = CAST(:category AS varchar)),
            :confidence, :name, :version, CAST(:top_k AS jsonb), :accepted)
    """
)


def write_text_classification(session: Session, complaint_id: int, result: TextResult) -> None:
    session.execute(DELETE_SQL, {"cid": complaint_id, "name": result.model_name, "version": result.model_version})
    session.execute(
        INSERT_SQL,
        {
            "cid": complaint_id,
            "category": result.predicted,
            "confidence": result.confidence,
            "name": result.model_name,
            "version": result.model_version,
            "top_k": json.dumps([{"category": c, "p": p} for c, p in result.top]),
            "accepted": result.is_accepted,
        },
    )


def classify_complaint(session: Session, complaint_id: int, classifier: TextClassifier) -> TextResult:
    """Step 3: classify the complaint's title + description and store the TEXT row."""
    row = session.execute(COMPLAINT_SQL, {"cid": complaint_id}).mappings().one_or_none()
    if row is None:
        raise DataError(f"complaint {complaint_id} not found")
    top = classifier.predict(complaint_text(row["title"], row["description"]))
    accepted = is_accepted(top, row["category_name"])
    result = TextResult(top=top, is_accepted=accepted, model_name=classifier.name, model_version=classifier.version)
    write_text_classification(session, complaint_id, result)
    return result
