"""Application tracker HTTP and relevance result schemas."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

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


RequirementType = Literal[
    "hard_skill",
    "responsibility",
    "quantitative",
    "education",
    "certification",
    "language",
    "project",
    "research",
    "other",
]


class JobRequirement(BaseModel):
    """One atomic, explainable requirement extracted from a job description."""

    id: str
    text: str
    normalized: str
    canonical: str | None = None
    type: RequirementType
    required: bool
    weight: float
    constraint: dict | None = None


class RequirementEvidence(BaseModel):
    """The strongest CV field supporting one job requirement."""

    section_type: str
    library_entry_id: str | None = None
    source_row_id: str | None = None
    field_path: str
    snippet: str
    method: Literal["taxonomy", "constraint", "fts5", "fuzzy"]
    score: float


class RequirementMatch(BaseModel):
    requirement: JobRequirement
    covered: bool
    score: float
    matched_by: list[str] = Field(default_factory=list)
    best_evidence: RequirementEvidence | None = None


class RequirementRelevanceResult(BaseModel):
    """Weighted requirement coverage for a generated or manually edited CV."""

    status: Literal["not_evaluated", "evaluated"]
    score: int | None
    # Added after requirement-v1. Optional keeps old persisted results readable.
    coverage_score: int | None = None
    required_score: int | None = None
    preferred_score: int | None = None
    matched_weight: float = 0.0
    total_weight: float = 0.0
    covered_requirements: int = 0
    total_requirements: int = 0
    requirements: list[RequirementMatch] = Field(default_factory=list)
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


class ApplicationStatusHistoryResponse(BaseModel):
    """A persisted application status transition."""

    model_config = {"from_attributes": True}

    id: str
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    changed_at: datetime


class CVQualityIssue(BaseModel):
    """A deterministic, actionable CV quality finding."""

    code: Literal["missing_name", "missing_contact", "empty_section", "invalid_link", "page_overflow"]
    severity: Literal["warning", "error"]
    message: str
    section_type: str | None = None
    field_path: str | None = None


class CVQualityResult(BaseModel):
    """Persisted quality summary for the linked generated CV."""

    status: Literal["pass", "warning", "error"] = "pass"
    page_count: int | None = None
    issues: list[CVQualityIssue] = Field(default_factory=list)


class ApplicationCreate(BaseModel):
    company: str = Field(max_length=255)
    role: str = Field(max_length=255)
    job_description: str = Field(max_length=100_000)
    job_url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=20_000)
    next_follow_up_at: date | None = None

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
    next_follow_up_at: date | None = None
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
    next_follow_up_at: date | None
    status_history: list[ApplicationStatusHistoryResponse] = Field(default_factory=list)
    generation_status: GenerationStatus
    generation_error: str | None
    extracted_keywords: list[dict]
    relevance: RequirementRelevanceResult | RelevanceResult | dict
    quality: CVQualityResult | dict
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
    next_follow_up_at: date | None
    generation_status: GenerationStatus
    generation_error: str | None
    relevance: RequirementRelevanceResult | RelevanceResult | dict
    fits_one_page: bool | None
    quality: CVQualityResult | dict
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
    "ApplicationStatusHistoryResponse",
    "ApplicationStatus",
    "ApplicationUpdate",
    "CVQualityIssue",
    "CVQualityResult",
    "ExtractedKeyword",
    "GenerationStatus",
    "JobRequirement",
    "MatchEvidence",
    "RequirementEvidence",
    "RequirementMatch",
    "RequirementRelevanceResult",
    "RequirementType",
    "RelevanceResult",
]
