"""Step 12 reproduction with the installed all-MiniLM-L6-v2 (FROZEN, docs/09_BUILD_PLAN_7DAY.md sec. 4).

Three pairs of data/duplicates/duplicate_engine_results.csv - one DUPLICATE, one UNCERTAIN, one NOT_DUPLICATE - are
scored again from the complaint texts (data/complaints/synthetic_complaints_500.csv = the research complaints) and
the research distance/hours: same text similarity and score within 0.001, same decision.
Skips only when the model folder is absent (CI).
"""

import csv

import numpy as np
import pytest

from app.config import REPO_ROOT_DIR, get_settings
from pipeline import duplicates as du

pytestmark = pytest.mark.models

PAIRS = {"ENG0059": "DUPLICATE", "ENG0069": "UNCERTAIN", "ENG0001": "NOT_DUPLICATE"}


def _csv(path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def embedder():
    settings = get_settings()
    if not settings.text_embedding_model_dir.is_dir():
        pytest.skip("all-MiniLM-L6-v2 not installed (CI)")
    du.clear_cache()
    yield du.get_embedder(settings)
    du.clear_cache()


@pytest.fixture(scope="module")
def texts() -> dict[int, str]:
    rows = _csv(REPO_ROOT_DIR / "data" / "complaints" / "synthetic_complaints_500.csv")
    return {int(r["complaint_id"]): du.complaint_text(r["title"], r["description"]) for r in rows}


def test_three_research_pairs_are_reproduced(embedder, texts, capsys):
    rows = {r["pair_id"]: r for r in _csv(REPO_ROOT_DIR / "data" / "duplicates" / "duplicate_engine_results.csv")}
    lines = []
    for pair_id, label in PAIRS.items():
        r = rows[pair_id]
        assert r["decision"] == label
        a, b = int(r["complaint_id_1"]), int(r["complaint_id_2"])
        similarity = embedder.similarities(texts[a], [texts[b]])[0]
        p = du.score_pair(similarity, float(r["distance_meters"]), float(r["time_difference_hours"]))
        lines.append(f"{pair_id} {label}: text {similarity:.6f} vs {float(r['text_similarity']):.6f}, "
                     f"score {p.duplicate_score:.6f} vs {float(r['duplicate_score']):.6f} -> {p.decision}")
        assert abs(p.text_similarity - float(r["text_similarity"])) < 0.001, pair_id
        assert abs(p.duplicate_score - float(r["duplicate_score"])) < 0.001, pair_id
        assert p.decision == label, pair_id
    with capsys.disabled():
        print("\nDUPLICATES REPRO:\n  " + "\n  ".join(lines))


def test_title_and_description_joined_by_space_or_newline_embed_the_same(embedder):
    """The research engine joined title and description with a newline, docs/06 with a space: the MiniLM tokenizer
    treats both as whitespace, so the embeddings are the same."""
    title, description = "Waterlogging on road", "Rainwater has accumulated on the road."
    emb = embedder.encode([f"{title} {description}", f"{title}\n{description}"])
    assert emb.shape == (2, 384)
    assert float(np.max(np.abs(emb[0] - emb[1]))) < 1e-6


def test_embedder_is_loaded_once_with_the_manifest_revision(embedder):
    assert du.get_embedder(get_settings()) is embedder
    assert embedder.name == "sentence-transformers/all-MiniLM-L6-v2" and len(embedder.revision) == 40
