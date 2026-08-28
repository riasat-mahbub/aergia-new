"""T2: Pytest: register endpoint schema validation (unit)"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.cv import CVCreate, DEFAULT_SECTIONS


class TestAuthSchemas:
    def test_register_request_valid(self):
        data = RegisterRequest(email="user@example.com", password="securepass123")
        assert data.email == "user@example.com"
        assert data.password == "securepass123"

    def test_register_request_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="securepass123")

    def test_register_request_empty_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="", password="securepass123")

    def test_register_request_empty_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="")

    def test_login_request_valid(self):
        data = LoginRequest(email="user@example.com", password="securepass123")
        assert data.email == "user@example.com"
        assert data.password == "securepass123"

    def test_password_minimum_is_eight_characters(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password="1234567")

    def test_password_rejects_more_than_bcrypts_utf8_byte_limit(self):
        long_utf8_password = "😀" * 19  # 76 UTF-8 bytes, but only 19 characters
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com", password=long_utf8_password)


class TestCVSchemas:
    def test_cv_create_valid(self):
        data = CVCreate(title="My CV", template_id="generic-modern")
        assert data.title == "My CV"
        assert data.template_id == "generic-modern"

    def test_cv_create_defaults(self):
        data = CVCreate(title="My CV")
        assert data.template_id == "generic-modern"
        assert data.sections == DEFAULT_SECTIONS
        assert data.customizations is None
