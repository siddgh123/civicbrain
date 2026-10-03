"""Step 12 duplicates (FROZEN) - pure scoring and the complaint decision (no model, no database)."""

import csv

import pytest

from app.config import REPO_ROOT_DIR
from pipeline import duplicates as du

RESULTS = REPO_ROOT_DIR / "data" / "duplicates" / "duplicate_engine_results.csv"


def test_the_formula_reproduces_all_109_research_pairs_from_their_inputs():
    """Given the research text similarity, distance and hours, every score, sub-score and decision is identical."""
    with RESULTS.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 109
    for r in rows:
        p = du.score_pair(float(r["text_similarity"]), float(r["distance_meters"]), float(r["time_difference_hours"]))
        assert abs(p.distance_score - float(r["distance_score"])) < 1e-12, r["pair_id"]
        assert abs(p.recency_score - float(r["recency_score"])) < 1e-12, r["pair_id"]
        assert abs(p.duplicate_score - float(r["duplicate_score"])) < 1e-12, r["pair_id"]
        assert p.decision == r["decision"], r["pair_id"]
    assert {r["decision"] for r in rows} == {"DUPLICATE", "UNCERTAIN", "NOT_DUPLICATE"}


@pytest.mark.parametrize(
    ("score", "decision"),
    [(1.0, "DUPLICATE"), (0.59, "DUPLICATE"), (0.5899999999, "UNCERTAIN"), (0.57, "UNCERTAIN"), (0.55, "UNCERTAIN"),
     (0.5499999999, "NOT_DUPLICATE"), (0.0, "NOT_DUPLICATE")],
)
def test_threshold_edges(score, decision):
    assert du.decision_for(score) == decision


def test_score_by_hand():
    p = du.score_pair(0.8, 60.0, 16.8)  # 0.70*0.8 + 0.20*(1 - 60/300) + 0.10*(1 - 16.8/168) = 0.56 + 0.16 + 0.09
    assert (p.distance_score, p.recency_score) == pytest.approx((0.8, 0.9))
    assert p.duplicate_score == pytest.approx(0.81) and p.decision == "DUPLICATE"


@pytest.mark.parametrize(
    ("args", "field", "expected"),
    [
        ((0.5, 0.0, 10.0), "distance_score", 1.0),
        ((0.5, 300.0, 10.0), "distance_score", 0.0),
        ((0.5, 450.0, 10.0), "distance_score", 0.0),
        ((0.5, 10.0, 0.0), "recency_score", 1.0),
        ((0.5, 10.0, 168.0), "recency_score", 0.0),
        ((0.5, 10.0, 200.0), "recency_score", 0.0),
        ((0.5, 10.0, -2.0), "recency_score", 1.0),
        ((-0.3, 10.0, 10.0), "text_similarity", 0.0),
        ((1.2, 10.0, 10.0), "text_similarity", 1.0),
    ],
)
def test_clamps(args, field, expected):
    assert getattr(du.score_pair(*args), field) == expected


def test_perfect_pair_scores_one_and_never_more():
    # 0.70 + 0.20 + 0.10 in floating point is 0.9999999999999999 - the research engine (np.clip) gives the same
    score = du.score_pair(1.5, -5.0, -1.0).duplicate_score
    assert score <= 1.0 and score == pytest.approx(1.0)


# ---- the complaint decision ----

def _cand(cid, score, *, status="VERIFIED", master_id=None, master_status=None):
    """A candidate whose pair has exactly `score` (decision from the frozen thresholds)."""
    pair = du.PairScore(0.5, 10.0, 0.9, 1.0, 0.99, score, du.decision_for(score))
    cand = du.Candidate(cid, 10.0, 1.0, status, master_id or cid, master_status or status)
    return du.ScoredCandidate(cand, pair)


def test_no_candidates_is_not_duplicate():
    d = du.decide([], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id, d.review_required) == (
        "NOT_DUPLICATE", False, None, None, False)
    assert d.relations == ()


def test_only_low_scores_is_not_duplicate_but_every_pair_is_kept():
    d = du.decide([_cand(5, 0.30), _cand(6, 0.54)], "SUBMITTED")
    assert (d.status, d.merge, d.matched_complaint_id) == ("NOT_DUPLICATE", False, None)
    assert [(r.similar_complaint_id, r.pair.decision, r.review_required) for r in d.relations] == [
        (5, "NOT_DUPLICATE", False), (6, "NOT_DUPLICATE", False)]


def test_best_duplicate_merges_into_the_candidates_master():
    d = du.decide([_cand(5, 0.62), _cand(6, 0.57), _cand(7, 0.20)], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id, d.review_required) == ("DUPLICATE", True, 5, 5, False)
    rel = {r.similar_complaint_id: r for r in d.relations}
    assert (rel[5].master_complaint_id, rel[5].review_required, rel[5].review_comment) == (5, False, None)
    assert (rel[6].pair.decision, rel[6].review_required, rel[6].master_complaint_id) == ("UNCERTAIN", True, None)
    assert rel[6].review_comment == "Borderline duplicate score; automatic merge disabled."
    assert (rel[7].review_required, rel[7].master_complaint_id) == (False, None)


def test_a_candidate_that_is_a_child_points_to_its_master():
    d = du.decide([_cand(9, 0.70, master_id=4, master_status="VERIFIED")], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id) == ("DUPLICATE", True, 4, 9)


def test_two_different_masters_need_the_officer():
    d = du.decide([_cand(5, 0.75), _cand(6, 0.64)], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id, d.review_required) == ("UNCERTAIN", False, None, 5, True)
    assert d.reason == "TWO_MASTERS"
    for r in d.relations:
        assert r.pair.decision == "DUPLICATE" and r.review_required and r.master_complaint_id is None
        assert "two different existing master issues" in r.review_comment


def test_duplicates_of_the_same_master_still_merge():
    d = du.decide([_cand(5, 0.75), _cand(9, 0.64, master_id=5, master_status="VERIFIED")], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id) == ("DUPLICATE", True, 5, 5)


@pytest.mark.parametrize("finished", ["COMPLETED", "CLOSED"])
def test_finished_master_needs_the_officer(finished):
    d = du.decide([_cand(5, 0.80, status=finished)], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id, d.review_required, d.reason) == (
        "UNCERTAIN", False, None, 5, True, "MASTER_FINISHED")
    assert d.relations[0].review_required and "COMPLETED or CLOSED" in d.relations[0].review_comment


def test_uncertain_only_never_merges():
    d = du.decide([_cand(5, 0.56), _cand(6, 0.58)], "SUBMITTED")
    assert (d.status, d.merge, d.master_complaint_id, d.matched_complaint_id, d.review_required, d.reason) == (
        "UNCERTAIN", False, None, 6, True, "BORDERLINE")


def test_reanalysis_of_a_complaint_that_is_no_longer_submitted_never_merges():
    d = du.decide([_cand(5, 0.80)], "VERIFIED")
    assert (d.status, d.merge, d.master_complaint_id, d.review_required, d.reason) == ("UNCERTAIN", False, None, True, "NOT_SUBMITTED")
    assert d.relations[0].review_required


def test_equal_scores_pick_the_earlier_candidate():
    d = du.decide([_cand(8, 0.66, master_id=8), _cand(3, 0.66, master_id=8)], "SUBMITTED")
    assert d.matched_complaint_id == 3 and d.master_complaint_id == 8


def test_real_and_synthetic_complaints_are_never_compared():
    real = du.Candidate(1, 10.0, 1.0, "VERIFIED", 1, "VERIFIED", is_synthetic=False)
    synthetic = du.Candidate(2, 10.0, 1.0, "SUBMITTED", 2, "SUBMITTED", is_synthetic=True)
    assert du.same_kind([real, synthetic], is_synthetic=False) == [real]
    assert du.same_kind([real, synthetic], is_synthetic=True) == [synthetic]


def test_duplicate_text_is_title_space_description():
    assert du.complaint_text("  Big pothole ", " near the bus stand ") == "Big pothole near the bus stand"
