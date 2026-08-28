"""Profile HTTP schemas for the singleton Library Profile."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.safe_url import normalize_http_url


class ProfileSocialLink(BaseModel):
    """A social link matching the frontend ProfileData shape."""

    label: str = Field(max_length=100)
    url: str = Field(max_length=2048)
    icon: str = Field(max_length=64)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        normalized = normalize_http_url(value)
        if not normalized:
            raise ValueError("social URL must be an HTTP(S) URL")
        return normalized


class UserProfile(BaseModel):
    """The contact and summary data shared by generated CVs."""

    name: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=255)
    site_text: str | None = Field(default=None, max_length=255)
    site_url: str | None = Field(default=None, max_length=2048)
    summary: str | None = Field(default=None, max_length=20_000)
    photo_url: str | None = Field(default=None, max_length=2048)
    email_link: bool = True
    social_links: list[ProfileSocialLink] = Field(default_factory=list, max_length=32)

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = normalize_http_url(value)
        if not normalized:
            raise ValueError("site_url must be an HTTP(S) URL")
        return normalized

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        if value.startswith("/api/v1/assets/") and ".." not in value and "\\" not in value:
            return value
        normalized = normalize_http_url(value)
        if not normalized:
            raise ValueError("photo_url must be an HTTP(S) URL or private asset URL")
        return normalized


class UserProfileUpdate(UserProfile):
    """Complete replacement payload for the singleton profile."""


__all__ = ["ProfileSocialLink", "UserProfile", "UserProfileUpdate"]
