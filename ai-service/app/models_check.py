"""Model files check against models/MANIFEST.json (docs/06_AI_PIPELINE.md sec. 5, ai-service/models/README.md).

Manifest format (written by training/model_manifest.py): {"manifest_version": 1, "files": [entry, ...]} where a
file entry is {"path": "<name>", "sha256": "<hex>", ...} and a folder entry is
{"path": "<folder>/", "files": [{"path": "<relative>", "sha256": "<hex>"}, ...]}.

`check_models()` returns a list of problems (empty = every required file present with the right SHA-256).
Until P12 a problem is only a warning (REQUIRE_MODELS=false); from P12 the worker and the API refuse to start.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from app.config import TEXT_CLF_FILE, YUNET_FILE, Settings

MANIFEST_NAME = "MANIFEST.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(models_dir: Path) -> dict | None:
    """The parsed manifest, or None when the file does not exist. ValueError on a broken file."""
    path = models_dir / MANIFEST_NAME
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("manifest_version") != 1 or not isinstance(data.get("files"), list):
        raise ValueError("unexpected format (manifest_version 1 with a files list expected)")
    return data


def required_files(settings: Settings) -> list[tuple[str, Path]]:
    """(manifest path, local path) of every model the worker needs. A trailing '/' marks a folder."""
    required = [
        (settings.yolo_weights.name, settings.yolo_weights),
        (TEXT_CLF_FILE, settings.models_dir / TEXT_CLF_FILE),
        (settings.text_embedding_model_dir.name + "/", settings.text_embedding_model_dir),
    ]
    if settings.blur_enabled:
        required.append((YUNET_FILE, settings.models_dir / YUNET_FILE))
    return required


def check_models(settings: Settings) -> list[str]:
    return check_manifest(settings.models_dir, required_files(settings))


def check_manifest(models_dir: Path, required: list[tuple[str, Path]]) -> list[str]:
    """Problems as short texts with manifest-relative names (no absolute paths, nothing secret)."""
    try:
        manifest = load_manifest(models_dir)
    except (OSError, ValueError) as exc:  # json.JSONDecodeError is a ValueError
        return [f"{MANIFEST_NAME}: cannot be read ({type(exc).__name__})"]
    problems: list[str] = []
    if manifest is None:
        problems.append(f"{MANIFEST_NAME}: not found in MODELS_DIR")
    entries = {e.get("path"): e for e in (manifest or {}).get("files", []) if isinstance(e, dict)}
    for name, local in required:
        if name.endswith("/"):
            problems.extend(_check_folder(name, local, entries.get(name), listed=manifest is not None))
        else:
            problems.extend(_check_file(name, local, entries.get(name), listed=manifest is not None))
    return problems


def _check_file(name: str, local: Path, entry: dict | None, *, listed: bool) -> list[str]:
    if not local.is_file():
        return [f"{name}: file missing"]
    if entry is None:
        return [f"{name}: not listed in {MANIFEST_NAME}"] if listed else []
    expected = str(entry.get("sha256") or "").lower()
    if not expected:
        return [f"{name}: manifest entry has no sha256"]
    if sha256_file(local) != expected:
        return [f"{name}: SHA-256 differs from {MANIFEST_NAME}"]
    return []


def _check_folder(name: str, local: Path, entry: dict | None, *, listed: bool) -> list[str]:
    if not local.is_dir():
        return [f"{name}: folder missing"]
    if entry is None:
        return [f"{name}: not listed in {MANIFEST_NAME}"] if listed else []
    files = entry.get("files")
    if not isinstance(files, list) or not files:
        return [f"{name}: manifest entry has no file list"]
    problems = []
    for f in files:
        rel = str(f.get("path") or "") if isinstance(f, dict) else ""
        if not rel or ".." in PurePosixPath(rel).parts or PurePosixPath(rel).is_absolute():
            problems.append(f"{name}: manifest lists an invalid path")
            continue
        path = local / rel
        if not path.is_file():
            problems.append(f"{name}{rel}: file missing")
        elif sha256_file(path) != str(f.get("sha256") or "").lower():
            problems.append(f"{name}{rel}: SHA-256 differs from {MANIFEST_NAME}")
    return problems


def describe_models(settings: Settings) -> dict:
    """Body of GET /v1/models (docs/04_API_CONTRACT.md sec. 10). Values are null until a model is installed."""
    try:
        manifest = load_manifest(settings.models_dir) or {"files": []}
    except (OSError, ValueError):
        manifest = {"files": []}
    entries = {e.get("path"): e for e in manifest["files"] if isinstance(e, dict)}
    yolo = entries.get(settings.yolo_weights.name) or {}
    clf = entries.get(TEXT_CLF_FILE) or {}
    emb = entries.get(settings.text_embedding_model_dir.name + "/") or {}
    clf_sha = str(clf.get("sha256") or "")
    return {
        "yolo": {"file": settings.yolo_weights.name, "sha256": yolo.get("sha256"), "classes": yolo.get("classes")},
        "classifier": {"version": clf.get("version") or (clf_sha[:12] or None)},
        "embedding": {"name": emb.get("repo") or (settings.text_embedding_model_dir.name if emb else None)},
    }
