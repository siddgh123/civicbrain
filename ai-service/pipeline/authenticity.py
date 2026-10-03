"""Authenticity checks - ANALYZE_COMPLAINT steps 2 and 4b (docs/06_AI_PIPELINE.md sec. 2.1, FR-20).

Score starts at 100, every check adds its delta, clamp 0-100; < 40 -> FLAGGED, else PASSED. The officer decides
(a FLAGGED complaint is never rejected automatically). Thresholds and deltas live in app/config.py.

    facts   = load_facts(session, complaint_id)            # small DB queries (PostGIS, fn_similar_images)
    results = run_checks(facts)                            # step 2: pure functions, all checks except the next one
    results.append(check_category_image_mismatch(...))     # step 4b: after YOLO
    score, status = write_results(session, complaint_id, facts.image_id, results)

Cases the table marks "(API already rejects)" are not expected here; if one still arrives (data that bypassed the
API) it is recorded as FAIL with the row's WARN delta (CAPTURE_SESSION: no delta in the table -> 0), so the officer
sees it and no new number is invented. A check without its input (no accuracy, no capture time, no boundary row) is
SKIPPED with delta 0; a missing/unreadable photo makes the two image-reuse checks WARN with delta 0 (06 sec. 2 step 1).
"""

from __future__ import annotations

import datetime as dt
import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import imagehash
from PIL import Image
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import (
    AUTH_FLAGGED_BELOW,
    AUTH_START_SCORE,
    BOUNDARY_EDGE_WARN_M,
    BOUNDARY_EDGE_WARN_PENALTY,
    CATEGORY_MATCH_MIN_CONF,
    CATEGORY_MISMATCH_PENALTY,
    CATEGORY_OTHER_CLASS_MIN_CONF,
    GPS_ACCURACY_PASS_MAX_M,
    GPS_ACCURACY_WARN_MAX_M,
    GPS_ACCURACY_WARN_PENALTY,
    GPS_FRESHNESS_PASS_MAX_MIN,
    GPS_FRESHNESS_WARN_MAX_MIN,
    GPS_FRESHNESS_WARN_PENALTY,
    IMAGE_REUSE_SHA256_PENALTY,
    IMPOSSIBLE_TRAVEL_MAX_KMH,
    IMPOSSIBLE_TRAVEL_PENALTY,
    PHASH_FAIL_MAX_BITS,
    PHASH_FAIL_PENALTY,
    PHASH_FAR_M,
    PHASH_LONG_AGO_DAYS,
    PHASH_WARN_MAX_BITS,
    PHASH_WARN_PENALTY,
    SUBMISSION_RATE_PASS_MAX_24H,
    SUBMISSION_RATE_WARN_PENALTY,
    TRUST_HIGH_ABOVE,
    TRUST_HIGH_BONUS,
    TRUST_LOW_BELOW,
    TRUST_LOW_PENALTY,
)
from app.errors import DataError

IMAGE_CHECKS = frozenset({"IMAGE_REUSE_SHA256", "IMAGE_REUSE_PHASH", "CATEGORY_IMAGE_MISMATCH"})  # rows carry image_id
MAX_IDS_IN_DETAILS = 10


@dataclass(frozen=True)
class CheckResult:
    code: str
    result: str  # PASS / WARN / FAIL / SKIPPED (authenticity_checks.result)
    delta: float
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureSessionFacts:
    present: bool
    belongs_to_user: bool
    used_by_this_complaint: bool
    used_before_expiry: bool
    other_complaints: int  # other complaints that reference the same session


@dataclass(frozen=True)
class PhashMatch:
    complaint_id: int
    image_id: int
    bits: int
    distance_m: float
    hours_apart: float


@dataclass(frozen=True)
class AuthFacts:
    complaint_id: int
    user_id: int
    image_id: int | None  # the citizen evidence photo
    category_class_id: int | None
    capture_session: CaptureSessionFacts
    accuracy_m: float | None
    captured_at: dt.datetime | None
    submitted_at: dt.datetime
    inside_boundary: bool | None
    edge_distance_m: float | None
    sha256_present: bool
    phash_present: bool
    sha256_other_complaint_ids: list[int]
    phash_matches: list[PhashMatch]
    complaints_24h: int
    previous_distance_m: float | None  # None = first complaint of the user
    previous_seconds: float | None
    trust_score: float


def _r(code: str, result: str, delta: float = 0, **details: object) -> CheckResult:
    return CheckResult(code, result, float(delta), {k: v for k, v in details.items() if v is not None})


# =============================================================================================================
# Pure checks (one per row of docs/06 sec. 2.1)
# =============================================================================================================
def check_capture_session(cs: CaptureSessionFacts) -> CheckResult:
    if not cs.present:
        return _r("CAPTURE_SESSION", "FAIL", reason="no capture session")
    problems = [
        name
        for name, bad in (
            ("session of another user", not cs.belongs_to_user),
            ("not marked as used by this complaint", not cs.used_by_this_complaint),
            ("used after it expired", not cs.used_before_expiry),
            ("also used by another complaint", cs.other_complaints > 0),
        )
        if bad
    ]
    if problems:
        return _r("CAPTURE_SESSION", "FAIL", reason="; ".join(problems))
    return _r("CAPTURE_SESSION", "PASS")


def check_gps_accuracy(accuracy_m: float | None) -> CheckResult:
    if accuracy_m is None:
        return _r("GPS_ACCURACY", "SKIPPED", reason="no accuracy value")
    acc = round(float(accuracy_m), 1)
    if accuracy_m <= GPS_ACCURACY_PASS_MAX_M:
        return _r("GPS_ACCURACY", "PASS", accuracyM=acc)
    if accuracy_m <= GPS_ACCURACY_WARN_MAX_M:
        return _r("GPS_ACCURACY", "WARN", -GPS_ACCURACY_WARN_PENALTY, accuracyM=acc)
    return _r("GPS_ACCURACY", "FAIL", -GPS_ACCURACY_WARN_PENALTY, accuracyM=acc)


def check_gps_freshness(captured_at: dt.datetime | None, submitted_at: dt.datetime) -> CheckResult:
    if captured_at is None:
        return _r("GPS_FRESHNESS", "SKIPPED", reason="no capture time")
    minutes = (submitted_at - captured_at).total_seconds() / 60
    shown = round(minutes, 2)
    if minutes <= GPS_FRESHNESS_PASS_MAX_MIN:  # a phone clock slightly ahead gives a negative age: still fresh
        return _r("GPS_FRESHNESS", "PASS", minutesBeforeSubmit=shown)
    if minutes <= GPS_FRESHNESS_WARN_MAX_MIN:
        return _r("GPS_FRESHNESS", "WARN", -GPS_FRESHNESS_WARN_PENALTY, minutesBeforeSubmit=shown)
    return _r("GPS_FRESHNESS", "FAIL", -GPS_FRESHNESS_WARN_PENALTY, minutesBeforeSubmit=shown)


def check_boundary(inside: bool | None, edge_distance_m: float | None) -> CheckResult:
    if inside is None:
        return _r("BOUNDARY", "SKIPPED", reason="no verified municipal boundary")
    edge = round(float(edge_distance_m), 1) if edge_distance_m is not None else None
    if not inside:
        return _r("BOUNDARY", "FAIL", -BOUNDARY_EDGE_WARN_PENALTY, edgeDistanceM=edge, reason="outside the TDMC boundary")
    if edge_distance_m is not None and edge_distance_m <= BOUNDARY_EDGE_WARN_M:
        return _r("BOUNDARY", "WARN", -BOUNDARY_EDGE_WARN_PENALTY, edgeDistanceM=edge)
    return _r("BOUNDARY", "PASS", edgeDistanceM=edge)


def check_image_reuse_sha256(sha256_present: bool, other_complaint_ids: Sequence[int]) -> CheckResult:
    if not sha256_present:
        return _r("IMAGE_REUSE_SHA256", "WARN", reason="photo missing or unreadable")
    if other_complaint_ids:
        others = list(other_complaint_ids)[:MAX_IDS_IN_DETAILS]
        return _r("IMAGE_REUSE_SHA256", "FAIL", -IMAGE_REUSE_SHA256_PENALTY, otherComplaintIds=others)
    return _r("IMAGE_REUSE_SHA256", "PASS")


def _nearby_and_recent(match: PhashMatch) -> bool:
    return match.distance_m <= PHASH_FAR_M and match.hours_apart <= PHASH_LONG_AGO_DAYS * 24


def check_image_reuse_phash(phash_present: bool, matches: Sequence[PhashMatch]) -> CheckResult:
    """Similar photo on ANOTHER complaint. Nearby (<= 300 m) and recent (<= 7 days) = the same defect reported
    again -> duplicate hint, PASS (the duplicate step decides). Far away or long ago -> reuse: <= 4 bits FAIL -40,
    5-10 bits WARN -15. The worst match decides."""
    if not phash_present:
        return _r("IMAGE_REUSE_PHASH", "WARN", reason="photo missing or unreadable")
    similar = [mt for mt in matches if mt.bits <= PHASH_WARN_MAX_BITS]
    hints = sorted({mt.complaint_id for mt in similar if _nearby_and_recent(mt)})
    reused = [mt for mt in similar if not _nearby_and_recent(mt)]
    hint_ids = hints[:MAX_IDS_IN_DETAILS] or None
    if not reused:
        return _r("IMAGE_REUSE_PHASH", "PASS", duplicateHintComplaintIds=hint_ids)
    worst = min(reused, key=lambda mt: (mt.bits, -mt.distance_m))
    evidence = {"otherComplaintId": worst.complaint_id, "bits": worst.bits, "distanceM": round(worst.distance_m, 1),
                "daysApart": round(worst.hours_apart / 24, 1)}
    if worst.bits <= PHASH_FAIL_MAX_BITS:
        return _r("IMAGE_REUSE_PHASH", "FAIL", -PHASH_FAIL_PENALTY, **evidence, duplicateHintComplaintIds=hint_ids)
    return _r("IMAGE_REUSE_PHASH", "WARN", -PHASH_WARN_PENALTY, **evidence, duplicateHintComplaintIds=hint_ids)


def check_submission_rate(count_24h: int) -> CheckResult:
    """Complaints of the user in the 24 h up to this one (this one included). The table has no FAIL: > 5 stays WARN."""
    if count_24h <= SUBMISSION_RATE_PASS_MAX_24H:
        return _r("SUBMISSION_RATE", "PASS", complaintsIn24h=count_24h)
    return _r("SUBMISSION_RATE", "WARN", -SUBMISSION_RATE_WARN_PENALTY, complaintsIn24h=count_24h)


def check_impossible_travel(distance_m: float | None, seconds: float | None) -> CheckResult:
    if distance_m is None or seconds is None:
        return _r("IMPOSSIBLE_TRAVEL", "PASS", reason="first complaint of this user")
    if seconds <= 0:
        speed = math.inf if distance_m > 0 else 0.0
    else:
        speed = (distance_m / 1000) / (seconds / 3600)
    shown = None if math.isinf(speed) else round(speed, 1)
    details = {"distanceM": round(float(distance_m), 1), "minutes": round(seconds / 60, 2), "speedKmh": shown}
    if speed > IMPOSSIBLE_TRAVEL_MAX_KMH:
        return _r("IMPOSSIBLE_TRAVEL", "WARN", -IMPOSSIBLE_TRAVEL_PENALTY, **details)
    return _r("IMPOSSIBLE_TRAVEL", "PASS", **details)


def check_account_trust(trust_score: float) -> CheckResult:
    trust = round(float(trust_score), 2)
    if trust_score < TRUST_LOW_BELOW:
        return _r("ACCOUNT_TRUST", "WARN", -TRUST_LOW_PENALTY, trustScore=trust)
    if trust_score > TRUST_HIGH_ABOVE:
        return _r("ACCOUNT_TRUST", "PASS", TRUST_HIGH_BONUS, trustScore=trust)
    return _r("ACCOUNT_TRUST", "PASS", trustScore=trust)


def category_image_evidence(class_conf: Iterable[tuple[int, float]], category_class_id: int | None) -> str:
    """NO_CLASS (category without YOLO class) / MATCH (own class >= 0.4) / OTHER_CLASS (only other classes >= 0.5)
    / NO_EVIDENCE (anything else, incl. no detection)."""
    if category_class_id is None:
        return "NO_CLASS"
    pairs = list(class_conf)
    if any(k == category_class_id and c >= CATEGORY_MATCH_MIN_CONF for k, c in pairs):
        return "MATCH"
    if any(k != category_class_id and c >= CATEGORY_OTHER_CLASS_MIN_CONF for k, c in pairs):
        return "OTHER_CLASS"
    return "NO_EVIDENCE"


def check_category_image_mismatch(category_class_id: int | None, class_conf: Iterable[tuple[int, float]] | None) -> CheckResult:
    """Step 4b. class_conf = (yolo class id, confidence) of every detection; None = detection did not run."""
    if category_class_id is None:
        return _r("CATEGORY_IMAGE_MISMATCH", "PASS", reason="category has no YOLO class")
    if class_conf is None:
        return _r("CATEGORY_IMAGE_MISMATCH", "SKIPPED", reason="no detection run (photo missing or unreadable)")
    pairs = list(class_conf)
    evidence = category_image_evidence(pairs, category_class_id)
    best_own = max((c for k, c in pairs if k == category_class_id), default=None)
    best_other = max((c for k, c in pairs if k != category_class_id), default=None)
    if evidence == "OTHER_CLASS":
        return _r("CATEGORY_IMAGE_MISMATCH", "WARN", -CATEGORY_MISMATCH_PENALTY, bestOwnClassConf=best_own, bestOtherClassConf=best_other)
    return _r("CATEGORY_IMAGE_MISMATCH", "PASS", evidence=evidence, bestOwnClassConf=best_own, bestOtherClassConf=best_other)


def run_checks(f: AuthFacts) -> list[CheckResult]:
    """Step 2: every check except CATEGORY_IMAGE_MISMATCH, in table order. Each check is independent."""
    return [
        check_capture_session(f.capture_session),
        check_gps_accuracy(f.accuracy_m),
        check_gps_freshness(f.captured_at, f.submitted_at),
        check_boundary(f.inside_boundary, f.edge_distance_m),
        check_image_reuse_sha256(f.sha256_present, f.sha256_other_complaint_ids),
        check_image_reuse_phash(f.phash_present, f.phash_matches),
        check_submission_rate(f.complaints_24h),
        check_impossible_travel(f.previous_distance_m, f.previous_seconds),
        check_account_trust(f.trust_score),
    ]


def final_score(results: Iterable[CheckResult]) -> tuple[float, str]:
    score = max(0.0, min(100.0, AUTH_START_SCORE + sum(r.delta for r in results)))
    return score, ("FLAGGED" if score < AUTH_FLAGGED_BELOW else "PASSED")


# =============================================================================================================
# pHash: imagehash.phash (64 bits) stored as signed int64 (complaint_images.phash bigint)
# =============================================================================================================
def to_signed64(value: int) -> int:
    value &= (1 << 64) - 1
    return value - (1 << 64) if value >= (1 << 63) else value


def phash_int64(image: Image.Image) -> int:
    return to_signed64(int(str(imagehash.phash(image)), 16))


def hamming_bits(a: int, b: int) -> int:
    """Same as fn_phash_distance(a, b): bit_count((a # b)::bit(64))."""
    return ((a ^ b) & ((1 << 64) - 1)).bit_count()


# =============================================================================================================
# Database (role civicbrain_ai; the caller owns the transaction)
# =============================================================================================================
FACTS_SQL = text(
    """
    SELECT c.complaint_id, c.user_id, cc.yolo_class_id, c.location_accuracy_m, c.location_captured_at, c.submitted_at,
           u.trust_score,
           c.capture_session_id IS NOT NULL                                AS cs_present,
           coalesce(cs.user_id = c.user_id, false)                         AS cs_same_user,
           coalesce(cs.used_by_complaint_id = c.complaint_id, false)       AS cs_used_by_this,
           coalesce(cs.used_at IS NOT NULL AND cs.used_at <= cs.expires_at, false) AS cs_in_time,
           (SELECT count(*) FROM complaints o
             WHERE o.capture_session_id = c.capture_session_id AND o.complaint_id <> c.complaint_id) AS cs_other,
           b.inside, b.edge_m,
           (SELECT count(*) FROM complaints n
             WHERE n.user_id = c.user_id AND n.submitted_at > c.submitted_at - interval '24 hours'
               AND n.submitted_at <= c.submitted_at)                       AS n24
      FROM complaints c
      JOIN users u ON u.user_id = c.user_id
      LEFT JOIN complaint_categories cc ON cc.category_id = c.category_id
      LEFT JOIN capture_sessions cs ON cs.capture_session_id = c.capture_session_id
      LEFT JOIN LATERAL (
            SELECT bool_or(ST_Covers(mb.geometry, c.location))                                AS inside,
                   min(ST_Distance(ST_Boundary(mb.geometry)::geography, c.location::geography)) AS edge_m
              FROM municipal_boundary mb
             WHERE mb.status IN ('VERIFIED', 'ACTIVE')) b ON true
     WHERE c.complaint_id = :cid
    """
)
IMAGE_SQL = text(
    """
    SELECT image_id, sha256, phash FROM complaint_images
     WHERE complaint_id = :cid AND image_role = 'CITIZEN_EVIDENCE'
     ORDER BY image_id LIMIT 1
    """
)
SHA256_SQL = text(
    "SELECT DISTINCT complaint_id FROM complaint_images WHERE sha256 = :sha AND complaint_id <> :cid ORDER BY complaint_id LIMIT 20"
)
PHASH_SQL = text(
    """
    SELECT s.complaint_id, s.image_id, s.hamming_bits, s.distance_m,
           abs(extract(epoch FROM co.submitted_at - c.submitted_at)) / 3600.0 AS hours_apart
      FROM fn_similar_images(:image_id, :max_bits) s
      JOIN complaints co ON co.complaint_id = s.complaint_id
      JOIN complaints c  ON c.complaint_id = :cid
     WHERE NOT s.same_complaint
     ORDER BY s.hamming_bits, s.distance_m, s.image_id
     LIMIT 50
    """
)
PREVIOUS_SQL = text(
    """
    SELECT ST_Distance(p.location::geography, c.location::geography) AS distance_m,
           c.location_captured_at AS this_captured, p.location_captured_at AS prev_captured,
           c.submitted_at AS this_submitted, p.submitted_at AS prev_submitted
      FROM complaints c
      JOIN complaints p ON p.user_id = c.user_id AND p.complaint_id <> c.complaint_id
                       AND (p.submitted_at, p.complaint_id) < (c.submitted_at, c.complaint_id)
     WHERE c.complaint_id = :cid
     ORDER BY p.submitted_at DESC, p.complaint_id DESC
     LIMIT 1
    """
)


def load_facts(session: Session, complaint_id: int) -> AuthFacts:
    row = session.execute(FACTS_SQL, {"cid": complaint_id}).mappings().one_or_none()
    if row is None:
        raise DataError(f"complaint {complaint_id} not found")
    image = session.execute(IMAGE_SQL, {"cid": complaint_id}).mappings().one_or_none()
    sha = image["sha256"] if image else None
    phash = image["phash"] if image else None
    sha_others = [int(r[0]) for r in session.execute(SHA256_SQL, {"sha": sha, "cid": complaint_id})] if sha else []
    matches = []
    if image is not None and phash is not None:
        params = {"image_id": image["image_id"], "max_bits": PHASH_WARN_MAX_BITS, "cid": complaint_id}
        matches = [
            PhashMatch(int(r["complaint_id"]), int(r["image_id"]), int(r["hamming_bits"]), float(r["distance_m"]), float(r["hours_apart"]))
            for r in session.execute(PHASH_SQL, params).mappings()
        ]
    prev = session.execute(PREVIOUS_SQL, {"cid": complaint_id}).mappings().one_or_none()
    prev_distance = prev_seconds = None
    if prev is not None:
        prev_distance = float(prev["distance_m"])
        # GPS fix times when both exist (the moment the user stood there), else the submit times
        if prev["this_captured"] is not None and prev["prev_captured"] is not None:
            prev_seconds = abs((prev["this_captured"] - prev["prev_captured"]).total_seconds())
        else:
            prev_seconds = abs((prev["this_submitted"] - prev["prev_submitted"]).total_seconds())
    return AuthFacts(
        complaint_id=int(row["complaint_id"]),
        user_id=int(row["user_id"]),
        image_id=int(image["image_id"]) if image else None,
        category_class_id=row["yolo_class_id"],
        capture_session=CaptureSessionFacts(
            present=bool(row["cs_present"]),
            belongs_to_user=bool(row["cs_same_user"]),
            used_by_this_complaint=bool(row["cs_used_by_this"]),
            used_before_expiry=bool(row["cs_in_time"]),
            other_complaints=int(row["cs_other"]),
        ),
        accuracy_m=float(row["location_accuracy_m"]) if row["location_accuracy_m"] is not None else None,
        captured_at=row["location_captured_at"],
        submitted_at=row["submitted_at"],
        inside_boundary=row["inside"],
        edge_distance_m=float(row["edge_m"]) if row["edge_m"] is not None else None,
        sha256_present=sha is not None,
        phash_present=phash is not None,
        sha256_other_complaint_ids=sha_others,
        phash_matches=matches,
        complaints_24h=int(row["n24"]),
        previous_distance_m=prev_distance,
        previous_seconds=prev_seconds,
        trust_score=float(row["trust_score"]),
    )


DELETE_SQL = text(
    """
    DELETE FROM authenticity_checks a
     WHERE a.complaint_id = :cid
       AND (a.image_id IS NULL
            OR a.image_id IN (SELECT i.image_id FROM complaint_images i
                               WHERE i.complaint_id = :cid AND i.image_role = 'CITIZEN_EVIDENCE'))
    """
)
INSERT_SQL = text(
    """
    INSERT INTO authenticity_checks (complaint_id, image_id, check_code, result, score_delta, details)
    VALUES (:cid, :image_id, :code, :result, :delta, CAST(:details AS jsonb))
    """
)
# an officer's REJECTED (fake) decision is never overwritten by a re-analysis
UPDATE_SQL = text(
    """
    UPDATE complaints
       SET authenticity_score = :score,
           authenticity_status = CASE WHEN authenticity_status = 'REJECTED' THEN authenticity_status ELSE :status END
     WHERE complaint_id = :cid
    """
)


def write_results(session: Session, complaint_id: int, image_id: int | None, results: Sequence[CheckResult]) -> tuple[float, str]:
    """Idempotent: delete this analysis' rows of the complaint (contractor-photo rows of ANALYZE_IMAGE stay), insert,
    then set complaints.authenticity_score/status. Returns (score, status)."""
    codes = [r.code for r in results]
    if len(codes) != len(set(codes)):
        raise DataError(f"duplicate check codes {codes}")
    session.execute(DELETE_SQL, {"cid": complaint_id})
    for r in results:
        session.execute(
            INSERT_SQL,
            {
                "cid": complaint_id,
                "image_id": image_id if r.code in IMAGE_CHECKS else None,
                "code": r.code,
                "result": r.result,
                "delta": r.delta,
                "details": json.dumps(r.details, sort_keys=True),
            },
        )
    score, status = final_score(results)
    session.execute(UPDATE_SQL, {"cid": complaint_id, "score": round(score, 2), "status": status})
    return score, status
