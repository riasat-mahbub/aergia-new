"""Typed contracts for server-owned tailoring evaluation (protocol v5)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.scanner.requirements import RequirementImportance
from app.scanner.results import EvidenceStatus, LexicalVisibility


TAILORING_EVALUATION_VERSION = "tailoring-evaluation-v1"

TailoringReadinessStatus = Literal["ready", "ready_with_review", "revise", "blocked"]
TransitionClassification = Literal[
    "improved",
    "regressed",
    "unchanged",
    "changed_needs_review",
]
PassChangeClassification = Literal["fixed", "introduced", "improved", "regressed"]
TailoringIssueKind = Literal["blocker", "review", "recommendation", "non_actionable_gap"]
TailoringIssueCategory = Literal[
    "semantic",
    "lexical",
    "ats",
    "resume_quality",
    "pdf_recovery",
    "inference",
    "comparison",
    "user_constraint",
    "fabrication",
    "render",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TailoringInferenceNote(_StrictModel):
    """A declared logical leap that should be visible during user review."""

    claim: str = Field(min_length=1, max_length=500)
    basis: list[str] = Field(min_length=1, max_length=8)
    confidence: Literal["entailed", "strong", "reasonable", "speculative"]
    section_id: str | None = Field(default=None, max_length=128)
    item_id: str | None = Field(default=None, max_length=128)
    field_path: str | None = Field(default=None, max_length=256)
    review_recommended: bool = True


class TailoringIssue(_StrictModel):
    id: str = Field(min_length=1, max_length=180)
    kind: TailoringIssueKind
    category: TailoringIssueCategory
    message: str = Field(min_length=1, max_length=2_000)
    detail: str | None = Field(default=None, max_length=2_000)
    priority: Literal["high", "normal", "low"] = "normal"
    requirement_id: str | None = Field(default=None, max_length=128)
    term_id: str | None = Field(default=None, max_length=128)
    code: str | None = Field(default=None, max_length=128)
    importance: RequirementImportance | None = None


class TailoringRequirementTransition(_StrictModel):
    requirement_id: str = Field(min_length=1, max_length=128)
    importance: RequirementImportance
    source_status: EvidenceStatus | None = None
    candidate_status: EvidenceStatus | None = None
    classification: TransitionClassification
    label: str = Field(min_length=1, max_length=500)


class TailoringKeywordTransition(_StrictModel):
    term_id: str = Field(min_length=1, max_length=128)
    term: str = Field(min_length=1, max_length=300)
    source_visibility: LexicalVisibility | None = None
    candidate_visibility: LexicalVisibility | None = None
    semantic_support: EvidenceStatus | None = None
    classification: TransitionClassification


class TailoringSourceComparison(_StrictModel):
    available: bool
    requirement_transitions: list[TailoringRequirementTransition] = Field(default_factory=list, max_length=100)
    keyword_transitions: list[TailoringKeywordTransition] = Field(default_factory=list, max_length=1_000)


class TailoringPassChange(_StrictModel):
    id: str = Field(min_length=1, max_length=180)
    area: Literal["semantic", "lexical", "ats", "resume_quality", "pdf_recovery"]
    classification: PassChangeClassification
    message: str = Field(min_length=1, max_length=2_000)
    requirement_id: str | None = Field(default=None, max_length=128)
    term_id: str | None = Field(default=None, max_length=128)


class TailoringPreviousPassComparison(_StrictModel):
    available: bool
    previous_candidate_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    changes: list[TailoringPassChange] = Field(default_factory=list, max_length=200)
    job_fit_delta: float | None = None
    term_visibility_delta: float | None = None


class TailoringNumericDimension(_StrictModel):
    """A dimension that already has a scanner-owned numeric meaning."""

    source: float | None = Field(default=None, ge=0.0, le=1.0)
    candidate: float | None = Field(default=None, ge=0.0, le=1.0)


class TailoringFindingDimension(_StrictModel):
    """A findings-based dimension; deliberately has no invented score."""

    source_count: int | None = Field(default=None, ge=0)
    candidate_count: int = Field(ge=0)
    candidate_error_count: int = Field(default=0, ge=0)
    candidate_warning_count: int = Field(default=0, ge=0)
    candidate_info_count: int = Field(default=0, ge=0)


class TailoringDimensions(_StrictModel):
    job_fit: TailoringNumericDimension
    keywords: TailoringNumericDimension
    ats: TailoringFindingDimension
    resume_quality: TailoringFindingDimension
    pdf_recovery: TailoringNumericDimension


class TailoringReadiness(_StrictModel):
    status: TailoringReadinessStatus
    submission_allowed: bool
    reasons: list[str] = Field(default_factory=list, max_length=20)


class TailoringEvaluation(_StrictModel):
    version: Literal[TAILORING_EVALUATION_VERSION] = TAILORING_EVALUATION_VERSION
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    pass_number: int = Field(default=1, ge=1, le=5)
    source_comparison: TailoringSourceComparison
    previous_pass_comparison: TailoringPreviousPassComparison
    dimensions: TailoringDimensions
    improvements: list[TailoringIssue] = Field(default_factory=list, max_length=100)
    regressions: list[TailoringIssue] = Field(default_factory=list, max_length=100)
    blockers: list[TailoringIssue] = Field(default_factory=list, max_length=100)
    review_items: list[TailoringIssue] = Field(default_factory=list, max_length=100)
    recommendations: list[TailoringIssue] = Field(default_factory=list, max_length=100)
    non_actionable_gaps: list[TailoringIssue] = Field(default_factory=list, max_length=100)
    inference_notes: list[TailoringInferenceNote] = Field(default_factory=list, max_length=20)
    render_warnings: list[str] = Field(default_factory=list, max_length=50)
    readiness: TailoringReadiness


class TailoringEditorialFinding(_StrictModel):
    category: Literal[
        "evidence_selection",
        "framing",
        "impact",
        "clarity",
        "natural_writing",
        "visual_balance",
    ]
    severity: Literal["important", "polish", "blocking"]
    section_id: str = Field(min_length=1, max_length=128)
    item_id: str | None = Field(default=None, max_length=128)
    field_path: str | None = Field(default=None, max_length=256)
    excerpt: str = Field(min_length=1, max_length=2_000)
    problem: str = Field(min_length=1, max_length=1_000)
    recommended_change: str = Field(min_length=1, max_length=1_000)


class TailoringEditorialReview(_StrictModel):
    review_version: Literal["aergia-editorial-review-v1"] = "aergia-editorial-review-v1"
    candidate_hash: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    pass_number: int = Field(ge=1, le=5)
    findings: list[TailoringEditorialFinding] = Field(default_factory=list, max_length=50)
    inference_notes: list[TailoringInferenceNote] = Field(default_factory=list, max_length=20)


__all__ = [
    "TAILORING_EVALUATION_VERSION",
    "TailoringDimensions",
    "TailoringEditorialFinding",
    "TailoringEditorialReview",
    "TailoringEvaluation",
    "TailoringFindingDimension",
    "TailoringInferenceNote",
    "TailoringIssue",
    "TailoringKeywordTransition",
    "TailoringNumericDimension",
    "TailoringPassChange",
    "TailoringPreviousPassComparison",
    "TailoringReadiness",
    "TailoringRequirementTransition",
    "TailoringSourceComparison",
]
