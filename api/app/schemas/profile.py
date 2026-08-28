"""Profile HTTP schemas for the singleton Library Profile."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProfileSocialLink(BaseModel):
    """A social link matching the frontend ProfileData shape."""

    label: str
    url: str
    icon: str


class UserProfile(BaseModel):
    """The contact and summary data shared by generated CVs."""

    name: str | None = None
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    site_text: str | None = None
    site_url: str | None = None
    summary: str | None = None
    photo_url: str | None = None
    email_link: bool = True
    social_links: list[ProfileSocialLink] = Field(default_factory=list)


class UserProfileUpdate(UserProfile):
    """Complete replacement payload for the singleton profile."""


__all__ = ["ProfileSocialLink", "UserProfile", "UserProfileUpdate"]
