"""Versioned result contracts for the independent scanner subsystems."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from app.scanner.requirements import (
    RequirementExtraction,
    RequirementImportance,
    ScannerModel,
)
from app.scanner.ats_results import AtsGuidance


class EvidenceStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    NOT_EVIDENCED = "not_evidenced"
    CONFLICTING = "conflicting"
    UNVERIFIABLE = "unverifiable"


class EvidenceMethod(StrEnum):
    STRUCTURED = "structured"
    TAXONOMY = "taxonomy"
    EXACT = "exact"
    FTS5 = "fts5"
    FUZZY = "fuzzy"
    DERIVED_STRUCTURED_CALCULATION = "derived_structured_calculation"
    SEMANTIC_RULE = "semantic_rule"
    HUMAN_ANNOTATION = "human_annotation"


class AnalysisStatus(StrEnum):
    EVALUATED = "evaluated"
    NOT_EVALUATED = "not_evaluated"
    FAILED = "failed"


class ScoreStatus(StrEnum):
    AVAILABLE = "available"
    INSUFFICIENT_SCORABLE_EVIDENCE = "insufficient_scorable_evidence"
    UNAVAILABLE = "unavailable"


class CVLocation(ScannerModel):
    section_id: str | None = Field(default=None, max_length=128)
    section_type: str | None = Field(default=None, max_length=100)
    entry_id: str | None = Field(default=None, max_length=128)
    field_path: str = Field(min_length=1, max_length=500)
    excerpt: str = Field(min_length=1, max_length=2_000)


class ConstraintEvidence(ScannerModel):
    constraint_id: str = Field(min_length=1, max_length=128)
    status: EvidenceStatus
    evidence_text: str | None = Field(default=None, max_length=2_000)


class Evidence(ScannerModel):
    id: str = Field(min_length=1, max_length=128)
    locations: list[CVLocation] = Field(min_length=1, max_length=50)
    concept_status: EvidenceStatus
    expectation_status: EvidenceStatus
    constraints: list[ConstraintEvidence] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)
    method: EvidenceMethod

    @model_validator(mode="after")
    def validate_unique_constraint_evidence(self) -> Evidence:
        constraint_ids = [item.constraint_id for item in self.constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("constraint evidence ids must be unique within an evidence bundle")
        return self


class ExpressionEvaluation(ScannerModel):
    node_id: str = Field(min_length=1, max_length=128)
    status: EvidenceStatus
    optional: bool = False
    mandatory_total: int = Field(default=0, ge=0)
    mandatory_supported: int = Field(default=0, ge=0)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    children: list[ExpressionEvaluation] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_counts(self) -> ExpressionEvaluation:
        if self.mandatory_supported > self.mandatory_total:
            raise ValueError("mandatory_supported cannot exceed mandatory_total")
        return self


class RequirementEvaluation(ScannerModel):
    requirement_id: str = Field(min_length=1, max_length=128)
    status: EvidenceStatus
    expression: ExpressionEvaluation


class SemanticAnalysis(ScannerModel):
    status: AnalysisStatus
    requirements: list[RequirementEvaluation] = Field(default_factory=list, max_length=100)
    evidence: list[Evidence] = Field(default_factory=list, max_length=1_000)
    summary: SemanticScoreSummary | None = None


class JobTextLocation(ScannerModel):
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=0)
    section_title: str | None = Field(default=None, max_length=500)
    section_purpose: str | None = Field(default=None, max_length=100)
    importance: RequirementImportance = RequirementImportance.UNKNOWN
    illustrative_example: bool = False


class LexicalVisibility(StrEnum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    VARIANT = "variant"
    ABSENT = "absent"
    UNVERIFIABLE = "unverifiable"


class LexicalEvidence(ScannerModel):
    location: CVLocation
    matched_text: str = Field(min_length=1, max_length=500)
    visibility: Literal["exact", "normalized", "variant"]


class LexicalTerm(ScannerModel):
    id: str = Field(min_length=1, max_length=128)
    term: str = Field(min_length=1, max_length=300)
    canonical_concept_id: str | None = Field(default=None, max_length=200)
    variants: list[str] = Field(default_factory=list, max_length=100)
    importance: RequirementImportance = RequirementImportance.UNKNOWN
    source_locations: list[JobTextLocation] = Field(min_length=1, max_length=100)
    illustrative_example: bool = False
    visibility: LexicalVisibility
    evidence: list[LexicalEvidence] = Field(default_factory=list, max_length=100)
    semantic_support: EvidenceStatus | None = None


class LexicalAnalysis(ScannerModel):
    status: AnalysisStatus
    terms: list[LexicalTerm] = Field(default_factory=list, max_length=1_000)
    summary: LexicalScoreSummary | None = None


class FindingSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class PresentationFinding(ScannerModel):
    code: str = Field(min_length=1, max_length=100)
    severity: FindingSeverity
    location: CVLocation | None = None
    evidence: str | None = Field(default=None, max_length=2_000)
    explanation: str = Field(min_length=1, max_length=2_000)


class BulletEvidenceClass(StrEnum):
    ACTION_ONLY = "action_only"
    ACTION_WITH_TECHNICAL_SPECIFICITY = "action_with_technical_specificity"
    ACTION_WITH_QUALITATIVE_OUTCOME = "action_with_qualitative_outcome"
    ACTION_WITH_QUANTIFIED_SCOPE = "action_with_quantified_scope"
    ACTION_WITH_QUANTIFIED_OUTCOME = "action_with_quantified_outcome"
    RESPONSIBILITY_ONLY = "responsibility_only"


class BulletAssessment(ScannerModel):
    location: CVLocation
    classification: BulletEvidenceClass


class PresentationQualityAnalysis(ScannerModel):
    status: AnalysisStatus
    findings: list[PresentationFinding] = Field(default_factory=list, max_length=1_000)
    bullet_assessments: list[BulletAssessment] = Field(default_factory=list, max_length=1_000)


class PDFRecoveryStatus(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"


class PDFCheck(ScannerModel):
    code: str = Field(min_length=1, max_length=100)
    status: PDFRecoveryStatus
    expected_count: int | None = Field(default=None, ge=0)
    recovered_count: int | None = Field(default=None, ge=0)
    evidence: list[str] = Field(default_factory=list, max_length=100)
    # Human-readable identities make recovery failures actionable without
    # exposing the raw renderer model.  These fields are optional so older
    # scanner-v1 snapshots remain readable while corrected scans populate
    # them.
    expected_items: list[str] = Field(default_factory=list, max_length=100)
    recovered_items: list[str] = Field(default_factory=list, max_length=100)
    missing_items: list[str] = Field(default_factory=list, max_length=100)
    affected_items: list[str] = Field(default_factory=list, max_length=100)
    explanation: str | None = Field(default=None, max_length=2_000)


class PDFTextRecoveryAnalysis(ScannerModel):
    status: PDFRecoveryStatus
    page_count: int | None = Field(default=None, ge=0)
    checks: list[PDFCheck] = Field(default_factory=list, max_length=100)
    summary: PDFRecoveryScoreSummary | None = None


class ScoreBucketSummary(ScannerModel):
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    scorable_fraction: float = Field(ge=0.0, le=1.0)
    scorable_weight: float = Field(ge=0.0)
    total_weight: float = Field(ge=0.0)
    requirement_count: int = Field(ge=0)


class SemanticScoreSummary(ScannerModel):
    status: ScoreStatus
    job_fit: float | None = Field(default=None, ge=0.0, le=1.0)
    # `scorable_fraction` is retained for previously persisted scanner-v1
    # results. New results populate the two explicit dimensions below.
    scorable_fraction: float = Field(ge=0.0, le=1.0)
    classified_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_scorable_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    classification_warning_code: Literal["low_requirement_classification_coverage"] | None = None
    qualification_fit: ScoreBucketSummary
    responsibility_alignment: ScoreBucketSummary
    preferred_fit: ScoreBucketSummary
    unclassified_requirement_count: int = Field(ge=0)
    supported_requirement_count: int | None = Field(default=None, ge=0)
    partial_requirement_count: int | None = Field(default=None, ge=0)
    not_evidenced_requirement_count: int | None = Field(default=None, ge=0)
    conflicting_requirement_count: int | None = Field(default=None, ge=0)
    unverifiable_requirement_count: int | None = Field(default=None, ge=0)
    unverifiable_component_count: int | None = Field(default=None, ge=0)
    # These shorter names remain readable in existing scanner-v1 snapshots.
    supported_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    not_evidenced_count: int = Field(ge=0)
    conflicting_count: int = Field(ge=0)
    unverifiable_count: int = Field(ge=0)
    required_constraint_conflicts: int = Field(ge=0)


class LexicalScoreSummary(ScannerModel):
    status: ScoreStatus
    visibility_score: float | None = Field(default=None, ge=0.0, le=1.0)
    scorable_fraction: float = Field(ge=0.0, le=1.0)
    exact_count: int = Field(ge=0)
    normalized_count: int = Field(ge=0)
    variant_count: int = Field(ge=0)
    absent_count: int = Field(ge=0)
    unverifiable_count: int = Field(ge=0)


class PDFRecoveryScoreSummary(ScannerModel):
    status: ScoreStatus
    recovery_score: float | None = Field(default=None, ge=0.0, le=1.0)
    scorable_fraction: float = Field(ge=0.0, le=1.0)
    scored_check_count: int = Field(ge=0)
    unavailable_check_count: int = Field(ge=0)


class ScannerVersions(ScannerModel):
    extractor_version: str = Field(min_length=1, max_length=100)
    matcher_version: str = Field(min_length=1, max_length=100)
    lexical_version: str = Field(min_length=1, max_length=100)
    quality_version: str = Field(min_length=1, max_length=100)
    pdf_analysis_version: str = Field(min_length=1, max_length=100)
    semantic_score_version: str | None = Field(default=None, max_length=100)
    lexical_score_version: str | None = Field(default=None, max_length=100)
    pdf_score_version: str | None = Field(default=None, max_length=100)
    classification_warning_version: str | None = Field(default=None, max_length=100)
    ats_guidance_version: str | None = Field(default=None, max_length=100)


class ScanInputFingerprints(ScannerModel):
    job_description_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cv_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pdf_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    render_input_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ScanResult(ScannerModel):
    schema_version: Literal["scanner-v1"] = "scanner-v1"
    created_at: datetime
    input_fingerprints: ScanInputFingerprints
    versions: ScannerVersions
    requirement_extraction: RequirementExtraction
    semantic: SemanticAnalysis
    lexical: LexicalAnalysis
    presentation_quality: PresentationQualityAnalysis
    pdf_recovery: PDFTextRecoveryAnalysis
    # New scans always populate this branch.  It remains optional so existing
    # scanner-v1 snapshots can still be read until their next forced scan.
    ats_guidance: AtsGuidance | None = None


ExpressionEvaluation.model_rebuild()
SemanticAnalysis.model_rebuild()
LexicalAnalysis.model_rebuild()
PDFTextRecoveryAnalysis.model_rebuild()
ScanResult.model_rebuild()


__all__ = [
    "AnalysisStatus",
    "BulletAssessment",
    "BulletEvidenceClass",
    "CVLocation",
    "ConstraintEvidence",
    "Evidence",
    "EvidenceMethod",
    "EvidenceStatus",
    "ExpressionEvaluation",
    "FindingSeverity",
    "JobTextLocation",
    "LexicalAnalysis",
    "LexicalScoreSummary",
    "LexicalEvidence",
    "LexicalTerm",
    "LexicalVisibility",
    "PDFCheck",
    "PDFRecoveryStatus",
    "PDFTextRecoveryAnalysis",
    "PDFRecoveryScoreSummary",
    "PresentationFinding",
    "PresentationQualityAnalysis",
    "RequirementEvaluation",
    "ScanInputFingerprints",
    "ScanResult",
    "ScoreBucketSummary",
    "ScoreStatus",
    "SemanticScoreSummary",
    "ScannerVersions",
    "SemanticAnalysis",
    "AtsGuidance",
]
