"""CivicBrain | ai-service/training/model_manifest.py - helpers for ai-service/models/MANIFEST.json

Used by install_kaggle_model.py and download_models.py. The worker and the AI API check every file listed
here (SHA-256) before they start (docs/06_AI_PIPELINE.md sec. 5). Standard library only.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "ai-service" / "models"
FROZEN_CLASSES = ["Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).astimezone().isoformat(timespec="seconds")


def load_manifest(models_dir: Path = MODELS_DIR) -> dict:
    path = models_dir / "MANIFEST.json"
    if not path.is_file():
        return {"manifest_version": 1, "created_at": now_iso(), "files": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("manifest_version") != 1 or not isinstance(data.get("files"), list):
        raise ValueError(f"{path} has an unexpected format (manifest_version 1 with a files list expected)")
    return data


def upsert_entry(entry: dict, models_dir: Path = MODELS_DIR) -> Path:
    """Adds or replaces the entry with the same 'path'; writes the file atomically."""
    if not entry.get("path"):
        raise ValueError("manifest entry needs a path")
    data = load_manifest(models_dir)
    data["files"] = [e for e in data["files"] if e.get("path") != entry["path"]] + [entry]
    data["files"].sort(key=lambda e: e["path"])
    data["updated_at"] = now_iso()
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / "MANIFEST.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path
