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


class JobTextLocation(ScannerModel):
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=0)
    section_title: str | None = Field(default=None, max_length=500)
    section_purpose: str | None = Field(default=None, max_length=100)


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
    visibility: LexicalVisibility
    evidence: list[LexicalEvidence] = Field(default_factory=list, max_length=100)


class LexicalAnalysis(ScannerModel):
    status: AnalysisStatus
    terms: list[LexicalTerm] = Field(default_factory=list, max_length=1_000)


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
    explanation: str | None = Field(default=None, max_length=2_000)


class PDFTextRecoveryAnalysis(ScannerModel):
    status: PDFRecoveryStatus
    page_count: int | None = Field(default=None, ge=0)
    checks: list[PDFCheck] = Field(default_factory=list, max_length=100)


class ScannerVersions(ScannerModel):
    extractor_version: str = Field(min_length=1, max_length=100)
    matcher_version: str = Field(min_length=1, max_length=100)
    lexical_version: str = Field(min_length=1, max_length=100)
    quality_version: str = Field(min_length=1, max_length=100)
    pdf_analysis_version: str = Field(min_length=1, max_length=100)


class ScanInputFingerprints(ScannerModel):
    job_description_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cv_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pdf_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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


ExpressionEvaluation.model_rebuild()


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
    "LexicalEvidence",
    "LexicalTerm",
    "LexicalVisibility",
    "PDFCheck",
    "PDFRecoveryStatus",
    "PDFTextRecoveryAnalysis",
    "PresentationFinding",
    "PresentationQualityAnalysis",
    "RequirementEvaluation",
    "ScanInputFingerprints",
    "ScanResult",
    "ScannerVersions",
    "SemanticAnalysis",
]
