"""Service JWT for the AI admin endpoints (docs/04_API_CONTRACT.md sec. 10, docs/07_SECURITY.md sec. 5).

The backend (or an admin by hand) signs a 60-second HS256 token with AI_SERVICE_JWT_SECRET (base64-decoded
key), iss=civicbrain-api, aud=civicbrain-ai. Only HS256 is accepted (no 'none', no other algorithm), and
exp, iat, aud and iss are required. Tokens are never logged.
"""

from __future__ import annotations

import time

import jwt

SERVICE_JWT_ALGORITHM = "HS256"
SERVICE_JWT_AUDIENCE = "civicbrain-ai"
SERVICE_JWT_ISSUER = "civicbrain-api"
SERVICE_JWT_MAX_LIFETIME_S = 60
CLOCK_SKEW_S = 5


class ServiceAuthError(Exception):
    """The token is missing, malformed, wrongly signed, expired or has wrong claims."""


def verify_service_jwt(token: str, key: bytes, *, now: float | None = None) -> dict:
    """Return the claims of a valid service token, else raise ServiceAuthError (reason without the token).

    PyJWT checks signature, algorithm, aud, iss and that exp/iat/aud/iss exist; the time checks are done
    here against `now` (testable with a fixed clock): not expired, not issued in the future, lifetime <= 60 s.
    """
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[SERVICE_JWT_ALGORITHM],
            audience=SERVICE_JWT_AUDIENCE,
            issuer=SERVICE_JWT_ISSUER,
            options={"require": ["exp", "iat", "aud", "iss"], "verify_signature": True, "verify_exp": False, "verify_iat": False},
        )
    except jwt.InvalidTokenError as exc:
        raise ServiceAuthError(type(exc).__name__) from None
    now = time.time() if now is None else now
    exp, iat = claims["exp"], claims["iat"]
    if isinstance(exp, bool) or isinstance(iat, bool) or not isinstance(exp, int | float) or not isinstance(iat, int | float):
        raise ServiceAuthError("InvalidClaims")
    if exp <= now - CLOCK_SKEW_S:
        raise ServiceAuthError("Expired")
    if iat > now + CLOCK_SKEW_S:
        raise ServiceAuthError("IssuedInFuture")
    if exp - iat > SERVICE_JWT_MAX_LIFETIME_S:
        raise ServiceAuthError("LifetimeTooLong")
    return claims


def make_service_jwt(key: bytes, *, lifetime_s: int = SERVICE_JWT_MAX_LIFETIME_S, now: float | None = None, **overrides) -> str:
    """Helper for manual use and tests: a valid token (claims can be overridden)."""
    iat = int(time.time() if now is None else now)
    claims = {"iss": SERVICE_JWT_ISSUER, "aud": SERVICE_JWT_AUDIENCE, "iat": iat, "exp": iat + lifetime_s, "sub": "civicbrain-api"}
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm=SERVICE_JWT_ALGORITHM)
