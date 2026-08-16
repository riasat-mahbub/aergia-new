"""Application tracker HTTP and relevance result schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.core.safe_url import normalize_http_url


class ExtractedKeyword(BaseModel):
    text: str
    normalized: str
    weight: float


class MatchEvidence(BaseModel):
    keyword: str
    section_type: str
    library_entry_id: str | None = None
    source_row_id: str | None = None
    field_path: str
    snippet: str


class RelevanceResult(BaseModel):
    score: int
    matched_weight: float
    total_weight: float
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    evidence: list[MatchEvidence] = Field(default_factory=list)
    algorithm_version: str


class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    APPLIED = "applied"
    RESPONDED = "responded"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class ApplicationCreate(BaseModel):
    company: str = Field(max_length=255)
    role: str = Field(max_length=255)
    job_description: str = Field(max_length=100_000)
    job_url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("company", "role", "job_description")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = normalize_http_url(value)
        if not normalized:
            raise ValueError("job_url must be an HTTP(S) URL")
        return normalized


class ApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    job_description: str | None = Field(default=None, max_length=100_000)
    job_url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=20_000)
    status: ApplicationStatus | None = None
    applied_at: datetime | None = None

    @field_validator("company", "role", "job_description")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("job_url")
    @classmethod
    def validate_job_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = normalize_http_url(value)
        if not normalized:
            raise ValueError("job_url must be an HTTP(S) URL")
        return normalized


class ApplicationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    cv_id: str | None
    company: str
    role: str
    job_url: str | None
    job_description: str
    notes: str | None
    status: ApplicationStatus
    applied_at: datetime | None
    generation_status: GenerationStatus
    generation_error: str | None
    extracted_keywords: list[dict]
    relevance: dict
    algorithm_version: str
    fits_one_page: bool | None
    created_at: datetime
    updated_at: datetime


class ApplicationListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    cv_id: str | None
    company: str
    role: str
    status: ApplicationStatus
    applied_at: datetime | None
    generation_status: GenerationStatus
    generation_error: str | None
    relevance: dict
    fits_one_page: bool | None
    created_at: datetime
    updated_at: datetime


class ApplicationGenerateResponse(BaseModel):
    application: ApplicationResponse
    cv_id: str | None


__all__ = [
    "ApplicationCreate",
    "ApplicationGenerateResponse",
    "ApplicationListItem",
    "ApplicationResponse",
    "ApplicationStatus",
    "ApplicationUpdate",
    "ExtractedKeyword",
    "GenerationStatus",
    "MatchEvidence",
    "RelevanceResult",
]
