"""Account linking and launch contracts for optional tailoring providers."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TailoringProvider = Literal["chatgpt", "gemini"]


class TailoringProviderStatus(BaseModel):
    status: Literal["unavailable", "disconnected", "setup_required", "ready", "reconnect"]
    detail: str | None = None


class TailoringProvidersStatus(BaseModel):
    chatgpt: TailoringProviderStatus
    gemini: TailoringProviderStatus


class TailoringAuthorizationLink(BaseModel):
    authorization_url: str


class TailoringOAuthCallback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str = Field(pattern=r"^[a-zA-Z0-9_-]{43}$")
    code: str | None = Field(default=None, max_length=4096)
    error: str | None = Field(default=None, max_length=256)
    client_id: str | None = Field(default=None, max_length=256)


class TailoringProviderLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: TailoringProvider
