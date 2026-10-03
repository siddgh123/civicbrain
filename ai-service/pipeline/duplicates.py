"""Duplicates - ANALYZE_COMPLAINT step 7 (FROZEN Step 12: docs/06_AI_PIPELINE.md sec. 2.6, FR-22).

Port of the scoring in scripts/duplicates/run_duplicate_engine_and_load.py (same arithmetic, same order):
  text_similarity = cosine of the all-MiniLM-L6-v2 embeddings (normalised), clamped 0-1
  distance_score  = 1 - d / 300            recency_score = 1 - hours / 168      (both clamped 0-1)
  score           = 0.70 text + 0.20 distance + 0.10 recency                    (clamped 0-1)
  >= 0.59 DUPLICATE · 0.55-0.59 UNCERTAIN (officer review, never auto-merge) · else NOT_DUPLICATE
Candidates come from fn_duplicate_candidates (300 m, previous 7 days, masters only). Text = title + " " + description
(the research joined them with a newline; the tokenizer treats both as whitespace - tests/unit/test_duplicates_repro.py).

Complaint decision (master rule of data/duplicates/duplicate_engine_config.json + docs/06 sec. 1, 2.6):
- the best DUPLICATE candidate -> the complaint is MERGED into that candidate's master (the earlier complaint);
- DUPLICATE candidates with two different masters -> UNCERTAIN (officer);
- master COMPLETED or CLOSED (maybe a new defect at the same place) -> UNCERTAIN (officer);
- a re-analysis of a complaint that is no longer SUBMITTED never merges -> UNCERTAIN (officer);
- only UNCERTAIN pairs -> UNCERTAIN; nothing -> NOT_DUPLICATE.
Real and synthetic complaints are never compared (synthetic data stays apart, 02-frozen-rules "Honesty").
Every scored pair is upserted into duplicate_relation; the status change itself (SUBMITTED -> MERGED) is the
orchestrator's last step (P12), in the same transaction.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import (
    DUP_DISTANCE_WEIGHT,
    DUP_ENCODE_BATCH,
    DUP_FINISHED_MASTER_STATUSES,
    DUP_MODEL_NAME,
    DUP_RADIUS_M,
    DUP_RECENCY_WEIGHT,
    DUP_TEXT_WEIGHT,
    DUP_THRESHOLD,
    DUP_UNCERTAIN_LOWER,
    DUP_WINDOW_HOURS,
    Settings,
)
from app.errors import ConfigError, DataError, ModelError
from app.models_check import check_manifest, load_manifest

DUPLICATE = "DUPLICATE"
UNCERTAIN = "UNCERTAIN"
NOT_DUPLICATE = "NOT_DUPLICATE"

REVIEW_COMMENTS = {
    "TWO_MASTERS": "Duplicate relation connects two different existing master issues; automatic master merge blocked. "
                   "Officer review required.",
    "MASTER_FINISHED": "Master complaint is COMPLETED or CLOSED (maybe a new defect at the same place); automatic merge "
                       "blocked. Officer review required.",
    "NOT_SUBMITTED": "Re-analysis of a complaint that is no longer SUBMITTED; it is never merged automatically. "
                     "Officer review required.",
    "BORDERLINE": "Borderline duplicate score; automatic merge disabled.",
}


# ---------------------------------------------------------------------------------------------------------------
# Pair score (pure)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class PairScore:
    text_similarity: float
    distance_meters: float
    distance_score: float
    time_difference_hours: float
    recency_score: float
    duplicate_score: float
    decision: str


def _clip(value: float) -> float:
    return min(1.0, max(0.0, value))


def decision_for(score: float) -> str:
    if score >= DUP_THRESHOLD:
        return DUPLICATE
    if score >= DUP_UNCERTAIN_LOWER:
        return UNCERTAIN
    return NOT_DUPLICATE


def score_pair(text_similarity: float, distance_m: float, hours_apart: float) -> PairScore:
    similarity = _clip(text_similarity)
    distance_score = _clip(1.0 - (distance_m / DUP_RADIUS_M))
    recency_score = _clip(1.0 - (hours_apart / DUP_WINDOW_HOURS))
    score = _clip(DUP_TEXT_WEIGHT * similarity + DUP_DISTANCE_WEIGHT * distance_score + DUP_RECENCY_WEIGHT * recency_score)
    return PairScore(similarity, distance_m, distance_score, hours_apart, recency_score, score, decision_for(score))


def complaint_text(title: str, description: str) -> str:
    """docs/06 sec. 2.6: title + " " + description."""
    return f"{(title or '').strip()} {(description or '').strip()}".strip()


# ---------------------------------------------------------------------------------------------------------------
# Complaint decision (pure)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Candidate:
    complaint_id: int
    distance_m: float
    hours_apart: float
    status: str
    master_id: int  # the candidate itself when it is a master (fn_duplicate_candidates returns masters only)
    master_status: str
    is_synthetic: bool = False
    text: str = ""


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Candidate
    pair: PairScore


@dataclass(frozen=True)
class RelationRow:
    similar_complaint_id: int
    master_complaint_id: int | None
    pair: PairScore
    review_required: bool
    review_comment: str | None


@dataclass(frozen=True)
class DuplicateDecision:
    status: str  # complaints.duplicate_status: DUPLICATE / UNCERTAIN / NOT_DUPLICATE
    merge: bool  # true -> the complaint becomes MERGED into master_complaint_id (status change by the orchestrator)
    master_complaint_id: int | None
    matched_complaint_id: int | None  # best DUPLICATE/UNCERTAIN candidate
    review_required: bool
    reason: str  # MERGE, TWO_MASTERS, MASTER_FINISHED, NOT_SUBMITTED, BORDERLINE, NO_MATCH
    relations: tuple[RelationRow, ...]


def same_kind(candidates: Sequence[Candidate], *, is_synthetic: bool) -> list[Candidate]:
    return [c for c in candidates if c.is_synthetic == is_synthetic]


def _rank(s: ScoredCandidate) -> tuple[float, int]:
    return (-s.pair.duplicate_score, s.candidate.complaint_id)  # best score first, ties -> the earlier (lower) id


def decide(scored: Sequence[ScoredCandidate], complaint_status: str) -> DuplicateDecision:
    dup = [s for s in scored if s.pair.decision == DUPLICATE]
    unc = [s for s in scored if s.pair.decision == UNCERTAIN]
    ranked = sorted(dup + unc, key=_rank)
    matched = ranked[0].candidate.complaint_id if ranked else None

    master: int | None = None
    if dup:
        best = min(dup, key=_rank)
        if len({s.candidate.master_id for s in dup}) > 1:
            reason = "TWO_MASTERS"
        elif best.candidate.master_status in DUP_FINISHED_MASTER_STATUSES:
            reason = "MASTER_FINISHED"
        elif complaint_status != "SUBMITTED":
            reason = "NOT_SUBMITTED"
        else:
            reason, master = "MERGE", best.candidate.master_id
    else:
        reason = "BORDERLINE" if unc else "NO_MATCH"
    merge = reason == "MERGE"

    relations = []
    for s in scored:
        if s.pair.decision == DUPLICATE and merge:
            relations.append(RelationRow(s.candidate.complaint_id, master, s.pair, False, None))
        elif s.pair.decision == DUPLICATE:
            relations.append(RelationRow(s.candidate.complaint_id, None, s.pair, True, REVIEW_COMMENTS[reason]))
        elif s.pair.decision == UNCERTAIN:
            relations.append(RelationRow(s.candidate.complaint_id, None, s.pair, True, REVIEW_COMMENTS["BORDERLINE"]))
        else:
            relations.append(RelationRow(s.candidate.complaint_id, None, s.pair, False, None))

    if merge:
        status = DUPLICATE
    elif reason == "NO_MATCH":
        status = NOT_DUPLICATE
    else:
        status = UNCERTAIN
    return DuplicateDecision(status, merge, master, matched, status == UNCERTAIN, reason, tuple(relations))


# ---------------------------------------------------------------------------------------------------------------
# all-MiniLM-L6-v2 (models/all-MiniLM-L6-v2/, every file's SHA-256 in MANIFEST.json, offline)
# ---------------------------------------------------------------------------------------------------------------
class Embedder(Protocol):
    def similarities(self, text: str, others: Sequence[str]) -> list[float]: ...


def _offline_env() -> None:
    """The worker never downloads: Hugging Face libraries read these when they are imported."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


class MiniLmEmbedder:
    def __init__(self, model: object, revision: str) -> None:
        self._model = model
        self.name = DUP_MODEL_NAME
        self.revision = revision
        self._lock = threading.Lock()

    @classmethod
    def load(cls, folder: Path, models_dir: Path) -> MiniLmEmbedder:
        """Check every file against MANIFEST.json BEFORE the library reads the folder."""
        entry_name = folder.name + "/"
        problems = check_manifest(models_dir, [(entry_name, folder)])
        if problems:
            raise ConfigError("; ".join(problems))
        manifest = load_manifest(models_dir) or {"files": []}
        entry = next((e for e in manifest["files"] if isinstance(e, dict) and e.get("path") == entry_name), {})
        _offline_env()
        from sentence_transformers import SentenceTransformer

        try:
            model = SentenceTransformer(str(folder), device="cpu")
        except Exception as exc:  # any loading problem is a model problem
            raise ModelError(f"{entry_name}: cannot be loaded ({type(exc).__name__})") from exc
        return cls(model, str(entry.get("revision") or ""))

    def encode(self, texts: Sequence[str]):
        with self._lock:
            return self._model.encode(  # type: ignore[attr-defined]
                list(texts), batch_size=DUP_ENCODE_BATCH, show_progress_bar=False, normalize_embeddings=True, convert_to_numpy=True
            )

    def similarities(self, text: str, others: Sequence[str]) -> list[float]:
        """Cosine similarity of `text` with each of `others` (dot product of normalised embeddings, not clamped)."""
        if not others:
            return []
        emb = self.encode([text, *others])
        return [float(emb[0] @ e) for e in emb[1:]]


_cache: dict[str, MiniLmEmbedder] = {}
_cache_lock = threading.Lock()


def get_embedder(settings: Settings) -> MiniLmEmbedder:
    """The process-wide embedder (loaded once)."""
    key = str(settings.text_embedding_model_dir)
    with _cache_lock:
        if key not in _cache:
            _cache.clear()
            _cache[key] = MiniLmEmbedder.load(settings.text_embedding_model_dir, settings.models_dir)
        return _cache[key]


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------------------------------------------
# Database (role civicbrain_ai; the caller owns the transaction)
# ---------------------------------------------------------------------------------------------------------------
COMPLAINT_SQL = text("SELECT title, description, status, is_synthetic FROM complaints WHERE complaint_id = :cid")
CANDIDATES_SQL = text(
    """
    SELECT f.candidate_id, f.distance_m, f.hours_apart, o.status, o.title, o.description, o.is_synthetic,
           COALESCE(o.master_complaint_id, o.complaint_id) AS master_id, m.status AS master_status
      FROM fn_duplicate_candidates(:cid) f
      JOIN complaints o ON o.complaint_id = f.candidate_id
      JOIN complaints m ON m.complaint_id = COALESCE(o.master_complaint_id, o.complaint_id)
     ORDER BY f.distance_m, f.candidate_id
    """
)
# Pairs of an earlier run that are no longer candidates (e.g. the candidate was merged meanwhile); officer rows stay.
DELETE_STALE_SQL = text(
    """
    DELETE FROM duplicate_relation
     WHERE complaint_id = :cid AND decision_source = 'AI' AND review_decision IS NULL AND reviewed_at IS NULL
       AND NOT (similar_complaint_id = ANY(CAST(:keep AS bigint[])))
    """
)
UPSERT_SQL = text(
    """
    INSERT INTO duplicate_relation (complaint_id, master_complaint_id, similar_complaint_id, text_similarity, distance_meters,
                                    time_difference_hours, duplicate_score, decision, decision_source, review_required, review_comment)
    VALUES (:cid, :master, :similar, :text, :distance, :hours, :score, :decision, 'AI', :review, :comment)
    ON CONFLICT ((LEAST(complaint_id, similar_complaint_id)), (GREATEST(complaint_id, similar_complaint_id)))
    DO UPDATE SET master_complaint_id = EXCLUDED.master_complaint_id,
                  text_similarity = EXCLUDED.text_similarity,
                  distance_meters = EXCLUDED.distance_meters,
                  time_difference_hours = EXCLUDED.time_difference_hours,
                  duplicate_score = EXCLUDED.duplicate_score,
                  decision = EXCLUDED.decision,
                  review_required = EXCLUDED.review_required,
                  review_comment = EXCLUDED.review_comment
     WHERE duplicate_relation.decision_source = 'AI' AND duplicate_relation.review_decision IS NULL
       AND duplicate_relation.reviewed_at IS NULL
    """
)
COMPLAINT_UPDATE_SQL = text(
    """
    UPDATE complaints
       SET duplicate_status = :status,
           matched_complaint_id = :matched,
           duplicate_checked_at = now(),
           duplicate_review_required = :review,
           master_complaint_id = CASE WHEN CAST(:merge AS boolean) THEN CAST(:master AS bigint) ELSE master_complaint_id END
     WHERE complaint_id = :cid
    """
)


def load_candidates(session: Session, complaint_id: int) -> tuple[dict, list[Candidate]]:
    row = session.execute(COMPLAINT_SQL, {"cid": complaint_id}).mappings().one_or_none()
    if row is None:
        raise DataError(f"complaint {complaint_id} not found")
    candidates = [
        Candidate(
            int(r["candidate_id"]), float(r["distance_m"]), float(r["hours_apart"]), r["status"], int(r["master_id"]),
            r["master_status"], bool(r["is_synthetic"]), complaint_text(r["title"], r["description"]),
        )
        for r in session.execute(CANDIDATES_SQL, {"cid": complaint_id}).mappings()
    ]
    return dict(row), same_kind(candidates, is_synthetic=bool(row["is_synthetic"]))


def write_duplicates(session: Session, complaint_id: int, decision: DuplicateDecision) -> None:
    session.execute(DELETE_STALE_SQL, {"cid": complaint_id, "keep": [r.similar_complaint_id for r in decision.relations]})
    for r in decision.relations:
        p = r.pair
        session.execute(
            UPSERT_SQL,
            {
                "cid": complaint_id, "master": r.master_complaint_id, "similar": r.similar_complaint_id, "text": p.text_similarity,
                "distance": p.distance_meters, "hours": p.time_difference_hours, "score": p.duplicate_score, "decision": p.decision,
                "review": r.review_required, "comment": r.review_comment,
            },
        )
    session.execute(
        COMPLAINT_UPDATE_SQL,
        {"cid": complaint_id, "status": decision.status, "matched": decision.matched_complaint_id, "review": decision.review_required,
         "merge": decision.merge, "master": decision.master_complaint_id},
    )


def find_duplicates(session: Session, complaint_id: int, embedder: Embedder) -> DuplicateDecision:
    """Step 7: score every candidate, decide, store the pairs and the complaint's duplicate fields."""
    complaint, candidates = load_candidates(session, complaint_id)
    sims = embedder.similarities(complaint_text(complaint["title"], complaint["description"]), [c.text for c in candidates])
    scored = [ScoredCandidate(c, score_pair(s, c.distance_m, c.hours_apart)) for c, s in zip(candidates, sims, strict=True)]
    decision = decide(scored, complaint["status"])
    write_duplicates(session, complaint_id, decision)
    return decision
