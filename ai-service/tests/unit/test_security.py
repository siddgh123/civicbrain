"""Service JWT: HS256 only, aud/iss/exp/iat required, 60-second tokens (docs/07_SECURITY.md sec. 5)."""

import base64
import json
import time

import jwt
import pytest

from app.security import ServiceAuthError, make_service_jwt, verify_service_jwt

KEY = b"k" * 32
NOW = 1_790_000_000  # fixed clock


def _token(**claims) -> str:
    base = {"iss": "civicbrain-api", "aud": "civicbrain-ai", "iat": NOW, "exp": NOW + 60}
    base.update(claims)
    return jwt.encode({k: v for k, v in base.items() if v is not None}, KEY, algorithm="HS256")


def _b64(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()


def test_valid_token_is_accepted():
    claims = verify_service_jwt(_token(), KEY, now=NOW + 1)
    assert claims["aud"] == "civicbrain-ai"


def test_helper_makes_a_valid_token():
    assert verify_service_jwt(make_service_jwt(KEY, now=NOW), KEY, now=NOW + 1)["iss"] == "civicbrain-api"


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "civicbrain-web"},  # wrong audience
        {"iss": "someone-else"},  # wrong issuer
        {"exp": None},  # exp missing
        {"iat": None},  # iat missing
        {"aud": None},  # aud missing
        {"iss": None},  # iss missing
        {"exp": NOW + 600},  # lives longer than 60 s
        {"iat": NOW + 600, "exp": NOW + 630},  # issued in the future
    ],
    ids=["wrong-aud", "wrong-iss", "no-exp", "no-iat", "no-aud", "no-iss", "too-long", "future-iat"],
)
def test_wrong_claims_are_rejected(claims):
    with pytest.raises(ServiceAuthError):
        verify_service_jwt(_token(**claims), KEY, now=NOW + 1)


def test_expired_token_is_rejected():
    with pytest.raises(ServiceAuthError, match="Expired"):
        verify_service_jwt(_token(), KEY, now=NOW + 120)


def test_token_from_the_real_clock_is_accepted():
    assert verify_service_jwt(make_service_jwt(KEY, now=time.time()), KEY)["aud"] == "civicbrain-ai"


def test_other_algorithm_is_rejected():
    token = jwt.encode({"iss": "civicbrain-api", "aud": "civicbrain-ai", "iat": NOW, "exp": NOW + 60}, KEY * 2, algorithm="HS512")
    with pytest.raises(ServiceAuthError, match="InvalidAlgorithmError"):
        verify_service_jwt(token, KEY * 2, now=NOW + 1)


def test_alg_none_is_rejected():
    token = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'iss': 'civicbrain-api', 'aud': 'civicbrain-ai', 'iat': NOW, 'exp': NOW + 60})}."
    with pytest.raises(ServiceAuthError):
        verify_service_jwt(token, KEY, now=NOW + 1)


def test_wrong_key_is_rejected():
    with pytest.raises(ServiceAuthError):
        verify_service_jwt(_token(), b"x" * 32, now=NOW + 1)


def test_garbage_is_rejected():
    with pytest.raises(ServiceAuthError):
        verify_service_jwt("not.a.jwt", KEY, now=NOW)
