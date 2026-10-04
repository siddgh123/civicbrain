"""V6 MVP scope (2026-10-04): citizens report 5 categories; "Other" (work type REVIEW_REQUIRED, no YOLO class, no depth
question) must run through every pipeline step built so far - classify, detect, authenticity, priority, duplicates -
without an error, and no step may change the citizen's category. The text classifier stays 8-class (its sanity
metric stays valid): a suggestion of a category citizens can no longer choose (e.g. Streetlight) is only a hint for
the officer (is_accepted = false), never a category change. Priority uses the documented default for a complaint
without a depth answer (severity MEDIUM, ASSUMPTION); the frozen Step 11/12 weights and thresholds are untouched.

Fixture rows are inserted as the owner (it_data) and deleted afterwards (docs/08_TEST_PLAN.md sec. 2).
"""

import datetime as dt
import random
import uuid
from collections.abc import Sequence

import pytest
from sqlalchemy import text

from app.config import PRIORITY_WEIGHTS, REPO_ROOT_DIR, get_settings
from app.db import session_scope
from pipeline import authenticity as au
from pipeline import classify as cl
from pipeline import detect as de
from pipeline import duplicates as du
from pipeline import priority as pr
from training.train_text_clf import build_pipeline

pytestmark = pytest.mark.integration

WARD1 = (18.7440, 73.6760)  # inside ward number 1 (docs/08_TEST_PLAN.md sec. 2)
M_LAT = 0.0000090  # about 1 m of latitude
NOW = dt.datetime.now(dt.UTC).replace(microsecond=0)
FIXTURES = REPO_ROOT_DIR / "tests" / "fixtures" / "images"
HIDDEN = {"Water Leakage", "Blocked Drain", "Streetlight"}
ALL_8 = {"Pothole", "Road Damage", "Waterlogging", "Garbage Accumulation", "Other"} | HIDDEN


class FixedEmbedder:
    """Stands in for MiniLM: every candidate gets the same text similarity."""

    def __init__(self, similarity: float) -> None:
        self.similarity = similarity

    def similarities(self, text: str, others: Sequence[str]) -> list[float]:
        return [self.similarity for _ in others]


def _other_complaint(it, at, submitted, title: str, description: str) -> int:
    """An "Other" complaint stored like the intake API does: used capture session, GPS facts, ward/road/POI located."""
    user_id = it.new_user()
    cs = it._sql(
        "INSERT INTO capture_sessions (user_id, issued_at, expires_at) "
        "VALUES (:u, :t - interval '2 minutes', :t + interval '8 minutes') RETURNING capture_session_id",
        u=user_id, t=submitted,
    )[0]["capture_session_id"]
    with it.engine.begin() as conn:
        conn.execute(text("SELECT set_config('civicbrain.actor_role', 'CITIZEN', true), set_config('civicbrain.actor_user_id', :u, true)"),
                     {"u": str(user_id)})
        cid = conn.execute(
            text(
                "INSERT INTO complaints (user_id, category_id, title, description, location, location_source, location_accuracy_m, "
                "                        location_captured_at, submitted_at, capture_session_id, ward_id, road_id, poi_id) "
                "SELECT :u, (SELECT category_id FROM complaint_categories WHERE category_name = 'Other'), :title, :descr, "
                "       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 'BROWSER_GPS', 12, :sub - make_interval(secs => 40), :sub, :cs, "
                "       l.ward_id, l.road_id, l.poi_id "
                "  FROM fn_locate_point(:lat, :lon) l RETURNING complaint_id"
            ),
            {"u": user_id, "title": title, "descr": description, "lat": at[0], "lon": at[1], "sub": submitted, "cs": cs},
        ).scalar_one()
    it.complaint_ids.append(cid)
    it._sql("UPDATE capture_sessions SET used_at = :t, used_by_complaint_id = :c WHERE capture_session_id = :s", t=submitted, c=cid, s=cs)
    return cid


def _image(it, complaint_id: int) -> int:
    key = f"it/{uuid.uuid4().hex}.jpg"
    return it._sql(
        "INSERT INTO complaint_images (complaint_id, file_url, storage_key, image_role, sha256, phash, width_px, height_px) "
        "VALUES (:c, :url, :key, 'CITIZEN_EVIDENCE', :sha, :ph, 720, 720) RETURNING image_id",
        c=complaint_id, url=f"storage://{key}", key=key, sha=uuid.uuid4().hex + uuid.uuid4().hex,
        ph=au.to_signed64(random.Random(uuid.uuid4().int).getrandbits(64)),
    )[0]["image_id"]


def _category_of(it, complaint_id: int) -> tuple[str, str, str]:
    row = it._sql(
        "SELECT cc.category_name, cc.work_type_code, c.status FROM complaints c "
        "JOIN complaint_categories cc ON cc.category_id = c.category_id WHERE c.complaint_id = :c",
        c=complaint_id,
    )[0]
    return row["category_name"], row["work_type_code"], row["status"]


def _run_all_steps(ai_engine, cid: int, image_id: int, classifier: cl.TextClassifier, detection: de.DetectionResult,
                   embedder: du.Embedder):
    """The steps in pipeline order (docs/06 sec. 2), each in its own transaction like separate job steps."""
    with session_scope(ai_engine) as s:
        text_result = cl.classify_complaint(s, cid, classifier)
    with session_scope(ai_engine) as s:
        stored = de.write_detections(s, cid, image_id, detection, category_class_id=None)  # "Other" has no YOLO class
    with session_scope(ai_engine) as s:
        facts = au.load_facts(s, cid)
        class_conf = [(d.class_id, d.confidence) for d in detection.detections]
        checks = au.run_checks(facts) + [au.check_category_image_mismatch(facts.category_class_id, class_conf)]
        authenticity = au.write_results(s, cid, facts.image_id, checks)
    with session_scope(ai_engine) as s:
        priority = pr.assess_complaint(s, cid, as_of=NOW)
    with session_scope(ai_engine) as s:
        decision = du.find_duplicates(s, cid, embedder)
    return text_result, stored, facts, checks, authenticity, priority, decision


def _assert_other_rules(it, cid, facts, checks, priority) -> None:
    assert facts.category_class_id is None
    mismatch = next(c for c in checks if c.code == "CATEGORY_IMAGE_MISMATCH")
    assert (mismatch.result, mismatch.delta) == ("PASS", 0) and mismatch.details["reason"] == "category has no YOLO class"
    # no depth answer -> documented default severity MEDIUM 50, labelled ASSUMPTION; frozen weights unchanged
    severity = priority.explanation["factors"]["severity"]
    assert priority.scores["severity"] == 50
    assert severity["input"] == {"depthAnswer": None, "severityLevel": "MEDIUM", "assumption": True}
    assert any("other categories MEDIUM" in a for a in priority.explanation["assumptions"])
    assert {k: v["weight"] for k, v in priority.explanation["factors"].items()} == dict(PRIORITY_WEIGHTS)
    assert priority.level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    # nothing changed the citizen's category; MERGED/VERIFIED is the orchestrator's step (P12)
    assert _category_of(it, cid) == ("Other", "REVIEW_REQUIRED", "SUBMITTED")


def test_other_complaint_goes_through_every_step_and_keeps_its_category(it_data, ai_engine):
    earlier = _other_complaint(it_data, WARD1, NOW - dt.timedelta(hours=2), "Street light not working",
                               "The street light near the primary school has been dark for a week.")
    cid = _other_complaint(it_data, (WARD1[0] + 30 * M_LAT, WARD1[1]), NOW - dt.timedelta(minutes=5),
                           "Streetlight dark near school", "The street light close to the school is off every night.")
    image_id = _image(it_data, cid)
    texts = ["deep pothole on the road", "pothole near the school", "garbage heap not collected", "garbage dumped on corner",
             "street light is off", "streetlight dark at night", "loud music at night", "stray cattle on the road"]
    labels = ["Pothole", "Pothole", "Garbage Accumulation", "Garbage Accumulation", "Streetlight", "Streetlight", "Other", "Other"]
    classifier = cl.TextClassifier(build_pipeline(5.0).fit(texts, labels), "f" * 64)
    detection = de.DetectionResult([de.Detection(0, "Pothole", 0.62, 100.0, 120.0, 80.0, 60.0)], 720, 720, 80.0,
                                   "yolov8s_civicbrain", "abcdef123456")

    text_result, stored, facts, checks, authenticity, priority, decision = _run_all_steps(
        ai_engine, cid, image_id, classifier, detection, FixedEmbedder(0.95))

    # classify: the hidden category Streetlight is suggested - stored as a hint only
    assert text_result.predicted == "Streetlight"
    row = it_data._sql("SELECT predicted_category, is_accepted FROM ai_classifications WHERE complaint_id = :c AND model_type = 'TEXT'",
                       c=cid)[0]
    assert row["predicted_category"] == "Streetlight"
    assert row["is_accepted"] is (text_result.confidence < 0.70)  # a confident other category -> "possible wrong category" hint
    # detect: boxes stored, no own class -> no evidence either way
    assert stored.primary is None  # the primary detection needs the category's own class
    image_row = it_data._sql("SELECT is_accepted FROM ai_classifications WHERE complaint_id = :c AND model_type = 'IMAGE'", c=cid)
    assert len(image_row) == 1 and image_row[0]["is_accepted"] is None
    # authenticity: a normal score, "category has no YOLO class" passes
    assert authenticity[1] in {"PASSED", "FLAGGED"} and 0 <= authenticity[0] <= 100
    _assert_other_rules(it_data, cid, facts, checks, priority)
    # duplicates (frozen Step 12: distance, time, text - no category rule): the earlier "Other" report is the master
    assert (decision.status, decision.merge, decision.master_complaint_id) == ("DUPLICATE", True, earlier)


@pytest.mark.models
def test_other_complaint_with_the_installed_models(it_data, ai_engine):
    settings = get_settings()
    if not (settings.yolo_weights.is_file() and settings.text_embedding_model_dir.is_dir()
            and (settings.models_dir / "text_clf.joblib").is_file()):
        pytest.skip("models not installed (CI)")
    classifier = cl.get_classifier(settings)
    assert set(classifier.labels) == ALL_8  # the classifier stays 8-class (sanity metric 0.90 stays valid)
    cid = _other_complaint(it_data, WARD1, NOW - dt.timedelta(minutes=5), "Street light not working",
                           "The street light near the temple has been off for three nights, the road is dark.")
    image_id = _image(it_data, cid)
    detection = de.get_detector(settings).detect(FIXTURES / "road_damage_1.jpg")

    text_result, _stored, facts, checks, authenticity, priority, decision = _run_all_steps(
        ai_engine, cid, image_id, classifier, detection, du.get_embedder(settings))

    assert text_result.predicted in ALL_8
    assert 0 <= authenticity[0] <= 100
    _assert_other_rules(it_data, cid, facts, checks, priority)
    assert decision.merge is False  # no earlier complaint nearby
