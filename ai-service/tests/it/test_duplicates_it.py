"""Step 12 duplicates against civicbrain_test (role civicbrain_ai): candidates from fn_duplicate_candidates, the upsert
into duplicate_relation and the complaint's duplicate fields. The status change to MERGED is the orchestrator's step
(P12) - here the decision object says "would be MERGED". Fixture rows are inserted as the owner and deleted afterwards.
"""

import datetime as dt

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.db import session_scope
from pipeline import duplicates as du

pytestmark = pytest.mark.integration

WARD1 = (18.7440, 73.6760)  # inside ward number 1 (docs/08_TEST_PLAN.md sec. 2)
M_LAT = 0.0000090  # about 1 m of latitude
NOW = dt.datetime.now(dt.UTC).replace(microsecond=0)


def _complaint(it, at, submitted, title, description, *, synthetic=False) -> int:
    user_id = it.user_ids[0] if it.user_ids else it.new_user()
    with it.engine.begin() as conn:
        conn.execute(text("SELECT set_config('civicbrain.actor_role', 'CITIZEN', true), set_config('civicbrain.actor_user_id', :u, true)"),
                     {"u": str(user_id)})
        cid = conn.execute(
            text(
                "INSERT INTO complaints (user_id, category_id, title, description, location, location_source, submitted_at, is_synthetic) "
                "VALUES (:u, (SELECT category_id FROM complaint_categories WHERE category_name = 'Pothole'), :t, :d, "
                "        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :src, :sub, :syn) RETURNING complaint_id"
            ),
            {"u": user_id, "t": title, "d": description, "lat": at[0], "lon": at[1], "src": "SYNTHETIC" if synthetic else "BROWSER_GPS",
             "sub": submitted, "syn": synthetic},
        ).scalar_one()
    it.complaint_ids.append(cid)
    return cid


def _north(metres: float) -> tuple[float, float]:
    return WARD1[0] + metres * M_LAT, WARD1[1]


def _relations(it, complaint_id: int) -> list[dict]:
    return [dict(r) for r in it._sql(
        "SELECT similar_complaint_id, master_complaint_id, decision, review_required, review_comment, review_decision, "
        "       duplicate_score, text_similarity, distance_meters, time_difference_hours, decision_source "
        "FROM duplicate_relation WHERE complaint_id = :c ORDER BY similar_complaint_id", c=complaint_id)]


def _fields(it, complaint_id: int) -> dict:
    return dict(it._sql(
        "SELECT status, duplicate_status, master_complaint_id, matched_complaint_id, duplicate_review_required, duplicate_checked_at "
        "FROM complaints WHERE complaint_id = :c", c=complaint_id)[0])


@pytest.mark.models
def test_similar_complaint_40_m_away_the_same_day_is_a_duplicate_that_would_be_merged(it_data, ai_engine):
    settings = get_settings()
    if not settings.text_embedding_model_dir.is_dir():
        pytest.skip("all-MiniLM-L6-v2 not installed (CI)")
    embedder = du.get_embedder(settings)
    earlier = _complaint(it_data, WARD1, NOW - dt.timedelta(hours=2), "Big pothole near the bus stand",
                         "A deep pothole in the middle of the road near the bus stand, bikes fall into it.")
    far = _complaint(it_data, _north(500), NOW - dt.timedelta(hours=1), "Big pothole near the bus stand",
                     "A deep pothole in the middle of the road near the bus stand, bikes fall into it.")
    synthetic = _complaint(it_data, _north(20), NOW - dt.timedelta(hours=1), "Big pothole near the bus stand",
                           "A deep pothole in the middle of the road near the bus stand, bikes fall into it.", synthetic=True)
    later = _complaint(it_data, _north(40), NOW, "Large pothole close to the bus stand",
                       "There is a large pothole on the road close to the bus stand and two-wheelers fall in it.")

    for _ in range(2):  # the same job twice -> the same end state
        with session_scope(ai_engine) as s:
            decision = du.find_duplicates(s, later, embedder)
    assert (decision.status, decision.merge, decision.master_complaint_id, decision.matched_complaint_id, decision.review_required) == (
        "DUPLICATE", True, earlier, earlier, False)
    rows = _relations(it_data, later)
    assert [r["similar_complaint_id"] for r in rows] == [earlier]  # not the far one (500 m), not the synthetic one
    row = rows[0]
    assert (row["decision"], row["master_complaint_id"], row["review_required"], row["decision_source"]) == (
        "DUPLICATE", earlier, False, "AI")
    assert 38 < row["distance_meters"] < 42 and abs(row["time_difference_hours"] - 2) < 0.01
    assert row["duplicate_score"] >= 0.59 and row["text_similarity"] > 0.6
    assert row["duplicate_score"] == pytest.approx(decision.relations[0].pair.duplicate_score)
    fields = _fields(it_data, later)
    assert (fields["status"], fields["duplicate_status"], fields["master_complaint_id"], fields["matched_complaint_id"]) == (
        "SUBMITTED", "DUPLICATE", earlier, earlier)  # MERGED is set by the orchestrator (P12)
    assert fields["duplicate_review_required"] is False and fields["duplicate_checked_at"] is not None
    assert _relations(it_data, far) == [] and _relations(it_data, synthetic) == []


class FakeEmbedder:
    """Fixed similarities, in candidate order (distance, then id)."""

    def __init__(self, values: list[float]) -> None:
        self.values = values

    def similarities(self, query: str, others) -> list[float]:
        assert len(others) == len(self.values)
        return list(self.values)


def test_two_masters_need_the_officer_and_officer_reviews_are_never_overwritten(it_data, ai_engine):
    first = _complaint(it_data, _north(30), NOW - dt.timedelta(hours=5), "Pothole", "pothole one")
    second = _complaint(it_data, _north(60), NOW - dt.timedelta(hours=4), "Pothole", "pothole two")
    cid = _complaint(it_data, WARD1, NOW, "Pothole", "pothole three")

    with session_scope(ai_engine) as s:
        decision = du.find_duplicates(s, cid, FakeEmbedder([0.9, 0.95]))
    assert (decision.status, decision.merge, decision.master_complaint_id, decision.reason) == ("UNCERTAIN", False, None, "TWO_MASTERS")
    assert decision.matched_complaint_id == second  # 0.95 at 60 m scores higher than 0.90 at 30 m
    rows = _relations(it_data, cid)
    assert [(r["similar_complaint_id"], r["decision"], r["review_required"], r["master_complaint_id"]) for r in rows] == [
        (first, "DUPLICATE", True, None), (second, "DUPLICATE", True, None)]
    assert all("two different existing master issues" in r["review_comment"] for r in rows)
    f = _fields(it_data, cid)
    assert (f["duplicate_status"], f["master_complaint_id"], f["matched_complaint_id"], f["duplicate_review_required"]) == (
        "UNCERTAIN", None, second, True)

    # the officer keeps the first pair separate; a re-analysis with low similarities must not touch that row
    officer = it_data.user_ids[0]
    it_data._sql("UPDATE duplicate_relation SET review_decision = 'KEEP_SEPARATE', reviewed_by = :u, reviewed_at = now() "
                 "WHERE complaint_id = :c AND similar_complaint_id = :s", u=officer, c=cid, s=first)
    with session_scope(ai_engine) as s:
        decision = du.find_duplicates(s, cid, FakeEmbedder([0.1, 0.1]))
    assert (decision.status, decision.matched_complaint_id, decision.review_required) == ("NOT_DUPLICATE", None, False)
    rows = {r["similar_complaint_id"]: r for r in _relations(it_data, cid)}
    assert (rows[first]["decision"], rows[first]["review_decision"], rows[first]["review_required"]) == ("DUPLICATE", "KEEP_SEPARATE", True)
    assert (rows[second]["decision"], rows[second]["review_required"], rows[second]["review_comment"]) == ("NOT_DUPLICATE", False, None)
    assert _fields(it_data, cid)["duplicate_status"] == "NOT_DUPLICATE"


def test_pairs_that_are_no_longer_candidates_are_removed(it_data, ai_engine):
    master = _complaint(it_data, _north(30), NOW - dt.timedelta(hours=5), "Pothole", "pothole one")
    child = _complaint(it_data, _north(50), NOW - dt.timedelta(hours=4), "Pothole", "pothole two")
    cid = _complaint(it_data, WARD1, NOW, "Pothole", "pothole three")
    with session_scope(ai_engine) as s:
        du.find_duplicates(s, cid, FakeEmbedder([0.2, 0.2]))
    assert [r["similar_complaint_id"] for r in _relations(it_data, cid)] == [master, child]

    # the officer merges `child` into `master`: it is no longer a candidate (masters only)
    with it_data.engine.begin() as conn:
        conn.execute(text("SELECT set_config('civicbrain.actor_role', 'OFFICER', true)"))
        conn.execute(text("UPDATE complaints SET status = 'MERGED', master_complaint_id = :m WHERE complaint_id = :c"),
                     {"m": master, "c": child})
    with session_scope(ai_engine) as s:
        decision = du.find_duplicates(s, cid, FakeEmbedder([0.2]))
    assert decision.status == "NOT_DUPLICATE"
    assert [r["similar_complaint_id"] for r in _relations(it_data, cid)] == [master]
