"""Settings and project constants of the AI service.

Settings: pydantic-settings, names exactly as in `.env.example` (rule 30). They are created lazily by
`get_settings()` (never at import time). Uvicorn, the worker and pytest run from `ai-service/` and read the
repo-root `.env` themselves; real environment variables win over the file (the start scripts and the tests
use that to switch DB_NAME).

Constants: FROZEN values come from the validated research steps (.agents/rules/02-frozen-rules.md) and never
change. ASSUMPTION values are project defaults (docs/06_AI_PIPELINE.md): the pipeline writes the ones it used
into the result's `assumptions` JSON and the UI shows them as assumptions.
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.errors import ConfigError


class Settings(BaseSettings):
    # extra='ignore': the shared .env also holds backend/mail/WhatsApp keys.
    # env_ignore_empty: `KEY=` in .env means "not set" (Windows cannot hold empty variables either).
    model_config = SettingsConfigDict(env_file=("../.env",), env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True)

    # ---- database: role civicbrain_ai, never the owner account (docs/07_SECURITY.md sec. 5) ----
    db_host: str = Field(min_length=1)
    db_port: int = Field(ge=1, le=65535)
    db_name: str = Field(min_length=1)
    db_ai_user: str = Field(min_length=1)
    db_ai_password: SecretStr

    # ---- worker (docs/06_AI_PIPELINE.md sec. 1) ----
    worker_id: str = Field(min_length=1, max_length=100)  # unique per worker process, shows up in jobs.locked_by
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    # Worker/API refuse to start when a required model file or checksum is missing (06 sec. 5).
    # false until P12 (the model files arrive in P08/P09); tests set false.
    require_models: bool = False

    # ---- routing (MVP: haversine; Phase 2: osrm) ----
    routing_mode: Literal["haversine", "osrm"] = "haversine"
    osrm_url: str = "http://127.0.0.1:5000"

    # ---- models (absolute paths; files + SHA-256 in models/MANIFEST.json) ----
    yolo_weights: Path
    models_dir: Path
    text_embedding_model_dir: Path

    # ---- internal API (docs/04_API_CONTRACT.md sec. 10) ----
    ai_service_jwt_secret: SecretStr  # base64 of >= 32 random bytes (scripts/dev/new-secret.ps1)
    ai_api_host: str = "127.0.0.1"
    ai_api_port: int = Field(default=8001, ge=1, le=65535)

    # ---- files, costs, privacy, logging ----
    storage_root: Path
    labour_rate_per_hour: float | None = Field(default=None, gt=0)  # empty until TDMC gives a rate: cost shows "rate not set"
    blur_enabled: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper(cls, v: object) -> object:
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("routing_mode", mode="before")
    @classmethod
    def _lower(cls, v: object) -> object:
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("ai_api_host")
    @classmethod
    def _localhost_only(cls, v: str) -> str:
        if v != "127.0.0.1":
            raise ValueError("must be 127.0.0.1 - the AI API is internal (docs/07_SECURITY.md sec. 5)")
        return v

    @field_validator("ai_service_jwt_secret")
    @classmethod
    def _base64_key(cls, v: SecretStr) -> SecretStr:
        _decode_key(v.get_secret_value())  # error messages never contain the value
        return v

    @property
    def jwt_key(self) -> bytes:
        """HMAC key of the service JWT = the base64-DECODED secret (same convention as JWT_SECRET)."""
        return _decode_key(self.ai_service_jwt_secret.get_secret_value())


def _decode_key(value: str) -> bytes:
    try:
        raw = base64.b64decode(value.strip(), validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("must be base64 (scripts/dev/new-secret.ps1)") from None
    if len(raw) < 32:
        raise ValueError(f"must decode to >= 32 bytes (found {len(raw)})")
    return raw


def describe_settings_error(exc: ValidationError) -> str:
    """One line per problem, named like the .env key. Input values are left out (they may be secrets)."""
    parts = []
    for err in exc.errors(include_input=False, include_url=False):
        key = ".".join(str(p) for p in err["loc"]).upper() or "SETTINGS"
        parts.append(f"{key}: {err['msg']}")
    return "Invalid or missing settings (names as in .env.example): " + "; ".join(parts)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The settings of this process, created on first use. Raises ConfigError with a clear message."""
    try:
        return Settings()  # type: ignore[call-arg]  # values come from the environment / .env
    except ValidationError as exc:
        raise ConfigError(describe_settings_error(exc)) from None


# =============================================================================================
# FROZEN (Step 9, .agents/rules/02-frozen-rules.md): YOLO classes, same order in data.yaml, code and DB
# =============================================================================================
YOLO_CLASSES: tuple[str, ...] = ("Pothole", "Garbage Accumulation", "Waterlogging", "Road Damage")

# =============================================================================================
# Model files (docs/06_AI_PIPELINE.md sec. 5) - paths relative to MODELS_DIR, as in models/MANIFEST.json
# =============================================================================================
TEXT_CLF_FILE = "text_clf.joblib"
YUNET_FILE = "face_detection_yunet_2023mar.onnx"  # required only when BLUR_ENABLED=true

# =============================================================================================
# Worker loop (docs/06_AI_PIPELINE.md sec. 1, docs/12_ERROR_HANDLING.md sec. 4)
# =============================================================================================
WORKER_JOB_TYPES: tuple[str, ...] = ("ANALYZE_COMPLAINT", "ANALYZE_IMAGE", "OPTIMIZE_PLAN", "BLUR_IMAGE")
# Hard limit per job: analyze 120 s, optimize 60 s, blur 60 s (06 sec. 1). ANALYZE_IMAGE is an analysis -> 120 s.
JOB_TIMEOUT_SECONDS: dict[str, float] = {"ANALYZE_COMPLAINT": 120, "ANALYZE_IMAGE": 120, "OPTIMIZE_PLAN": 60, "BLUR_IMAGE": 60}
STALE_REQUEUE_EVERY_SECONDS = 300  # every 5 min ...
STALE_JOB_AFTER = "15 minutes"  # ... fn_requeue_stale_jobs('15 minutes')
DB_RETRY_WAIT_SECONDS = 10.0  # worker pause after a database error before it polls again

# =============================================================================================
# 2.1 Authenticity score (docs/06_AI_PIPELINE.md sec. 2.1) - project defaults (ASSUMPTION)
# Start 100, clamp 0-100, < 40 -> FLAGGED else PASSED. Penalties are subtracted from the start score.
# =============================================================================================
AUTH_START_SCORE = 100
AUTH_FLAGGED_BELOW = 40
GPS_ACCURACY_PASS_MAX_M = 50  # <= 50 m PASS
GPS_ACCURACY_WARN_MAX_M = 150  # 50-150 m WARN (the API rejects > 150 m)
GPS_ACCURACY_WARN_PENALTY = 10
GPS_FRESHNESS_PASS_MAX_MIN = 2  # captured <= 2 min before submit PASS
GPS_FRESHNESS_WARN_MAX_MIN = 10  # 2-10 min WARN (the API rejects > 10 min)
GPS_FRESHNESS_WARN_PENALTY = 10
BOUNDARY_EDGE_WARN_M = 50  # inside but within 50 m of the TDMC edge -> WARN
BOUNDARY_EDGE_WARN_PENALTY = 5
IMAGE_REUSE_SHA256_PENALTY = 50  # same SHA-256 on another complaint -> FAIL
PHASH_FAIL_MAX_BITS = 4  # <= 4 bits (far away or long ago) -> FAIL
PHASH_WARN_MAX_BITS = 10  # 5-10 bits (far away or long ago) -> WARN
PHASH_FAR_M = 300  # "far away" = other complaint > 300 m away ...
PHASH_LONG_AGO_DAYS = 7  # ... or > 7 days apart (nearby and recent = duplicate hint, PASS)
PHASH_WARN_PENALTY = 15
PHASH_FAIL_PENALTY = 40
SUBMISSION_RATE_PASS_MAX_24H = 3  # <= 3 complaints in 24 h PASS
SUBMISSION_RATE_WARN_MAX_24H = 5  # 4-5 in 24 h WARN
SUBMISSION_RATE_WARN_PENALTY = 10
IMPOSSIBLE_TRAVEL_MAX_KMH = 150  # > 150 km/h since the user's previous complaint -> WARN
IMPOSSIBLE_TRAVEL_PENALTY = 20
TRUST_LOW_BELOW = 30  # users.trust_score < 30 -> WARN
TRUST_LOW_PENALTY = 15
TRUST_HIGH_ABOVE = 70  # users.trust_score > 70 -> +5
TRUST_HIGH_BONUS = 5
CATEGORY_MATCH_MIN_CONF = 0.4  # detection of the category's own class >= 0.4 -> PASS
CATEGORY_OTHER_CLASS_MIN_CONF = 0.5  # only other classes >= 0.5 -> WARN
CATEGORY_MISMATCH_PENALTY = 10

# =============================================================================================
# 2.4 Measurement (docs/06_AI_PIPELINE.md sec. 2.4)
# =============================================================================================
# Tier A - A4 sheet as reference (tried only when complaints.a4_in_frame = true)
A4_SIZE_MM = (210.0, 297.0)  # ISO 216 (fact, not an assumption)
A4_MIN_AREA_FRACTION = 0.01  # quadrilateral area >= 1 % of the image
A4_ASPECT = 1.414  # rectified aspect ratio ...
A4_ASPECT_TOLERANCE = 0.15  # ... +- 0.15
TIER_A_ERROR_BAND_PCT = 10  # ASSUMPTION: +-10 %
# Tier B - ground-plane projection from the phone pitch
PHONE_F35_MM = 26.0  # ASSUMPTION: typical phone main camera, 35 mm-equivalent focal length (no per-device table)
FULL_FRAME_DIAGONAL_MM = 43.27  # 35 mm film diagonal (fact): f_px = f35 * sqrt(W^2 + H^2) / 43.27
CAMERA_HEIGHT_M = 1.4  # ASSUMPTION: phone held at chest height
TIER_B_MIN_DEPRESSION_DEG = 30.0  # camera depression theta = 90 - beta must be >= 30 deg, else Tier C
MONTE_CARLO_SAMPLES = 200  # error band P10-P90 from 200 samples:
MC_SIGMA_CAMERA_HEIGHT_M = 0.15  #   h ~ N(1.4, 0.15)
MC_SIGMA_DEPRESSION_DEG = 2.0  #   theta ~ N(theta, 2 deg)
MC_SIGMA_F35_MM = 2.0  #   f35 ~ N(26, 2)
MC_BAND_PERCENTILES = (10, 90)
# Tier C - class priors (ASSUMPTION), +-60 %
TIER_C_ERROR_BAND_PCT = 60
TIER_C_PRIORS_M: dict[str, dict[str, float]] = {
    "Pothole": {"length_m": 0.6, "width_m": 0.4},
    "Road Damage": {"length_m": 2.0},  # crack length
    "Garbage Accumulation": {"length_m": 1.5, "width_m": 1.0},  # base of the heap
    "Waterlogging": {"length_m": 4.0, "width_m": 3.0},
}
# NOTE: 06 sec. 2.4 says "NULL depth answer -> the class prior's depth (Tier C)" but gives no number for it;
# P12 decides it and records the DECISION in docs/PROGRESS.md (no depth is invented here).
# Method and confidence by tier (defect_measurements.method / confidence)
TIER_METHOD = {"A": "REFERENCE_OBJECT", "B": "GROUND_PLANE_HOMOGRAPHY", "C": "CATEGORY_DEFAULT"}
TIER_CONFIDENCE = {"A": 0.9, "B": 0.6, "C": 0.3}
# Depth is never measured from the photo: it comes from complaints.depth_answer (V5)
POTHOLE_DEPTH_M = {"SHALLOW": 0.025, "FINGER": 0.050, "DEEP": 0.075}  # IRC:82 small / medium; DEEP 75 mm ASSUMPTION
WATERLOGGING_DEPTH_M = {"SHALLOW": 0.08, "FINGER": 0.30, "DEEP": 0.50}  # ASSUMPTION: below ankle / below knee / deeper
DEPTH_SEVERITY_CLASS = {"SHALLOW": "SMALL", "FINGER": "MEDIUM", "DEEP": "LARGE"}
DEPTH_SOURCE_FROM_ANSWER = "ASSUMED_FROM_SEVERITY_CLASS"
