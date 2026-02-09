"""T1: Pytest: password hashing + JWT creation/validation (unit)"""

from app.core.auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token


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

    def test_verify_token_invalid(self):
        result = verify_token("invalid_token_here")
        assert result is None

    def test_access_and_refresh_tokens_differ(self):
        access = create_access_token("test@example.com")
        refresh = create_refresh_token("test@example.com")
        assert access != refresh
