"""pipeline/authenticity.py: one test per row of docs/06_AI_PIPELINE.md sec. 2.1 (PASS/WARN/FAIL + delta), clamp,
FLAGGED threshold, nearby & recent pHash = duplicate hint (PASS), pHash as signed int64."""

import datetime as dt
from pathlib import Path

import imagehash
import pytest
from PIL import Image

from pipeline import authenticity as au
from pipeline.authenticity import AuthFacts, CaptureSessionFacts, CheckResult, PhashMatch

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "images"
T0 = dt.datetime(2026, 10, 3, 10, 0, tzinfo=dt.UTC)


def rd(r: CheckResult) -> tuple[str, float]:
    return r.result, r.delta


# ------------------------------------------------------------------ CAPTURE_SESSION
VALID_SESSION = CaptureSessionFacts(
    present=True, belongs_to_user=True, used_by_this_complaint=True, used_before_expiry=True, other_complaints=0
)


def test_capture_session_valid_and_used_once_passes():
    assert rd(au.check_capture_session(VALID_SESSION)) == ("PASS", 0)


@pytest.mark.parametrize(
    "facts",
    [
        CaptureSessionFacts(False, False, False, False, 0),
        CaptureSessionFacts(present=True, belongs_to_user=False, used_by_this_complaint=True, used_before_expiry=True, other_complaints=0),
        CaptureSessionFacts(present=True, belongs_to_user=True, used_by_this_complaint=False, used_before_expiry=True, other_complaints=0),
        CaptureSessionFacts(present=True, belongs_to_user=True, used_by_this_complaint=True, used_before_expiry=False, other_complaints=0),
        CaptureSessionFacts(present=True, belongs_to_user=True, used_by_this_complaint=True, used_before_expiry=True, other_complaints=1),
    ],
    ids=["missing", "other-user", "not-used-by-this", "used-after-expiry", "used-twice"],
)
def test_capture_session_problem_is_fail_without_a_delta(facts):
    # the API already rejects these; the table gives no delta, so FAIL is recorded with 0 for the officer
    assert rd(au.check_capture_session(facts)) == ("FAIL", 0)


# ------------------------------------------------------------------ GPS_ACCURACY
@pytest.mark.parametrize(
    "acc,expected",
    [(5, ("PASS", 0)), (50, ("PASS", 0)), (50.01, ("WARN", -10)), (150, ("WARN", -10)), (150.5, ("FAIL", -10)), (None, ("SKIPPED", 0))],
)
def test_gps_accuracy(acc, expected):
    assert rd(au.check_gps_accuracy(acc)) == expected


# ------------------------------------------------------------------ GPS_FRESHNESS
@pytest.mark.parametrize(
    "seconds,expected",
    [(0, ("PASS", 0)), (120, ("PASS", 0)), (121, ("WARN", -10)), (600, ("WARN", -10)), (601, ("FAIL", -10)), (-30, ("PASS", 0))],
)
def test_gps_freshness(seconds, expected):
    submitted = T0 + dt.timedelta(seconds=seconds)
    assert rd(au.check_gps_freshness(T0, submitted)) == expected


def test_gps_freshness_without_capture_time_is_skipped():
    assert rd(au.check_gps_freshness(None, T0)) == ("SKIPPED", 0)


# ------------------------------------------------------------------ BOUNDARY
@pytest.mark.parametrize(
    "inside,edge,expected",
    [
        (True, 1200.0, ("PASS", 0)), (True, 50.5, ("PASS", 0)), (True, 50.0, ("WARN", -5)), (True, 3.0, ("WARN", -5)),
        (False, 20.0, ("FAIL", -5)), (None, None, ("SKIPPED", 0)),
    ],
)
def test_boundary(inside, edge, expected):
    assert rd(au.check_boundary(inside, edge)) == expected


# ------------------------------------------------------------------ IMAGE_REUSE_SHA256
def test_sha256_unique_passes():
    assert rd(au.check_image_reuse_sha256(True, [])) == ("PASS", 0)


def test_sha256_on_another_complaint_fails_minus_50():
    r = au.check_image_reuse_sha256(True, [17, 23])
    assert rd(r) == ("FAIL", -50)
    assert r.details["otherComplaintIds"] == [17, 23]


def test_sha256_without_image_warns_without_delta():
    assert rd(au.check_image_reuse_sha256(False, [])) == ("WARN", 0)


# ------------------------------------------------------------------ IMAGE_REUSE_PHASH
def m(bits: int, distance_m: float, hours: float, cid: int = 9) -> PhashMatch:
    return PhashMatch(complaint_id=cid, image_id=cid * 10, bits=bits, distance_m=distance_m, hours_apart=hours)


@pytest.mark.parametrize(
    "matches,expected",
    [
        ([], ("PASS", 0)),  # nothing <= 10 bits
        ([m(11, 5000, 500)], ("PASS", 0)),  # > 10 bits is not similar
        ([m(4, 301, 1)], ("FAIL", -40)),  # <= 4 bits, far away
        ([m(0, 10, 169)], ("FAIL", -40)),  # <= 4 bits, > 7 days apart
        ([m(5, 301, 1)], ("WARN", -15)),  # 5-10 bits, far away
        ([m(10, 20, 200)], ("WARN", -15)),  # 5-10 bits, long ago
        ([m(4, 300, 168)], ("PASS", 0)),  # <= 4 bits nearby & recent = duplicate hint
        ([m(8, 120, 2)], ("PASS", 0)),  # 5-10 bits nearby & recent: same place, also only a hint
        ([m(2, 50, 3, cid=1), m(7, 900, 3, cid=2)], ("WARN", -15)),  # the worst match counts
        ([m(7, 900, 3, cid=1), m(3, 2000, 3, cid=2)], ("FAIL", -40)),
    ],
)
def test_phash_reuse(matches, expected):
    assert rd(au.check_image_reuse_phash(True, matches)) == expected


def test_phash_nearby_and_recent_is_a_duplicate_hint():
    r = au.check_image_reuse_phash(True, [m(3, 80, 5, cid=41)])
    assert rd(r) == ("PASS", 0)
    assert r.details["duplicateHintComplaintIds"] == [41]


def test_phash_without_image_warns_without_delta():
    assert rd(au.check_image_reuse_phash(False, [])) == ("WARN", 0)


# ------------------------------------------------------------------ SUBMISSION_RATE
@pytest.mark.parametrize("count,expected", [(1, ("PASS", 0)), (3, ("PASS", 0)), (4, ("WARN", -10)), (5, ("WARN", -10)), (9, ("WARN", -10))])
def test_submission_rate(count, expected):
    assert rd(au.check_submission_rate(count)) == expected


# ------------------------------------------------------------------ IMPOSSIBLE_TRAVEL
@pytest.mark.parametrize(
    "distance_m,seconds,expected",
    [
        (None, None, ("PASS", 0)),  # first complaint of the user
        (150_000, 3600, ("PASS", 0)),  # exactly 150 km/h
        (151_000, 3600, ("WARN", -20)),
        (3_000, 60, ("WARN", -20)),  # 180 km/h
        (300, 60, ("PASS", 0)),
        (0, 0, ("PASS", 0)),
        (10, 0, ("WARN", -20)),  # moved in no time
    ],
)
def test_impossible_travel(distance_m, seconds, expected):
    assert rd(au.check_impossible_travel(distance_m, seconds)) == expected


# ------------------------------------------------------------------ ACCOUNT_TRUST
@pytest.mark.parametrize(
    "trust,expected",
    [
        (0, ("WARN", -15)), (29.99, ("WARN", -15)), (30, ("PASS", 0)), (50, ("PASS", 0)), (70, ("PASS", 0)),
        (70.01, ("PASS", 5)), (100, ("PASS", 5)),
    ],
)
def test_account_trust(trust, expected):
    assert rd(au.check_account_trust(trust)) == expected


# ------------------------------------------------------------------ CATEGORY_IMAGE_MISMATCH
@pytest.mark.parametrize(
    "class_id,dets,expected",
    [
        (None, [(1, 0.9)], ("PASS", 0)),  # category without a YOLO class
        (0, [(0, 0.4)], ("PASS", 0)),  # own class >= 0.4
        (0, [(0, 0.41), (1, 0.95)], ("PASS", 0)),
        (0, [(1, 0.5)], ("WARN", -10)),  # only other classes >= 0.5
        (0, [(0, 0.39), (3, 0.6)], ("WARN", -10)),
        (0, [(1, 0.49)], ("PASS", 0)),  # no evidence either way
        (0, [], ("PASS", 0)),  # nothing detected (measurement falls back to Tier C)
        (0, None, ("SKIPPED", 0)),  # detection did not run (image missing)
    ],
)
def test_category_image_mismatch(class_id, dets, expected):
    assert rd(au.check_category_image_mismatch(class_id, dets)) == expected


# ------------------------------------------------------------------ score
def _r(delta: float) -> CheckResult:
    return CheckResult("GPS_ACCURACY", "WARN" if delta < 0 else "PASS", delta, {})


def test_score_starts_at_100_and_clamps():
    assert au.final_score([]) == (100, "PASSED")
    assert au.final_score([_r(5)]) == (100, "PASSED")  # trust bonus cannot go above 100
    assert au.final_score([_r(-50), _r(-40), _r(-20), _r(-15), _r(-10)]) == (0, "FLAGGED")  # -135 -> 0


def test_flagged_below_40():
    assert au.final_score([_r(-40), _r(-20)]) == (40, "PASSED")
    assert au.final_score([_r(-50), _r(-15)]) == (35, "FLAGGED")
    assert au.final_score([_r(-50), _r(-10), _r(5)]) == (45, "PASSED")


def _facts(**overrides) -> AuthFacts:
    base = dict(
        complaint_id=1, user_id=2, image_id=3, category_class_id=0, capture_session=VALID_SESSION,
        accuracy_m=12.0, captured_at=T0, submitted_at=T0 + dt.timedelta(seconds=40),
        inside_boundary=True, edge_distance_m=800.0, sha256_present=True, phash_present=True,
        sha256_other_complaint_ids=[], phash_matches=[],
        complaints_24h=1, previous_distance_m=None, previous_seconds=None, trust_score=50.0,
    )
    base.update(overrides)
    return AuthFacts(**base)


def test_run_checks_gives_the_nine_pre_yolo_checks_in_table_order():
    results = au.run_checks(_facts())
    assert [r.code for r in results] == [
        "CAPTURE_SESSION", "GPS_ACCURACY", "GPS_FRESHNESS", "BOUNDARY", "IMAGE_REUSE_SHA256", "IMAGE_REUSE_PHASH",
        "SUBMISSION_RATE", "IMPOSSIBLE_TRAVEL", "ACCOUNT_TRUST",
    ]
    assert {r.result for r in results} == {"PASS"}
    assert au.final_score(results) == (100, "PASSED")


def test_a_reused_far_away_photo_is_flagged():
    results = au.run_checks(_facts(sha256_other_complaint_ids=[7], phash_matches=[m(0, 5000, 2, cid=7)]))
    assert au.final_score(results) == (10, "FLAGGED")  # -50 -40


def test_every_check_code_is_allowed_by_the_db():
    allowed = {"BOUNDARY", "GPS_ACCURACY", "GPS_FRESHNESS", "CAPTURE_SESSION", "IMAGE_REUSE_SHA256", "IMAGE_REUSE_PHASH",
               "EXIF_CONSISTENCY", "SUBMISSION_RATE", "IMPOSSIBLE_TRAVEL", "ACCOUNT_TRUST", "CATEGORY_IMAGE_MISMATCH"}
    results = au.run_checks(_facts()) + [au.check_category_image_mismatch(0, [])]
    assert {r.code for r in results} <= allowed
    assert {r.result for r in results} <= {"PASS", "WARN", "FAIL", "SKIPPED"}


# ------------------------------------------------------------------ pHash (imagehash.phash 64-bit -> signed int64)
def test_to_signed64():
    assert au.to_signed64(0) == 0
    assert au.to_signed64(0x7FFFFFFFFFFFFFFF) == 2**63 - 1
    assert au.to_signed64(0x8000000000000000) == -(2**63)
    assert au.to_signed64(0xFFFFFFFFFFFFFFFF) == -1


def test_phash_int64_matches_imagehash_and_the_db_distance():
    with Image.open(FIXTURES / "pothole_1.jpg") as img:
        value = au.phash_int64(img)
        expected = imagehash.phash(img)
        smaller = au.phash_int64(img.resize((360, 360)))
    assert -(2**63) <= value < 2**63
    assert value == au.to_signed64(int(str(expected), 16))
    assert au.hamming_bits(value, value) == 0
    assert au.hamming_bits(value, smaller) <= 4  # a resized copy is still the "same" photo
    with Image.open(FIXTURES / "garbage_1.jpg") as other:
        assert au.hamming_bits(value, au.phash_int64(other)) > 10
    # same rule as fn_phash_distance: bit_count((a # b)::bit(64))
    assert au.hamming_bits(-1, 0) == 64 and au.hamming_bits(-(2**63), 0) == 1
