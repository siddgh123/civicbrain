"""P08 pipeline modules against civicbrain_test (role civicbrain_ai): authenticity facts from PostGIS and
fn_similar_images, and the three writers (authenticity, TEXT classification, YOLO boxes + IMAGE row) are idempotent.

Fixture rows are inserted as the owner (it_data) with their own users/complaints/images and deleted afterwards.
"""

import datetime as dt
import random
import uuid

import pytest
from sqlalchemy import text

from app.db import session_scope
from pipeline import authenticity as au
from pipeline.classify import TextClassifier, classify_complaint
from pipeline.detect import Detection, DetectionResult, write_detections
from training.train_text_clf import build_pipeline

pytestmark = pytest.mark.integration

WARD1 = (18.7440, 73.6760)  # inside ward number 1 (docs/08_TEST_PLAN.md sec. 2)
DEPOT = (18.729411, 73.699489)  # D001, about 2.9 km from WARD1
NOW = dt.datetime.now(dt.UTC).replace(microsecond=0)


def _user(it, trust: float = 50) -> int:
    uid = it.new_user()
    it._sql("UPDATE users SET trust_score = :t WHERE user_id = :u", t=trust, u=uid)
    return uid


def _complaint(it, user_id: int, at=WARD1, submitted=NOW, *, category="Pothole", session=True, accuracy=12.0, captured_s_before=40) -> int:
    """A real SUBMITTED complaint with (optionally) a used capture session, like the intake API stores it."""
    cs = None
    if session:
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
                "                        location_captured_at, submitted_at, capture_session_id) "
                "VALUES (:u, (SELECT category_id FROM complaint_categories WHERE category_name = :cat), 'IT deep pothole', "
                "        'big pothole on the road near the school', ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 'BROWSER_GPS', :acc, "
                "        :sub - make_interval(secs => :before), :sub, :cs) RETURNING complaint_id"
            ),
            {"u": user_id, "cat": category, "lon": at[1], "lat": at[0], "acc": accuracy, "sub": submitted, "before": captured_s_before,
             "cs": cs},
        ).scalar_one()
    it.complaint_ids.append(cid)
    if cs is not None:
        it._sql("UPDATE capture_sessions SET used_at = :t, used_by_complaint_id = :c WHERE capture_session_id = :s",
                t=submitted, c=cid, s=cs)
    return cid


def _image(it, complaint_id: int, sha: str | None, phash: int | None) -> int:
    key = f"it/{uuid.uuid4().hex}.jpg"
    return it._sql(
        "INSERT INTO complaint_images (complaint_id, file_url, storage_key, image_role, sha256, phash, width_px, height_px) "
        "VALUES (:c, :url, :key, 'CITIZEN_EVIDENCE', :sha, :ph, 720, 720) RETURNING image_id",
        c=complaint_id, url=f"storage://{key}", key=key, sha=sha, ph=phash,
    )[0]["image_id"]


def _sha() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def _phash() -> int:
    return au.to_signed64(random.Random(uuid.uuid4().int).getrandbits(64))


def _rows(it, complaint_id: int) -> list[tuple]:
    rows = it._sql(
        "SELECT check_code, result, score_delta::float AS d, image_id, details "
        "FROM authenticity_checks WHERE complaint_id = :c ORDER BY check_code",
        c=complaint_id,
    )
    return [(r["check_code"], r["result"], r["d"], r["image_id"], r["details"]) for r in rows]


def test_reused_far_away_photo_is_flagged_and_rewriting_gives_the_same_rows(it_data, ai_engine):
    sha, ph = _sha(), _phash()
    other = _complaint(it_data, _user(it_data), at=DEPOT, submitted=NOW - dt.timedelta(hours=1))
    _image(it_data, other, sha, ph)
    cid = _complaint(it_data, _user(it_data, trust=80))
    image_id = _image(it_data, cid, sha, ph)

    with session_scope(ai_engine) as s:
        facts = au.load_facts(s, cid)
    assert facts.image_id == image_id and facts.category_class_id == 0
    assert facts.capture_session == au.CaptureSessionFacts(True, True, True, True, 0)
    assert facts.accuracy_m == 12.0 and (facts.submitted_at - facts.captured_at).total_seconds() == 40
    assert facts.inside_boundary is True and facts.edge_distance_m > 0
    assert facts.sha256_other_complaint_ids == [other]
    assert [(m.complaint_id, m.bits) for m in facts.phash_matches] == [(other, 0)]
    assert 2500 < facts.phash_matches[0].distance_m < 3500 and abs(facts.phash_matches[0].hours_apart - 1) < 0.01
    assert facts.complaints_24h == 1 and facts.previous_distance_m is None and facts.trust_score == 80

    results = au.run_checks(facts) + [au.check_category_image_mismatch(0, [(0, 0.8)])]
    for _ in range(2):  # the same job twice -> the same end state
        with session_scope(ai_engine) as s:
            score, status = au.write_results(s, cid, facts.image_id, results)
        assert (score, status) == (15, "FLAGGED")  # 100 - 50 (SHA-256) - 40 (pHash, far) + 5 (trust > 70)
    rows = _rows(it_data, cid)
    assert len(rows) == 10
    by_code = {r[0]: r for r in rows}
    assert by_code["IMAGE_REUSE_SHA256"][1:4] == ("FAIL", -50, image_id)
    assert by_code["IMAGE_REUSE_PHASH"][1:4] == ("FAIL", -40, image_id)
    assert by_code["CATEGORY_IMAGE_MISMATCH"][3] == image_id and by_code["GPS_ACCURACY"][3] is None
    assert by_code["IMAGE_REUSE_PHASH"][4]["otherComplaintId"] == other
    c = it_data._sql("SELECT authenticity_score::float AS s, authenticity_status AS st FROM complaints WHERE complaint_id = :c", c=cid)[0]
    assert (c["s"], c["st"]) == (15, "FLAGGED")

    # an officer's REJECTED (fake) decision survives a re-analysis
    it_data._sql("UPDATE complaints SET authenticity_status = 'REJECTED' WHERE complaint_id = :c", c=cid)
    with session_scope(ai_engine) as s:
        au.write_results(s, cid, facts.image_id, results)
    assert it_data._sql("SELECT authenticity_status FROM complaints WHERE complaint_id = :c", c=cid)[0]["authenticity_status"] == "REJECTED"
    assert _rows(it_data, cid) == rows


def test_rate_travel_and_nearby_photo_hint_from_the_database(it_data, ai_engine):
    uid = _user(it_data)
    for minutes in (300, 200, 100):
        _complaint(it_data, uid, submitted=NOW - dt.timedelta(minutes=minutes), session=False)
    # 4th complaint in 24 h, 60 s after the 3rd one but 2.9 km away
    cid = _complaint(it_data, uid, at=DEPOT, submitted=NOW - dt.timedelta(minutes=99))
    ph = _phash()
    _image(it_data, cid, _sha(), ph)
    neighbour = _complaint(it_data, _user(it_data), at=(DEPOT[0] + 0.0005, DEPOT[1]), submitted=NOW - dt.timedelta(hours=3))
    _image(it_data, neighbour, _sha(), ph ^ 0b101)  # 2 bits apart, ~55 m away, 81 minutes earlier

    with session_scope(ai_engine) as s:
        facts = au.load_facts(s, cid)
    assert facts.complaints_24h == 4
    assert 2500 < facts.previous_distance_m < 3500 and facts.previous_seconds == 60  # GPS fix times, both 40 s before submit
    by_code = {r.code: r for r in au.run_checks(facts)}
    assert (by_code["SUBMISSION_RATE"].result, by_code["SUBMISSION_RATE"].delta) == ("WARN", -10)
    assert (by_code["IMPOSSIBLE_TRAVEL"].result, by_code["IMPOSSIBLE_TRAVEL"].delta) == ("WARN", -20)
    assert by_code["IMAGE_REUSE_PHASH"].result == "PASS"
    assert by_code["IMAGE_REUSE_PHASH"].details["duplicateHintComplaintIds"] == [neighbour]
    assert by_code["IMAGE_REUSE_SHA256"].result == "PASS"


def test_point_near_the_boundary_edge_warns_and_missing_session_fails(it_data, ai_engine):
    near = it_data._sql(
        """
        WITH p AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS g),
             e AS (SELECT ST_ClosestPoint(ST_Boundary(b.geometry), p.g) AS ep, p.g
                     FROM municipal_boundary b, p WHERE b.status IN ('VERIFIED', 'ACTIVE') LIMIT 1)
        SELECT ST_Y(q) AS lat, ST_X(q) AS lon
          FROM (SELECT ST_LineInterpolatePoint(ST_MakeLine(ep, g), 20.0 / ST_Distance(ep::geography, g::geography)) AS q FROM e) x
        """,
        lat=WARD1[0], lon=WARD1[1],
    )[0]
    cid = _complaint(it_data, _user(it_data, trust=20), at=(near["lat"], near["lon"]), session=False, accuracy=80.0, captured_s_before=300)
    with session_scope(ai_engine) as s:
        facts = au.load_facts(s, cid)
    assert facts.inside_boundary is True and 15 < facts.edge_distance_m <= 21
    by_code = {r.code: (r.result, r.delta) for r in au.run_checks(facts)}
    assert by_code == {
        "CAPTURE_SESSION": ("FAIL", 0),
        "GPS_ACCURACY": ("WARN", -10),
        "GPS_FRESHNESS": ("WARN", -10),
        "BOUNDARY": ("WARN", -5),
        "IMAGE_REUSE_SHA256": ("WARN", 0),  # no photo
        "IMAGE_REUSE_PHASH": ("WARN", 0),
        "SUBMISSION_RATE": ("PASS", 0),
        "IMPOSSIBLE_TRAVEL": ("PASS", 0),
        "ACCOUNT_TRUST": ("WARN", -15),
    }
    assert facts.image_id is None
    with session_scope(ai_engine) as s:
        assert au.write_results(s, cid, None, au.run_checks(facts) + [au.check_category_image_mismatch(0, None)]) == (60, "PASSED")


def test_text_classification_row_is_written_once_per_model_version(it_data, ai_engine):
    texts = ["deep pothole on road", "pothole near school", "garbage heap", "garbage not collected", "street light off", "dark light"]
    labels = ["Pothole", "Pothole", "Garbage Accumulation", "Garbage Accumulation", "Streetlight", "Streetlight"]
    clf = TextClassifier(build_pipeline(5.0).fit(texts, labels), "e" * 64)
    # V6: citizens can no longer choose Streetlight, so the stored complaint uses a selectable category (the classifier
    # itself stays 8-class: Streetlight remains one of its labels)
    cid = _complaint(it_data, _user(it_data), category="Garbage Accumulation", session=False)
    for _ in range(2):
        with session_scope(ai_engine) as s:
            result = classify_complaint(s, cid, clf)
    assert result.predicted == "Pothole"
    rows = it_data._sql(
        "SELECT a.predicted_category, cc.category_name, a.confidence::float AS conf, a.model_name, a.model_version, a.top_k, a.is_accepted "
        "FROM ai_classifications a LEFT JOIN complaint_categories cc ON cc.category_id = a.predicted_category_id "
        "WHERE a.complaint_id = :c AND a.model_type = 'TEXT'",
        c=cid,
    )
    assert len(rows) == 1
    row = rows[0]
    assert (row["predicted_category"], row["category_name"], row["model_name"], row["model_version"]) == (
        "Pothole", "Pothole", "text_clf_tfidf_lr", "e" * 12)
    assert row["conf"] == result.confidence and [t["category"] for t in row["top_k"]] == [c for c, _ in result.top]
    assert row["is_accepted"] is (result.confidence < 0.70)  # citizen said Garbage: a confident Pothole is a mismatch


def test_yolo_boxes_and_image_row_are_rewritten_not_added(it_data, ai_engine):
    cid = _complaint(it_data, _user(it_data), session=False)
    image_id = _image(it_data, cid, _sha(), _phash())
    dets = [
        Detection(0, "Pothole", 0.81, 100.5, 200.25, 60.0, 40.0),
        Detection(3, "Road Damage", 0.55, 0.0, 300.0, 700.0, 120.5),
        Detection(0, "Pothole", 0.33, 400.0, 410.0, 30.0, 20.0),
    ]
    result = DetectionResult(dets, 720, 720, 90.0, "yolov8s_civicbrain", "abcdef123456")
    for _ in range(2):
        with session_scope(ai_engine) as s:
            stored = write_detections(s, cid, image_id, result, category_class_id=0)
    boxes = it_data._sql(
        "SELECT detection_id, detected_class, confidence::float AS c, bbox_x::float AS x, bbox_width::float AS w, model_version "
        "FROM yolo_detections WHERE image_id = :i ORDER BY detection_id",
        i=image_id,
    )
    assert [(b["detected_class"], b["c"], b["x"], b["w"]) for b in boxes] == [
        ("Pothole", 0.81, 100.5, 60.0), ("Road Damage", 0.55, 0.0, 700.0), ("Pothole", 0.33, 400.0, 30.0)]
    assert {b["model_version"] for b in boxes} == {"abcdef123456"}
    assert stored.primary == dets[0] and stored.primary_detection_id == boxes[0]["detection_id"]
    image_rows = it_data._sql(
        "SELECT a.predicted_category, cc.yolo_class_id, a.confidence::float AS c, a.top_k, a.is_accepted "
        "FROM ai_classifications a JOIN complaint_categories cc ON cc.category_id = a.predicted_category_id "
        "WHERE a.complaint_id = :c AND a.model_type = 'IMAGE'",
        c=cid,
    )
    assert len(image_rows) == 1
    assert (image_rows[0]["predicted_category"], image_rows[0]["yolo_class_id"], image_rows[0]["c"]) == ("Pothole", 0, 0.81)
    assert image_rows[0]["is_accepted"] is True
    assert [t["category"] for t in image_rows[0]["top_k"]] == ["Pothole", "Road Damage"]
