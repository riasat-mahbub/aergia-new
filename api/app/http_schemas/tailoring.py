"""HTTP contracts for whole-document local-agent tailoring (protocol v5).

The agent authors one complete CV candidate. There is deliberately no patch
or evidence-reference model here: the exchanged context is read-only input,
while the authenticated user remains the only actor that can accept the
result and change an application's linked CV.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.document_schema.models import Customizations, SectionInstance
from app.scanner.requirements import RequirementExtraction
from app.scanner.results import ScanResult, ScannerVersions
from app.http_schemas.tailoring_evaluation import (
    TAILORING_EVALUATION_VERSION,
    TailoringEditorialReview,
    TailoringEvaluation,
    TailoringInferenceNote,
)


TAILORING_PROTOCOL_VERSION = 5
PROTOCOL_VERSION = TAILORING_PROTOCOL_VERSION


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TailoringCodeExchange(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION]
    code: str = Field(min_length=16, max_length=128)

    @field_validator("code")
    @classmethod
    def trim_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("code must not be blank")
        return value


class TailoringSessionCreateResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    source_cv_id: str | None = None
    # Readable source alias for existing browser consumers.
    cv_id: str | None = None
    code: str
    session_url: str = Field(min_length=1, max_length=2048)
    skill_url: str = Field(min_length=1, max_length=2048)
    prompt: str = Field(min_length=1, max_length=5000)
    status: Literal["created"] = "created"
    expires_at: datetime


class TailoringExchangeResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    expires_at: datetime
    capability: str


TailoringSessionState = Literal[
    "created",
    "exchanged",
    "draft_ready",
    "accepted",
    "rejected",
    "failed",
    "expired",
    "cancelled",
    "stale",
]


class TailoringSessionStatusResponse(_StrictModel):
    # Historical v4 drafts remain owner-reviewable. New exchanges and active
    # agent contexts are v5 only.
    protocol_version: Literal[4, PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    source_cv_id: str | None = None
    draft_cv_id: str | None = None
    # Source-document alias; never points at an unaccepted draft.
    cv_id: str | None = None
    status: TailoringSessionState
    expires_at: datetime
    created_at: datetime
    exchanged_at: datetime | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    updated_at: datetime
    attempts: int = Field(ge=0)
    result: dict | None = None


class TailoringJob(_StrictModel):
    company: str
    role: str
    job_url: str | None = None
    description: str
    # Existing application notes are the one user-owned instruction channel
    # exposed to tailoring; job text and evidence remain untrusted data.
    user_instructions: str | None = Field(default=None, max_length=20_000)


class TailoringSection(SectionInstance):
    """A complete renderer-backed section in the generated candidate."""


class TailoringCV(_StrictModel):
    id: str | None = None
    title: str
    description: str | None = None
    template_id: str
    sections: list[TailoringSection] = Field(max_length=32)
    customizations: Customizations = Field(default_factory=Customizations)


class TailoringLibraryEntry(_StrictModel):
    id: str
    kind: str
    content_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    payload: list[dict] = Field(max_length=100)


class TailoringTemplate(_StrictModel):
    id: str
    name: str
    description: str | None = None
    manifest: dict


class TailoringRenderArtifact(_StrictModel):
    format: Literal["pdf"] = "pdf"
    endpoint: str = Field(min_length=1, max_length=256)
    sha256: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    page_count: int | None = Field(default=None, ge=0)


class TailoringScannerContext(_StrictModel):
    """Frozen scanner interpretation exposed to one tailoring session."""

    schema_version: Literal["scanner-v1"] = "scanner-v1"
    versions: ScannerVersions
    requirement_extraction: RequirementExtraction
    source_scan: ScanResult | None = None


class TailoringContextResponse(_StrictModel):
    """Read-only context available to the local agent after exchange."""

    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    source_cv_id: str | None = None
    expires_at: datetime
    context_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    job: TailoringJob
    profile: dict
    previous_cv: TailoringCV | None = None
    library: list[TailoringLibraryEntry] = Field(max_length=100)
    scanner: TailoringScannerContext
    # Compatibility convenience for clients that iterate requirements directly.
    # The scanner.requirement_extraction list is canonical.
    requirements: list[dict] = Field(max_length=100)
    templates: list[TailoringTemplate] = Field(max_length=32)
    selected_template_id: str
    selected_template_manifest: dict
    capabilities: dict = Field(max_length=100)
    capabilities_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    effective_appearance: dict = Field(default_factory=dict, max_length=100)
    rendered_source: TailoringRenderArtifact | None = None
    evaluation_version: Literal[TAILORING_EVALUATION_VERSION] = TAILORING_EVALUATION_VERSION


class TailoringCandidateCV(_StrictModel):
    """The only document write value accepted by protocol v5."""

    id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    template_id: str = Field(min_length=1, max_length=100)
    sections: list[TailoringSection] = Field(min_length=1, max_length=32)
    customizations: Customizations = Field(default_factory=Customizations)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("candidate title must not be blank")
        return value


class TailoringPreviewRequest(_StrictModel):
    context_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    candidate: TailoringCandidateCV
    inference_notes: list[TailoringInferenceNote] = Field(default_factory=list, max_length=20)


class TailoringPreviewResponse(_StrictModel):
    format: Literal["pdf"] = "pdf"
    pdf_base64: str
    page_count: int = Field(ge=0)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    render_warnings: list[str] = Field(default_factory=list, max_length=50)


class TailoringSubmitRequest(_StrictModel):
    context_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    expected_candidate_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    candidate: TailoringCandidateCV
    review_notes: list[str] = Field(default_factory=list, max_length=20)
    inference_notes: list[TailoringInferenceNote] = Field(default_factory=list, max_length=20)
    editorial_review: TailoringEditorialReview | None = None
    allow_bounded_fallback: bool = False

    @field_validator("review_notes")
    @classmethod
    def normalize_review_notes(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("review notes must not be blank")
        if any(len(value) > 1_000 for value in normalized):
            raise ValueError("review notes must not exceed 1000 characters each")
        return normalized


class TailoringSubmitResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    status: Literal["draft_ready"] = "draft_ready"
    source_cv_id: str | None = None
    draft_cv_id: str
    candidate_hash: str
    candidate: TailoringCandidateCV
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    inference_notes: list[TailoringInferenceNote] = Field(default_factory=list, max_length=20)
    editorial_review: TailoringEditorialReview | None = None
    render_warnings: list[str] = Field(default_factory=list, max_length=50)
    review_notes: list[str] = Field(default_factory=list, max_length=20)


class TailoringReviewResponse(_StrictModel):
    protocol_version: Literal[4, PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    status: Literal["accepted", "rejected"]
    source_cv_id: str | None = None
    draft_cv_id: str | None = None
    cv_id: str | None = None
    scanner_result: ScanResult | None = None


__all__ = [
    "PROTOCOL_VERSION",
    "TAILORING_PROTOCOL_VERSION",
    "TAILORING_EVALUATION_VERSION",
    "TailoringCandidateCV",
    "TailoringCodeExchange",
    "TailoringContextResponse",
    "TailoringCV",
    "TailoringEditorialReview",
    "TailoringEvaluation",
    "TailoringExchangeResponse",
    "TailoringJob",
    "TailoringLibraryEntry",
    "TailoringInferenceNote",
    "TailoringPreviewRequest",
    "TailoringPreviewResponse",
    "TailoringRenderArtifact",
    "TailoringReviewResponse",
    "TailoringSection",
    "TailoringSessionCreateResponse",
    "TailoringSessionState",
    "TailoringSessionStatusResponse",
    "TailoringSubmitRequest",
    "TailoringSubmitResponse",
    "TailoringScannerContext",
    "TailoringTemplate",
]
