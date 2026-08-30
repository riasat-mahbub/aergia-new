"""Auth request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


MAX_PASSWORD_LENGTH = 128
MAX_BCRYPT_PASSWORD_BYTES = 72
AccountTier = Literal["free", "premium"]


def _validate_bcrypt_password_bytes(value: str) -> str:
    try:
        byte_length = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("password contains invalid characters") from exc
    if byte_length > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_LENGTH)
    turnstile_token: str | None = Field(default=None, max_length=2048)

    _password_byte_limit = field_validator("password")(_validate_bcrypt_password_bytes)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class RegistrationConfigResponse(BaseModel):
    """Public registration settings; never expose the verification secret."""

    turnstile_site_key: str | None = None
    turnstile_required: bool
    turnstile_action: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthMessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    authenticated: bool
    account_tier: AccountTier | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


__all__ = [
    "AuthMessageResponse",
    "AccountTier",
    "LoginRequest",
    "RegistrationConfigResponse",
    "RefreshRequest",
    "RegisterRequest",
    "SessionResponse",
    "TokenResponse",
]
