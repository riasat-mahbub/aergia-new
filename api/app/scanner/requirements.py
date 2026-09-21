"""Typed job-requirement contracts for scanner analysis.

These models intentionally keep concepts, expectations, constraints, and
logical structure independent. They do not encode a coverage score.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ScannerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementImportance(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNKNOWN = "unknown"


class RequirementFamily(StrEnum):
    TECHNICAL_SKILL = "technical_skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    RESPONSIBILITY = "responsibility"
    BEHAVIORAL = "behavioral"
    LANGUAGE = "language"
    ELIGIBILITY = "eligibility"
    OTHER = "other"


class SectionPurpose(StrEnum):
    CANDIDATE_RESPONSIBILITIES = "candidate_responsibilities"
    CANDIDATE_QUALIFICATIONS = "candidate_qualifications"
    CANDIDATE_PREFERENCES = "candidate_preferences"
    EMPLOYER_INFORMATION = "employer_information"
    BENEFITS = "benefits"
    LOGISTICS = "logistics"
    APPLICATION_PROCESS = "application_process"
    LEGAL = "legal"
    UNKNOWN = "unknown"


class CandidateSignalKind(StrEnum):
    SECTION_CONTEXT = "section_context"
    CANDIDATE_DIRECTED_LANGUAGE = "candidate_directed_language"
    CONCEPT_IN_CANDIDATE_SECTION = "concept_in_candidate_section"
    REQUIREMENT_MODEL_SPAN = "requirement_model_span"
    SENTENCE_CLASSIFIER = "sentence_classifier"
    OTHER = "other"


class CandidateSignalPolarity(StrEnum):
    SUPPORTS = "supports"
    OPPOSES = "opposes"


class SectionContext(ScannerModel):
    title: str | None = None
    purpose: SectionPurpose = SectionPurpose.UNKNOWN
    confidence: float = Field(ge=0.0, le=1.0)
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_source_range(self) -> SectionContext:
        if (self.source_start is None) != (self.source_end is None):
            raise ValueError("section source_start and source_end must be provided together")
        if self.source_start is not None and self.source_end < self.source_start:
            raise ValueError("section source_end must be greater than or equal to source_start")
        return self


class CandidateFacingSignal(ScannerModel):
    kind: CandidateSignalKind
    polarity: CandidateSignalPolarity
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str | None = None


class RequirementSource(ScannerModel):
    original_text: str = Field(min_length=1)
    source_start: int = Field(ge=0)
    source_end: int = Field(ge=0)
    section: SectionContext | None = None
    candidate_signals: list[CandidateFacingSignal] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    extractor_version: str = Field(min_length=1)

    @field_validator("original_text")
    @classmethod
    def require_nonblank_source(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("original_text must not be blank")
        return value

    @model_validator(mode="after")
    def validate_source_range(self) -> RequirementSource:
        if self.source_end <= self.source_start:
            raise ValueError("source_end must be greater than source_start")
        return self


class ImportanceEvidenceKind(StrEnum):
    EXPLICIT_REQUIRED = "explicit_required"
    EXPLICIT_PREFERRED = "explicit_preferred"
    SECTION_CONTEXT = "section_context"
    MODEL_LABEL = "model_label"
    NEGATED = "negated"


class ImportanceEvidence(ScannerModel):
    kind: ImportanceEvidenceKind
    interpretation: RequirementImportance
    source_text: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class ExpectationKind(StrEnum):
    FAMILIARITY = "familiarity"
    PROFICIENCY = "proficiency"
    PRACTICAL_USE = "practical_use"
    PRIOR_EXPERIENCE = "prior_experience"
    ABILITY_TO_PERFORM = "ability_to_perform"
    WILLINGNESS_TO_LEARN = "willingness_to_learn"
    INTEREST = "interest"
    DEVELOPMENTAL_INTEREST = "developmental_interest"
    CURIOSITY = "curiosity"
    PARTICIPATION = "participation"
    KNOWLEDGE = "knowledge"
    DEMONSTRATED_APPLICATION = "demonstrated_application"
    OTHER = "other"


class Concept(ScannerModel):
    name: str = Field(min_length=1, max_length=300)
    canonical_id: str | None = Field(default=None, max_length=200)
    family: str | None = Field(default=None, max_length=100)
    source_text: str | None = Field(default=None, max_length=2_000)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("concept name must not be blank")
        return value


class Expectation(ScannerModel):
    kind: ExpectationKind
    qualifier: str | None = Field(default=None, max_length=500)
    source_text: str | None = Field(default=None, max_length=2_000)
    confidence: float = Field(ge=0.0, le=1.0)


class ContextualModifierKind(StrEnum):
    GUIDANCE = "guidance"
    SUPERVISION = "supervision"
    LEARNING_PURPOSE = "learning_purpose"


class RequirementContextualModifier(ScannerModel):
    """Employer-provided work context, not an extra candidate qualification."""

    kind: ContextualModifierKind
    source_text: str = Field(min_length=1, max_length=500)
    scope: str | None = Field(default=None, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class ConstraintSource(ScannerModel):
    id: str = Field(min_length=1, max_length=128)
    source_text: str = Field(min_length=1, max_length=2_000)
    confidence: float = Field(ge=0.0, le=1.0)


class MinimumYearsConstraint(ConstraintSource):
    kind: Literal["minimum_years"]
    years: float = Field(gt=0.0)
    operator: Literal["gt", "gte"] = "gte"


class DegreeConstraint(ConstraintSource):
    kind: Literal["degree"]
    level: str = Field(min_length=1, max_length=100)
    field_of_study: str | None = Field(default=None, max_length=200)


class CertificationConstraint(ConstraintSource):
    kind: Literal["certification"]
    name: str = Field(min_length=1, max_length=200)


class LanguageProficiencyConstraint(ConstraintSource):
    kind: Literal["language_proficiency"]
    language: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=100)


class WorkAuthorizationConstraint(ConstraintSource):
    kind: Literal["work_authorization"]
    jurisdiction: str | None = Field(default=None, max_length=200)
    sponsorship_available: bool | None = None


class GeographicEligibilityConstraint(ConstraintSource):
    kind: Literal["geographic_eligibility"]
    locations: list[str] = Field(min_length=1, max_length=50)
    relation: Literal["any", "all"] = "any"


class NumericThresholdConstraint(ConstraintSource):
    kind: Literal["numeric_threshold"]
    operator: Literal["eq", "gt", "gte", "lt", "lte", "range"]
    value: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def validate_threshold(self) -> NumericThresholdConstraint:
        if self.operator == "range":
            if self.minimum is None or self.maximum is None or self.minimum > self.maximum:
                raise ValueError("range thresholds require ordered minimum and maximum values")
            if self.value is not None:
                raise ValueError("range thresholds cannot also set value")
        elif self.value is None or self.minimum is not None or self.maximum is not None:
            raise ValueError("non-range thresholds require value and cannot set minimum or maximum")
        return self


class OtherConstraint(ConstraintSource):
    kind: Literal["other"]
    description: str = Field(min_length=1, max_length=500)


Constraint: TypeAlias = Annotated[
    MinimumYearsConstraint
    | DegreeConstraint
    | CertificationConstraint
    | LanguageProficiencyConstraint
    | WorkAuthorizationConstraint
    | GeographicEligibilityConstraint
    | NumericThresholdConstraint
    | OtherConstraint,
    Field(discriminator="kind"),
]


class ExpressionModifiers(ScannerModel):
    optional: bool = False
    list_semantics: Literal["exhaustive", "examples", "unknown"] = "unknown"
    scope: str | None = Field(default=None, max_length=500)


class RequirementLeaf(ScannerModel):
    kind: Literal["leaf"]
    id: str = Field(min_length=1, max_length=128)
    concept: Concept
    expectation: Expectation
    constraints: list[Constraint] = Field(default_factory=list)
    modifiers: ExpressionModifiers = Field(default_factory=ExpressionModifiers)
    confidence: float = Field(ge=0.0, le=1.0)


class AllExpression(ScannerModel):
    kind: Literal["all"]
    id: str = Field(min_length=1, max_length=128)
    children: list[ExpressionNode] = Field(min_length=2, max_length=100)
    modifiers: ExpressionModifiers = Field(default_factory=ExpressionModifiers)
    confidence: float = Field(ge=0.0, le=1.0)


class AnyExpression(ScannerModel):
    kind: Literal["any"]
    id: str = Field(min_length=1, max_length=128)
    children: list[ExpressionNode] = Field(min_length=2, max_length=100)
    modifiers: ExpressionModifiers = Field(default_factory=ExpressionModifiers)
    confidence: float = Field(ge=0.0, le=1.0)


ExpressionNode: TypeAlias = Annotated[
    RequirementLeaf | AllExpression | AnyExpression,
    Field(discriminator="kind"),
]

AllExpression.model_rebuild()
AnyExpression.model_rebuild()


class Requirement(ScannerModel):
    id: str = Field(min_length=1, max_length=128)
    source: RequirementSource
    importance: RequirementImportance
    importance_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    importance_evidence: list[ImportanceEvidence] = Field(default_factory=list, max_length=50)
    family: RequirementFamily = RequirementFamily.OTHER
    weight: float = Field(ge=0.0)
    expression: ExpressionNode
    contextual_modifiers: list[RequirementContextualModifier] = Field(default_factory=list, max_length=50)


class RequirementExtraction(ScannerModel):
    status: Literal["evaluated", "partial", "failed"]
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    extractor_version: str = Field(min_length=1, max_length=100)
    requirements: list[Requirement] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=100)


__all__ = [
    "AllExpression",
    "AnyExpression",
    "CandidateFacingSignal",
    "CandidateSignalKind",
    "CandidateSignalPolarity",
    "CertificationConstraint",
    "Concept",
    "Constraint",
    "ContextualModifierKind",
    "DegreeConstraint",
    "Expectation",
    "ExpectationKind",
    "ExpressionModifiers",
    "ExpressionNode",
    "GeographicEligibilityConstraint",
    "ImportanceEvidence",
    "ImportanceEvidenceKind",
    "LanguageProficiencyConstraint",
    "MinimumYearsConstraint",
    "NumericThresholdConstraint",
    "OtherConstraint",
    "Requirement",
    "RequirementContextualModifier",
    "RequirementExtraction",
    "RequirementImportance",
    "RequirementFamily",
    "RequirementLeaf",
    "RequirementSource",
    "SectionContext",
    "SectionPurpose",
    "WorkAuthorizationConstraint",
]
