"""CivicBrain | ai-service/training/train_text_clf.py - complaint-text classifier (docs/06_AI_PIPELINE.md sec. 2.2)

The agent may run it (prompt P08):

    ai-service\\.venv\\Scripts\\python.exe ai-service\\training\\train_text_clf.py

Train  = data/complaints/synthetic_complaints_500.csv (title + ". " + description) + kit_authored_train.csv.
Recipe = TF-IDF union (word 1-2-grams, char_wb 2-5-grams, sublinear tf) -> LogisticRegression(class_weight='balanced',
         max_iter=2000, random_state=42); C from 5-fold stratified CV (shuffle, seed 42, macro-F1) over [1, 2, 5, 10],
         ties -> the smallest C.
Report = accuracy, macro-F1, confusion matrix on sanity_test_mvp.csv - a "sanity check on 40 kit-written sentences",
         never called an evaluation on real data (data/complaints/README.md).
Writes   ai-service/models/text_clf.joblib, ai-service/models/text_clf_metrics.json, docs/reports/text_clf_metrics.json and
         the MANIFEST.json entry (kind text-classifier, sha256, data files + row counts, C, metrics).
Exit codes: 0 saved, 1 regression guard failed (sanity accuracy < 0.80, nothing saved), 2 input missing.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_manifest import MODELS_DIR, REPO_ROOT, now_iso, sha256_file, upsert_entry  # noqa: E402

DATA_DIR = REPO_ROOT / "data" / "complaints"
SYNTHETIC_CSV = DATA_DIR / "synthetic_complaints_500.csv"
KIT_TRAIN_CSV = DATA_DIR / "kit_authored_train.csv"
SANITY_CSV = DATA_DIR / "sanity_test_mvp.csv"
MODEL_FILE = "text_clf.joblib"
METRICS_FILE = "text_clf_metrics.json"

C_GRID = (1.0, 2.0, 5.0, 10.0)
CV_FOLDS = 5
CV_SCORING = "f1_macro"
SEED = 42
SANITY_MIN_ACCURACY = 0.80  # regression guard (docs/06 sec. 2.2 measured ~0.90 with this recipe)
SANITY_LABEL = "sanity check on 40 kit-written sentences"


@dataclass(frozen=True)
class DataFile:
    path: Path
    rows: int
    sha256: str

    @property
    def rel(self) -> str:
        return self.path.relative_to(REPO_ROOT).as_posix()


@dataclass(frozen=True)
class Data:
    train_files: list[DataFile]
    train_texts: list[str]
    train_labels: list[str]
    sanity_file: DataFile
    sanity_texts: list[str]
    sanity_labels: list[str]


@dataclass(frozen=True)
class Trained:
    pipeline: Pipeline
    c: float
    cv_mean_by_c: dict[float, float]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _need(row: dict[str, str], key: str, path: Path) -> str:
    value = (row.get(key) or "").strip()
    if not value:
        raise ValueError(f"{path.name}: empty '{key}' in row {row}")
    return value


def load_data(synthetic: Path = SYNTHETIC_CSV, kit_train: Path = KIT_TRAIN_CSV, sanity: Path = SANITY_CSV) -> Data:
    texts: list[str] = []
    labels: list[str] = []
    syn_rows = _read_csv(synthetic)
    for r in syn_rows:
        texts.append(f"{_need(r, 'title', synthetic)}. {_need(r, 'description', synthetic)}")
        labels.append(_need(r, "category", synthetic))
    kit_rows = _read_csv(kit_train)
    for r in kit_rows:
        texts.append(_need(r, "text", kit_train))
        labels.append(_need(r, "category", kit_train))
    san_rows = _read_csv(sanity)
    sanity_texts = [_need(r, "text", sanity) for r in san_rows]
    sanity_labels = [_need(r, "category", sanity) for r in san_rows]
    if set(sanity_labels) - set(labels):
        raise ValueError(f"sanity labels not in the training data: {sorted(set(sanity_labels) - set(labels))}")
    overlap = set(sanity_texts) & set(texts)
    if overlap:
        raise ValueError(f"{len(overlap)} sanity sentence(s) also in the training data")
    return Data(
        train_files=[
            DataFile(synthetic, len(syn_rows), sha256_file(synthetic)),
            DataFile(kit_train, len(kit_rows), sha256_file(kit_train)),
        ],
        train_texts=texts,
        train_labels=labels,
        sanity_file=DataFile(sanity, len(san_rows), sha256_file(sanity)),
        sanity_texts=sanity_texts,
        sanity_labels=sanity_labels,
    )


def build_pipeline(c: float) -> Pipeline:
    features = FeatureUnion(
        [
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ]
    )
    clf = LogisticRegression(C=c, class_weight="balanced", max_iter=2000, random_state=SEED)
    return Pipeline([("features", features), ("clf", clf)])


def train(data: Data, c_grid: tuple[float, ...] = C_GRID) -> Trained:
    folds = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    means = {}
    for c in c_grid:
        scores = cross_val_score(build_pipeline(c), data.train_texts, data.train_labels, cv=folds, scoring=CV_SCORING)
        means[c] = round(float(np.mean(scores)), 6)
    best = max(means.values())
    chosen = min(c for c, m in means.items() if m == best)
    pipe = build_pipeline(chosen).fit(data.train_texts, data.train_labels)
    return Trained(pipeline=pipe, c=chosen, cv_mean_by_c=means)


def evaluate(pipe: Pipeline, texts: list[str], labels: list[str]) -> dict:
    names = [str(c) for c in pipe.classes_]
    pred = list(pipe.predict(texts))
    proba = pipe.predict_proba(texts)
    p, r, f, s = precision_recall_fscore_support(labels, pred, labels=names, zero_division=0)
    errors = [
        {"text": t, "true": y, "predicted": yp, "p": round(float(pr.max()), 4)}
        for t, y, yp, pr in zip(texts, labels, pred, proba, strict=True)
        if y != yp
    ]
    return {
        "rows": len(texts),
        "accuracy": round(float(accuracy_score(labels, pred)), 4),
        "macro_f1": round(float(f1_score(labels, pred, labels=names, average="macro", zero_division=0)), 4),
        "labels": names,
        "confusion_matrix": confusion_matrix(labels, pred, labels=names).tolist(),
        "per_class": {
            n: {"precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4), "f1": round(float(f[i]), 4), "support": int(s[i])}
            for i, n in enumerate(names)
        },
        "errors": errors,
    }


def metrics_document(data: Data, trained: Trained, sanity: dict, sha256: str) -> dict:
    return {
        "model": MODEL_FILE,
        "kind": "text-classifier",
        "model_sha256": sha256,
        "recipe": {
            "features": "TF-IDF union: word 1-2-grams + char_wb 2-5-grams, sublinear tf",
            "classifier": "LogisticRegression(class_weight='balanced', max_iter=2000, random_state=42)",
            "c_selection": f"{CV_FOLDS}-fold stratified CV (shuffle, seed {SEED}, {CV_SCORING}) over {list(C_GRID)}; ties -> smallest C",
        },
        "C": trained.c,
        "cv_mean_by_C": {str(c): m for c, m in trained.cv_mean_by_c.items()},
        "train": {
            "rows": len(data.train_texts),
            "distinct_texts": len(set(data.train_texts)),
            "files": [{"file": f.rel, "rows": f.rows, "sha256": f.sha256} for f in data.train_files],
            "note": "synthetic Step 8 complaints (only 24 distinct texts) + kit-written bootstrap sentences - not real citizen reports",
        },
        "sanity": {"label": SANITY_LABEL, "file": data.sanity_file.rel, "sha256": data.sanity_file.sha256, **sanity},
        "sklearn": sklearn.__version__,
        "created_at": now_iso(),
    }


def manifest_entry(data: Data, trained: Trained, sanity: dict, sha256: str) -> dict:
    return {
        "path": MODEL_FILE,
        "sha256": sha256,
        "kind": "text-classifier",
        "version": sha256[:12],
        "labels": sanity["labels"],
        "C": trained.c,
        "data": [{"file": f.rel, "rows": f.rows, "sha256": f.sha256} for f in data.train_files],
        "metrics_file": METRICS_FILE,
        "metrics": {"sanity_accuracy": sanity["accuracy"], "sanity_macro_f1": sanity["macro_f1"], "sanity_label": SANITY_LABEL},
        "sklearn": sklearn.__version__,
        "trained_at": now_iso(),
    }


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", type=Path, default=MODELS_DIR)
    ap.add_argument("--reports-dir", type=Path, default=REPO_ROOT / "docs" / "reports")
    args = ap.parse_args(argv)

    missing = [p.name for p in (SYNTHETIC_CSV, KIT_TRAIN_CSV, SANITY_CSV) if not p.is_file()]
    if missing:
        print(f"ERROR: missing data files in data/complaints: {missing}", file=sys.stderr)
        return 2
    data = load_data()
    trained = train(data)
    sanity = evaluate(trained.pipeline, data.sanity_texts, data.sanity_labels)
    distinct = len(set(data.train_texts))
    print(f"TRAIN     {len(data.train_texts)} rows ({distinct} distinct texts), CV {CV_SCORING} by C: {trained.cv_mean_by_c}")
    print(f"C         {trained.c}")
    print(f"SANITY    accuracy={sanity['accuracy']} macro_F1={sanity['macro_f1']} ({SANITY_LABEL})")
    for e in sanity["errors"]:
        print(f"  wrong: {e['true']:21s} -> {e['predicted']:21s} p={e['p']:.2f}  {e['text']}")
    if sanity["accuracy"] < SANITY_MIN_ACCURACY:
        print(f"ERROR: sanity accuracy {sanity['accuracy']} < {SANITY_MIN_ACCURACY} - nothing saved", file=sys.stderr)
        return 1

    args.models_dir.mkdir(parents=True, exist_ok=True)
    target = args.models_dir / MODEL_FILE
    tmp = target.with_suffix(".joblib.tmp")
    joblib.dump(trained.pipeline, tmp)
    os.replace(tmp, target)
    digest = sha256_file(target)
    doc = metrics_document(data, trained, sanity, digest)
    _write_json(args.models_dir / METRICS_FILE, doc)
    _write_json(args.reports_dir / METRICS_FILE, doc)
    manifest = upsert_entry(manifest_entry(data, trained, sanity, digest), args.models_dir)
    print(f"SAVED     {target} (sha256 {digest[:12]}...)")
    print(f"METRICS   {args.models_dir / METRICS_FILE} + {args.reports_dir / METRICS_FILE}")
    print(f"MANIFEST  {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
