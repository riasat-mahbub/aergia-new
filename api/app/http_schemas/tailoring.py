"""HTTP contracts for full-history whole-document tailoring (protocol v10).

The agent authors one complete CV candidate. There is deliberately no patch
or evidence-reference model here: the exchanged context is read-only input,
while the authenticated user remains the only actor that can accept the
result and change an application's linked CV.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.document_schema.models import Customizations, SectionInstance
from app.scanner.requirements import RequirementExtraction
from app.scanner.results import ScanResult, ScannerVersions
from app.http_schemas.tailoring_evaluation import (
    TAILORING_EVALUATION_VERSION,
    TailoringEvaluation,
)
from app.http_schemas.tailoring_fit_review import FitReviewReport


TAILORING_PROTOCOL_VERSION = 10
PROTOCOL_VERSION = TAILORING_PROTOCOL_VERSION
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SESSION_ID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
_EVALUATION_ID_PATTERN = r"^[A-Za-z0-9_-]{16,128}$"
TailoringFitReview = FitReviewReport


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TailoringCodeExchange(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION]
    session_id: str = Field(min_length=36, max_length=36, pattern=_SESSION_ID_PATTERN)
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
    # Historical drafts stay owner-reviewable; only protocol v10 can start or resume.
    protocol_version: Literal[4, 5, 6, 7, 8, 9, PROTOCOL_VERSION] = PROTOCOL_VERSION
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
    # New owner-review state is absent on historical protocol rows.
    draft_review: "TailoringDraftReview | None" = None


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


class TailoringTemplate(_StrictModel):
    id: str
    name: str
    description: str | None = None
    manifest: dict


class TailoringScannerContext(_StrictModel):
    """Frozen scanner interpretation held server-side for one session."""

    schema_version: Literal["scanner-v1"] = "scanner-v1"
    versions: ScannerVersions
    requirement_extraction: RequirementExtraction
    source_scan: ScanResult | None = None


class TailoringContextResponse(_StrictModel):
    """Read-only writer context available after capability exchange."""

    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    source_cv_id: str | None = None
    source_cv_revision: int | None = Field(default=None, ge=1)
    expires_at: datetime
    context_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    job: TailoringJob
    dossier: str = Field(min_length=1)
    templates: list[TailoringTemplate] = Field(max_length=32)
    selected_template_id: str
    selected_template_manifest: dict
    capabilities: dict = Field(max_length=100)
    capabilities_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    scanner_context: TailoringScannerContext
    evaluation_version: Literal[TAILORING_EVALUATION_VERSION] = TAILORING_EVALUATION_VERSION


class TailoringCandidateCV(_StrictModel):
    """The complete document write value accepted by protocol v10."""

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
    context_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    reservation_id: str = Field(min_length=36, max_length=36, pattern=_SESSION_ID_PATTERN)
    candidate: TailoringCandidateCV


class TailoringPreviewReservationRequest(_StrictModel):
    context_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    candidate: TailoringCandidateCV
    request_id: UUID


class TailoringPreviewReservationResponse(_StrictModel):
    reservation_id: str = Field(min_length=36, max_length=36, pattern=_SESSION_ID_PATTERN)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    expires_at: datetime


class TailoringPreviewReservationReleaseResponse(_StrictModel):
    reservation_id: str = Field(min_length=36, max_length=36, pattern=_SESSION_ID_PATTERN)
    state: Literal["released", "already_released", "completed"]


class TailoringPreviewResponse(_StrictModel):
    format: Literal["pdf"] = "pdf"
    pdf_base64: str
    page_count: int = Field(ge=0)
    evaluation_id: str = Field(min_length=16, max_length=128, pattern=_EVALUATION_ID_PATTERN)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    pdf_sha256: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    candidate: TailoringCandidateCV
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    render_warnings: list[str] = Field(default_factory=list, max_length=50)


class TailoringSubmitRequest(_StrictModel):
    context_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    evaluation_id: str = Field(min_length=16, max_length=128, pattern=_EVALUATION_ID_PATTERN)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    candidate: TailoringCandidateCV
    review_notes: list[str] = Field(default_factory=list, max_length=20)
    # Null/absent means no report was recorded; it never implies a positive verdict.
    fit_review: FitReviewReport | None = None

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
    evaluation_id: str = Field(min_length=16, max_length=128, pattern=_EVALUATION_ID_PATTERN)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    candidate: TailoringCandidateCV
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    render_warnings: list[str] = Field(default_factory=list, max_length=50)
    review_notes: list[str] = Field(default_factory=list, max_length=20)
    fit_review: FitReviewReport | None = None


class TailoringDraftReview(_StrictModel):
    """Owner review data for the persisted pending draft, never the source CV."""

    state: Literal["current", "needs_reevaluation", "unavailable"]
    # Current meaningful CV revision and canonical candidate identity.
    cv_revision: int | None = Field(default=None, ge=1)
    candidate_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    render_basis_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    evaluation_id: str | None = Field(default=None, min_length=16, max_length=128, pattern=_EVALUATION_ID_PATTERN)
    evaluation: TailoringEvaluation | None = None
    scanner_result: ScanResult | None = None
    warnings: list[str] = Field(default_factory=list, max_length=50)
    pdf_sha256: str | None = Field(default=None, min_length=64, max_length=64, pattern=_SHA256_PATTERN)
    fit_review: FitReviewReport | None = None
    fit_review_applicability: Literal["current", "earlier_version", "not_run"] = "not_run"


class TailoringReevaluateRequest(_StrictModel):
    expected_cv_revision: int = Field(ge=1)


class TailoringReevaluateResponse(_StrictModel):
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    draft_cv_id: str
    draft_review: TailoringDraftReview
    format: Literal["pdf"] = "pdf"
    pdf_base64: str
    page_count: int = Field(ge=0)


class TailoringAcceptRequest(_StrictModel):
    """Optimistic-concurrency tokens required by protocol v10 acceptance."""

    expected_cv_revision: int = Field(ge=1)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=_SHA256_PATTERN)


class TailoringDraftScannerContext(_StrictModel):
    """Frozen job interpretation for a pending draft; deliberately omits source_scan."""

    schema_version: Literal["scanner-v1"] = "scanner-v1"
    versions: ScannerVersions
    requirement_extraction: RequirementExtraction


class TailoringDraftContextResponse(_StrictModel):
    """Narrow owner builder context for an owned, pending tailoring draft."""

    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    draft_cv_id: str
    draft_review: TailoringDraftReview
    job: TailoringJob
    scanner_context: TailoringDraftScannerContext


class TailoringReviewResponse(_StrictModel):
    protocol_version: Literal[4, 5, 6, 7, 8, 9, PROTOCOL_VERSION] = PROTOCOL_VERSION
    session_id: str
    application_id: str
    status: Literal["accepted", "rejected"]
    source_cv_id: str | None = None
    draft_cv_id: str | None = None
    cv_id: str | None = None
    scanner_result: ScanResult | None = None


TailoringErrorCode = Literal[
    "stale_target",
    "edited_draft",
    "preview_in_progress",
    "preview_limit",
    "quota",
    "inactive_capability",
    "invalid_session",
    "context_mismatch",
    "reservation_expired",
    "reservation_conflict",
    "request_id_reused",
    "candidate_invalid",
    "evaluation_mismatch",
    "draft_unavailable",
    "review_not_current",
    "source_changed",
    "application_unavailable",
]


class TailoringErrorResponse(_StrictModel):
    """Stable machine-readable code beside the human-readable detail."""

    code: TailoringErrorCode
    detail: str = Field(min_length=1, max_length=1_000)


__all__ = [
    "PROTOCOL_VERSION",
    "TAILORING_PROTOCOL_VERSION",
    "TAILORING_EVALUATION_VERSION",
    "TailoringCandidateCV",
    "TailoringAcceptRequest",
    "TailoringCodeExchange",
    "TailoringContextResponse",
    "TailoringDraftContextResponse",
    "TailoringDraftReview",
    "TailoringDraftScannerContext",
    "TailoringErrorCode",
    "TailoringErrorResponse",
    "TailoringEvaluation",
    "TailoringExchangeResponse",
    "TailoringJob",
    "TailoringPreviewRequest",
    "TailoringPreviewResponse",
    "TailoringPreviewReservationReleaseResponse",
    "TailoringPreviewReservationRequest",
    "TailoringPreviewReservationResponse",
    "TailoringReevaluateRequest",
    "TailoringReevaluateResponse",
    "TailoringReviewResponse",
    "TailoringSection",
    "TailoringSessionCreateResponse",
    "TailoringSessionState",
    "TailoringSessionStatusResponse",
    "TailoringSubmitRequest",
    "TailoringSubmitResponse",
    "TailoringScannerContext",
    "TailoringTemplate",
    "TailoringFitReview",
]
