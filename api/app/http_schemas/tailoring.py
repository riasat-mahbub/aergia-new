"""HTTP contracts for persistent-index whole-document tailoring (protocol v8).

The agent authors one complete CV candidate. There is deliberately no patch
or evidence-reference model here: the exchanged context is read-only input,
while the authenticated user remains the only actor that can accept the
result and change an application's linked CV.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.document_schema.models import Customizations, SectionInstance
from app.scanner.requirements import RequirementExtraction
from app.scanner.results import ScanResult, ScannerVersions
from app.http_schemas.tailoring_evaluation import (
    TAILORING_EVALUATION_VERSION,
    TailoringEditorialReview,
    TailoringEvaluation,
)


TAILORING_PROTOCOL_VERSION = 8
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
    # Historical drafts stay owner-reviewable; only protocol v8 can start or resume.
    protocol_version: Literal[4, 5, 6, 7, PROTOCOL_VERSION] = PROTOCOL_VERSION
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
    scanner: TailoringScannerContext
    # Compatibility convenience for clients that iterate requirements directly.
    # The scanner.requirement_extraction list is canonical.
    requirements: list[dict] = Field(max_length=100)
    templates: list[TailoringTemplate] = Field(max_length=32)
    selected_template_id: str
    selected_template_manifest: dict
    capabilities: dict = Field(max_length=100)
    capabilities_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    candidate_index: dict
    candidate_evidence: dict
    linked_cv_scan: ScanResult | None = None
    opportunities: list[dict] = Field(default_factory=list, max_length=100)
    retrieved_sources: list[dict] = Field(default_factory=list, max_length=100)
    writer_context_characters: int = Field(ge=0)
    effective_appearance: dict = Field(default_factory=dict, max_length=100)
    rendered_source: TailoringRenderArtifact | None = None
    evaluation_version: Literal[TAILORING_EVALUATION_VERSION] = TAILORING_EVALUATION_VERSION


class TailoringEvidenceRelation(_StrictModel):
    kind: Literal["technology", "method", "collaborator", "artifact", "domain", "outcome", "scope", "other"]
    value: str = Field(min_length=1, max_length=160)
    relation: Literal[
        "used", "deployed_with", "tested_with", "tested_across", "collaborated_with",
        "created", "documented", "within", "associated_with",
    ]


class TailoringEvidenceClaim(_StrictModel):
    id: str
    statement: str
    confidence_category: str
    associated_concepts: list[TailoringEvidenceRelation] = Field(default_factory=list)


class TailoringEvidenceGroup(_StrictModel):
    id: str
    kind: str
    identity: dict
    structured_facts: dict
    claims: list[TailoringEvidenceClaim]


class TailoringCandidateEvidence(_StrictModel):
    schema_version: Literal["candidate-evidence-v2"]
    groups: list[TailoringEvidenceGroup]


class TailoringEvidenceSourceRef(_StrictModel):
    source_id: str
    source_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    kind: str
    identity: dict
    structured_facts: dict
    narrative: str = Field(max_length=48_000)


class TailoringEvidenceVersions(_StrictModel):
    proposition_extractor: Literal["isolated-job-blind-worker"]
    proposition_model: str
    proposition_model_revision: str
    prompt_version: str
    schema_version: Literal["candidate-semantic-v1"]
    extractor_version: str


class TailoringEvidenceSourcesResponse(_StrictModel):
    """Bounded job-blind batch of stale or missing candidate sources."""

    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    stage: Literal["candidate_index_refresh"] = "candidate_index_refresh"
    session_id: str
    expires_at: datetime
    cache_state: Literal["warm", "stale", "missing", "mixed"]
    source_counts: dict[str, int]
    semantic_contract: TailoringEvidenceVersions
    sources: list[TailoringEvidenceSourceRef] = Field(max_length=24)


class TailoringPropositionConcept(_StrictModel):
    kind: Literal["technology", "method", "collaborator", "artifact", "domain", "outcome", "scope", "other"]
    value: str = Field(min_length=1, max_length=160)
    relation: Literal[
        "used", "deployed_with", "tested_with", "tested_across", "collaborated_with",
        "created", "documented", "within", "associated_with",
    ]


class TailoringExtractedProposition(_StrictModel):
    statement: str = Field(min_length=3, max_length=280)
    support: Literal["explicit"] = "explicit"
    source_excerpt: str = Field(min_length=1, max_length=250)
    associated_concepts: list[TailoringPropositionConcept] = Field(default_factory=list, max_length=30)


class TailoringSourcePropositions(_StrictModel):
    source_id: str
    source_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    claims: list[TailoringExtractedProposition] = Field(max_length=80)


class TailoringEvidenceSubmission(_StrictModel):
    # Validate each result independently so one malformed source does not
    # discard successful records from the same batch.
    source_results: list[Any] = Field(max_length=24)


class TailoringOpportunity(_StrictModel):
    requirement_id: str | None = None
    label: str
    current_cv_status: str
    kind: Literal["skill", "semantic_or_structured", "keyword"]
    missing_skills: list[str] = Field(default_factory=list)
    poorly_surfaced_skills: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list, max_length=3)
    operation: Literal["SURFACE", "PROMOTE", "REFRAME", "REVIEW"]
    source_note: str


class TailoringRetrievedSource(_StrictModel):
    source_id: str
    kind: str
    identity: dict
    structured_facts: dict
    source_fingerprint: str
    semantic_claims: list[dict] = Field(default_factory=list, max_length=80)
    narrative: str = Field(max_length=8_000)


class TailoringEvidenceContextResponse(_StrictModel):
    """Per-source result of a semantic refresh attempt."""

    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    stage: Literal["candidate_index_refresh_result"] = "candidate_index_refresh_result"
    session_id: str
    expires_at: datetime
    accepted_source_ids: list[str] = Field(default_factory=list, max_length=24)
    rejected_source_ids: list[str] = Field(default_factory=list, max_length=24)
    source_counts: dict[str, int]


class TailoringCandidateCV(_StrictModel):
    """The complete document write value accepted by protocol v8."""

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


class TailoringPreviewResponse(_StrictModel):
    format: Literal["pdf"] = "pdf"
    pdf_base64: str
    page_count: int = Field(ge=0)
    evaluation_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    render_warnings: list[str] = Field(default_factory=list, max_length=50)


class TailoringSourcePreviewResponse(_StrictModel):
    format: Literal["pdf"] = "pdf"
    pdf_base64: str
    page_count: int = Field(ge=0)
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    render_warnings: list[str] = Field(default_factory=list, max_length=50)


class TailoringRuntimeMetrics(_StrictModel):
    candidate_cache_state: Literal["warm", "stale", "missing", "mixed"] | None = None
    fresh_source_count: int = Field(default=0, ge=0)
    stale_source_count: int = Field(default=0, ge=0)
    missing_source_count: int = Field(default=0, ge=0)
    candidate_cue_calls: Literal[0] = 0
    semantic_indexing_calls: int = Field(default=0, ge=0)
    indexing_workers: int = Field(default=0, ge=0, le=1)
    semantic_refresh_duration_ms: int = Field(default=0, ge=0)
    semantic_batches_processed: int = Field(default=0, ge=0, le=1)
    accepted_semantic_sources: int = Field(default=0, ge=0)
    rejected_semantic_sources: int = Field(default=0, ge=0)
    source_counts_after_refresh: dict[str, int] = Field(default_factory=dict)
    sources_retrieved: int = Field(default=0, ge=0)
    writer_context_characters: int = Field(default=0, ge=0)
    main_writer_calls: int = Field(default=1, ge=0)
    renders: int = Field(default=0, ge=0)
    revision_count: int = Field(default=0, ge=0)


class TailoringSubmitRequest(_StrictModel):
    context_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    evaluation_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    expected_candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    candidate: TailoringCandidateCV
    review_notes: list[str] = Field(default_factory=list, max_length=20)
    editorial_review: TailoringEditorialReview
    runtime_metrics: TailoringRuntimeMetrics = Field(default_factory=TailoringRuntimeMetrics)

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
    evaluation_id: str
    candidate_hash: str
    candidate: TailoringCandidateCV
    scanner_result: ScanResult
    evaluation: TailoringEvaluation
    editorial_review: TailoringEditorialReview
    render_warnings: list[str] = Field(default_factory=list, max_length=50)
    review_notes: list[str] = Field(default_factory=list, max_length=20)


class TailoringReviewResponse(_StrictModel):
    protocol_version: Literal[4, 5, 6, 7, PROTOCOL_VERSION] = PROTOCOL_VERSION
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
    "TailoringEvidenceContextResponse",
    "TailoringEvidenceSourcesResponse",
    "TailoringEvidenceSubmission",
    "TailoringCV",
    "TailoringEditorialReview",
    "TailoringEvaluation",
    "TailoringExchangeResponse",
    "TailoringJob",
    "TailoringLibraryEntry",
    "TailoringPreviewRequest",
    "TailoringPreviewResponse",
    "TailoringSourcePreviewResponse",
    "TailoringRenderArtifact",
    "TailoringReviewResponse",
    "TailoringRuntimeMetrics",
    "TailoringSection",
    "TailoringSessionCreateResponse",
    "TailoringSessionState",
    "TailoringSessionStatusResponse",
    "TailoringSubmitRequest",
    "TailoringSubmitResponse",
    "TailoringScannerContext",
    "TailoringTemplate",
]
