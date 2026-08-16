"""T1: Pytest: password hashing + JWT creation/validation (unit)"""

import jwt

from app.config import get_settings
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_access_token,
    verify_password,
    verify_refresh_token,
    verify_token,
    verify_token_hash,
)


class TestPasswordHashing:
    def test_hash_password_returns_hash(self):
        hashed = hash_password("my_secret_password")
        assert hashed != "my_secret_password"
        assert isinstance(hashed, str)
        assert len(hashed) > 20

    def test_verify_password_correct(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_rejects_bcrypt_oversized_input(self):
        hashed = hash_password("correct_password")
        assert verify_password("a" * 73, hashed) is False

    def test_token_hash_comparison_is_exact(self):
        token = "refresh-token"
        assert verify_token_hash(token, hash_token(token)) is True
        assert verify_token_hash(token, hash_token("different-token")) is False


class TestJWT:
    def test_create_access_token_returns_string(self):
        token = create_access_token("test@example.com")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_create_refresh_token_returns_string(self):
        token = create_refresh_token("test@example.com")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_verify_token_valid(self):
        token = create_access_token("test@example.com")
        email = verify_token(token)
        assert email == "test@example.com"

    def test_access_and_refresh_verifiers_are_type_specific(self):
        access = create_access_token("test@example.com")
        refresh = create_refresh_token("test@example.com")
        assert verify_access_token(access) == "test@example.com"
        assert verify_access_token(refresh) is None
        assert verify_refresh_token(refresh) == "test@example.com"
        assert verify_refresh_token(access) is None

    def test_tokens_include_separate_audience_issuer_type_and_jti_claims(self):
        settings = get_settings()
        access_claims = jwt.decode(create_access_token("test@example.com"), options={"verify_signature": False})
        refresh_claims = jwt.decode(create_refresh_token("test@example.com"), options={"verify_signature": False})

        assert access_claims["typ"] == "access"
        assert refresh_claims["typ"] == "refresh"
        assert access_claims["iss"] == refresh_claims["iss"] == "aergia"
        assert access_claims["aud"] == "aergia-api"
        assert refresh_claims["aud"] == "aergia-refresh"
        assert access_claims["jti"] != refresh_claims["jti"]
        assert settings.secret_key

    def test_verify_token_invalid(self):
        result = verify_token("invalid_token_here")
        assert result is None

    def test_access_and_refresh_tokens_differ(self):
        access = create_access_token("test@example.com")
        refresh = create_refresh_token("test@example.com")
        assert access != refresh
