"""Versioned deterministic score projections over categorical scanner results."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from app.scanner.requirements import (
    AllExpression,
    AnyExpression,
    ExamplesExpression,
    ExpressionNode,
    Requirement,
    RequirementImportance,
    RequirementLeaf,
    SectionPurpose,
)
from app.scanner.results import (
    AnalysisStatus,
    Evidence,
    EvidenceStatus,
    ExpressionEvaluation,
    LexicalAnalysis,
    LexicalScoreSummary,
    LexicalTerm,
    LexicalVisibility,
    PDFRecoveryScoreSummary,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
    RequirementEvaluation,
    ScoreBucketSummary,
    ScoreStatus,
    SemanticAnalysis,
    SemanticScoreSummary,
)


SEMANTIC_SCORE_VERSION = "job-fit-v2"
CLASSIFICATION_WARNING_VERSION = "classification-coverage-warning-v1"
LEXICAL_SCORE_VERSION = "term-visibility-v2"
PDF_SCORE_VERSION = "pdf-recovery-score-v1"
MINIMUM_JOB_FIT_SCORABLE_FRACTION = 0.70
MINIMUM_CLASSIFICATION_COVERAGE_WARNING_FRACTION = 0.70
CLASSIFICATION_COVERAGE_WARNING_CODE = "low_requirement_classification_coverage"

_STATUS_VALUE = {
    EvidenceStatus.SUPPORTED: 1.0,
    EvidenceStatus.PARTIAL: 0.5,
    EvidenceStatus.NOT_EVIDENCED: 0.0,
    EvidenceStatus.CONFLICTING: 0.0,
}
_BUCKET_WEIGHTS = {
    "qualification": 0.70,
    "responsibility": 0.25,
    "preferred": 0.05,
}
_LEXICAL_VALUES = {
    LexicalVisibility.EXACT: 1.0,
    LexicalVisibility.NORMALIZED: 0.95,
    LexicalVisibility.VARIANT: 0.80,
    LexicalVisibility.ABSENT: 0.0,
}
_PDF_WEIGHTS = {
    "text_retention": 0.35,
    "reading_order": 0.25,
    "contact_recovery": 0.15,
    "section_heading_recovery": 0.10,
    "entry_recovery": 0.10,
    "link_recovery": 0.05,
}


@dataclass(frozen=True, slots=True)
class _ScoreProjection:
    earned: float
    scorable_units: float
    total_units: float

    @property
    def score(self) -> float | None:
        if self.scorable_units <= 0:
            return None
        return self.earned / self.scorable_units

    @property
    def scorable_fraction(self) -> float:
        if self.total_units <= 0:
            return 0.0
        return min(1.0, self.scorable_units / self.total_units)


def _status_projection(status: EvidenceStatus, *, optional: bool = False) -> _ScoreProjection:
    if optional:
        return _ScoreProjection(earned=0.0, scorable_units=0.0, total_units=0.0)
    if status is EvidenceStatus.UNVERIFIABLE:
        return _ScoreProjection(earned=0.0, scorable_units=0.0, total_units=1.0)
    value = _STATUS_VALUE[status]
    return _ScoreProjection(earned=value, scorable_units=1.0, total_units=1.0)


def _expression_projection(
    expression: ExpressionNode,
    evaluation: ExpressionEvaluation,
) -> _ScoreProjection:
    optional = evaluation.optional
    if isinstance(expression, RequirementLeaf):
        return _status_projection(evaluation.status, optional=optional)
    if isinstance(expression, ExamplesExpression):
        # Examples share one parent obligation. The categorical examples
        # evaluator decides whether their evidence is partial or sufficient.
        return _status_projection(evaluation.status, optional=optional)

    pairs = list(zip(expression.children, evaluation.children, strict=True))
    if isinstance(expression, AllExpression):
        children = [
            _expression_projection(child, result)
            for child, result in pairs
            if not result.optional
        ]
        return _ScoreProjection(
            earned=sum(item.earned for item in children),
            scorable_units=sum(item.scorable_units for item in children),
            total_units=sum(item.total_units for item in children),
        )

    if isinstance(expression, AnyExpression):
        children = [_expression_projection(child, result) for child, result in pairs if not result.optional]
        scores = [item.score for item in children if item.score is not None]
        if not children:
            return _ScoreProjection(earned=0.0, scorable_units=0.0, total_units=0.0)
        best = max(scores, default=0.0)
        # One complete alternative fully establishes an ANY expression. Until
        # then, coverage records the share of alternatives the CV can assess.
        coverage = 1.0 if best >= 1.0 else sum(item.scorable_fraction for item in children) / len(children)
        return _ScoreProjection(earned=best * coverage, scorable_units=coverage, total_units=1.0)

    raise TypeError(f"Unsupported expression node: {type(expression).__name__}")


def _walk_required_constraint_leaves(node: ExpressionNode) -> list[RequirementLeaf]:
    if node.modifiers.optional:
        return []
    if isinstance(node, RequirementLeaf):
        return [node]
    if isinstance(node, ExamplesExpression):
        # An illustrative example does not create a hard-constraint obligation.
        return _walk_required_constraint_leaves(node.subject)
    return [
        leaf
        for child in node.children
        for leaf in _walk_required_constraint_leaves(child)
    ]


def _count_unverifiable_components(
    expression: ExpressionNode,
    evaluation: ExpressionEvaluation,
) -> int:
    """Count unverifiable mandatory leaves without conflating them with parents."""

    if expression.modifiers.optional or evaluation.optional:
        return 0
    if isinstance(expression, RequirementLeaf):
        return int(evaluation.status is EvidenceStatus.UNVERIFIABLE)
    if isinstance(expression, ExamplesExpression):
        # The subject is the obligation. Illustrative children are optional
        # evidence vocabulary and must not inflate component counts.
        subject_result = next(
            (child for child in evaluation.children if child.node_id == expression.subject.id),
            None,
        )
        return (
            _count_unverifiable_components(expression.subject, subject_result)
            if subject_result is not None
            else 0
        )

    evaluation_by_id = {child.node_id: child for child in evaluation.children}
    return sum(
        _count_unverifiable_components(child, evaluation_by_id[child.id])
        for child in expression.children
        if not child.modifiers.optional
        and child.id in evaluation_by_id
        and not evaluation_by_id[child.id].optional
    )


def _bucket_for(requirement: Requirement) -> str | None:
    if requirement.importance is RequirementImportance.UNKNOWN:
        return None
    if requirement.importance is RequirementImportance.PREFERRED:
        return "preferred"
    purpose = requirement.source.section.purpose if requirement.source.section else SectionPurpose.UNKNOWN
    if purpose is SectionPurpose.CANDIDATE_RESPONSIBILITIES:
        return "responsibility"
    if purpose is SectionPurpose.CANDIDATE_QUALIFICATIONS:
        return "qualification"
    if requirement.family.value == "responsibility":
        return "responsibility"
    return "qualification"


@dataclass(slots=True)
class _BucketAccumulator:
    earned: float = 0.0
    scorable_weight: float = 0.0
    total_weight: float = 0.0
    requirement_count: int = 0

    def add(self, weight: float, projection: _ScoreProjection) -> None:
        if projection.total_units <= 0:
            return
        self.total_weight += weight
        self.scorable_weight += weight * projection.scorable_fraction
        if projection.score is not None:
            self.earned += weight * projection.scorable_fraction * projection.score
        self.requirement_count += 1

    def summary(self) -> ScoreBucketSummary:
        score = self.earned / self.scorable_weight if self.scorable_weight > 0 else None
        fraction = self.scorable_weight / self.total_weight if self.total_weight > 0 else 0.0
        return ScoreBucketSummary(
            score=score,
            scorable_fraction=fraction,
            scorable_weight=self.scorable_weight,
            total_weight=self.total_weight,
            requirement_count=self.requirement_count,
        )


def _required_constraint_conflicts(
    requirements: Sequence[Requirement],
    evidence: Sequence[Evidence],
) -> int:
    required_leaf_constraints: dict[str, tuple[str, set[str]]] = {}
    for requirement in requirements:
        if requirement.importance is not RequirementImportance.REQUIRED:
            continue
        for leaf in _walk_required_constraint_leaves(requirement.expression):
            required_leaf_constraints[leaf.id] = (
                requirement.id,
                {constraint.id for constraint in leaf.constraints},
            )
    conflicts: set[tuple[str, str]] = set()
    for item in evidence:
        evidence_id = item.id
        leaf_id = next(
            (
                candidate
                for candidate in sorted(required_leaf_constraints, key=len, reverse=True)
                if evidence_id.startswith(f"ev-{candidate}-")
                and evidence_id.removeprefix(f"ev-{candidate}-").isdigit()
            ),
            None,
        )
        if leaf_id is None:
            continue
        requirement_id, constraint_ids = required_leaf_constraints[leaf_id]
        for constraint in item.constraints:
            constraint_id = constraint.constraint_id
            if constraint_id in constraint_ids and constraint.status is EvidenceStatus.CONFLICTING:
                conflicts.add((requirement_id, constraint_id))
    return len(conflicts)


def score_semantic_analysis(
    analysis: SemanticAnalysis,
    requirements: Sequence[Requirement],
) -> SemanticScoreSummary:
    """Project categorical requirement results into the versioned job-fit score."""

    evaluation_by_id: dict[str, RequirementEvaluation] = {
        item.requirement_id: item for item in analysis.requirements
    }
    buckets = {name: _BucketAccumulator() for name in _BUCKET_WEIGHTS}
    status_counts = {status: 0 for status in EvidenceStatus}
    unclassified = 0
    total_requirement_weight = 0.0
    classified_requirement_weight = 0.0
    evidence_scorable_weight = 0.0
    unverifiable_component_count = 0
    for requirement in requirements:
        total_requirement_weight += requirement.weight
        bucket_name = _bucket_for(requirement)
        if bucket_name is None:
            unclassified += 1
        else:
            classified_requirement_weight += requirement.weight

        evaluation = evaluation_by_id.get(requirement.id)
        if evaluation is not None:
            status_counts[evaluation.status] += 1
            unverifiable_component_count += _count_unverifiable_components(
                requirement.expression,
                evaluation.expression,
            )
        if bucket_name is None:
            continue
        projection = (
            _expression_projection(requirement.expression, evaluation.expression)
            if evaluation is not None
            else _status_projection(EvidenceStatus.UNVERIFIABLE)
        )
        evidence_scorable_weight += requirement.weight * projection.scorable_fraction
        buckets[bucket_name].add(
            requirement.weight,
            projection,
        )

    classified_fraction = (
        classified_requirement_weight / total_requirement_weight
        if total_requirement_weight > 0
        else 0.0
    )
    evidence_scorable_fraction = (
        evidence_scorable_weight / classified_requirement_weight
        if classified_requirement_weight > 0
        else 0.0
    )
    bucket_summaries = {name: bucket.summary() for name, bucket in buckets.items()}
    present = {
        name: summary
        for name, summary in bucket_summaries.items()
        if summary.total_weight > 0
    }
    scored_bucket_weight = sum(
        _BUCKET_WEIGHTS[name] * summary.scorable_fraction
        for name, summary in present.items()
        if summary.score is not None
    )
    job_fit = (
        sum(
            _BUCKET_WEIGHTS[name] * summary.scorable_fraction * summary.score
            for name, summary in present.items()
            if summary.score is not None
        )
        / scored_bucket_weight
        if scored_bucket_weight > 0
        else None
    )
    if analysis.status is not AnalysisStatus.EVALUATED:
        score_status = ScoreStatus.UNAVAILABLE
        job_fit = None
    elif evidence_scorable_fraction < MINIMUM_JOB_FIT_SCORABLE_FRACTION:
        score_status = ScoreStatus.INSUFFICIENT_SCORABLE_EVIDENCE
        job_fit = None
    elif job_fit is None:
        score_status = ScoreStatus.UNAVAILABLE
    else:
        score_status = ScoreStatus.AVAILABLE

    return SemanticScoreSummary(
        status=score_status,
        job_fit=job_fit,
        # Keep the legacy alias aligned with the explicit evidence fraction.
        scorable_fraction=evidence_scorable_fraction,
        classified_fraction=classified_fraction,
        evidence_scorable_fraction=evidence_scorable_fraction,
        classification_warning_code=(
            CLASSIFICATION_COVERAGE_WARNING_CODE
            if classified_fraction < MINIMUM_CLASSIFICATION_COVERAGE_WARNING_FRACTION
            else None
        ),
        qualification_fit=bucket_summaries["qualification"],
        responsibility_alignment=bucket_summaries["responsibility"],
        preferred_fit=bucket_summaries["preferred"],
        unclassified_requirement_count=unclassified,
        supported_requirement_count=status_counts[EvidenceStatus.SUPPORTED],
        partial_requirement_count=status_counts[EvidenceStatus.PARTIAL],
        not_evidenced_requirement_count=status_counts[EvidenceStatus.NOT_EVIDENCED],
        conflicting_requirement_count=status_counts[EvidenceStatus.CONFLICTING],
        unverifiable_requirement_count=status_counts[EvidenceStatus.UNVERIFIABLE],
        unverifiable_component_count=unverifiable_component_count,
        supported_count=status_counts[EvidenceStatus.SUPPORTED],
        partial_count=status_counts[EvidenceStatus.PARTIAL],
        not_evidenced_count=status_counts[EvidenceStatus.NOT_EVIDENCED],
        conflicting_count=status_counts[EvidenceStatus.CONFLICTING],
        unverifiable_count=status_counts[EvidenceStatus.UNVERIFIABLE],
        required_constraint_conflicts=_required_constraint_conflicts(requirements, analysis.evidence),
    )


def _lexical_term_weight(term: LexicalTerm) -> float:
    weights: list[float] = []
    for location in term.source_locations:
        purpose = str(location.section_purpose or "")
        if location.importance is RequirementImportance.PREFERRED or (
            location.importance is RequirementImportance.UNKNOWN
            and term.importance is RequirementImportance.PREFERRED
        ):
            weights.append(0.35)
        elif purpose == "candidate_qualifications":
            weights.append(1.0)
        elif purpose == "candidate_responsibilities":
            weights.append(0.65)
        elif purpose == "candidate_preferences":
            weights.append(0.35)
        else:
            weights.append(0.40)
    return max(weights, default=0.35 if term.importance is RequirementImportance.PREFERRED else 0.40)


def _is_illustrative_example(term: LexicalTerm) -> bool:
    return term.illustrative_example and bool(term.source_locations) and all(
        location.illustrative_example for location in term.source_locations
    )


def score_lexical_analysis(analysis: LexicalAnalysis) -> LexicalScoreSummary:
    """Score only literal visibility; semantic support never adds lexical credit."""

    counts = {visibility: 0 for visibility in LexicalVisibility}
    for term in analysis.terms:
        if not _is_illustrative_example(term):
            counts[term.visibility] += 1
    if analysis.status is not AnalysisStatus.EVALUATED:
        return LexicalScoreSummary(
            status=ScoreStatus.UNAVAILABLE,
            visibility_score=None,
            scorable_fraction=0.0,
            exact_count=counts[LexicalVisibility.EXACT],
            normalized_count=counts[LexicalVisibility.NORMALIZED],
            variant_count=counts[LexicalVisibility.VARIANT],
            absent_count=counts[LexicalVisibility.ABSENT],
            unverifiable_count=counts[LexicalVisibility.UNVERIFIABLE],
        )
    weighted_total = 0.0
    scorable_weight = 0.0
    earned = 0.0
    for term in analysis.terms:
        if _is_illustrative_example(term):
            continue
        weight = _lexical_term_weight(term)
        weighted_total += weight
        value = _LEXICAL_VALUES.get(term.visibility)
        if value is None:
            continue
        scorable_weight += weight
        earned += weight * value
    score = earned / scorable_weight if scorable_weight > 0 else None
    scorable_fraction = scorable_weight / weighted_total if weighted_total > 0 else 0.0
    return LexicalScoreSummary(
        status=ScoreStatus.AVAILABLE if score is not None else ScoreStatus.UNAVAILABLE,
        visibility_score=score,
        scorable_fraction=scorable_fraction,
        exact_count=counts[LexicalVisibility.EXACT],
        normalized_count=counts[LexicalVisibility.NORMALIZED],
        variant_count=counts[LexicalVisibility.VARIANT],
        absent_count=counts[LexicalVisibility.ABSENT],
        unverifiable_count=counts[LexicalVisibility.UNVERIFIABLE],
    )


def _pdf_check_score(code: str, status: PDFRecoveryStatus, expected: int | None, recovered: int | None) -> float | None:
    if code not in _PDF_WEIGHTS or status is PDFRecoveryStatus.UNAVAILABLE:
        return None
    if expected is None or recovered is None or expected <= 0:
        return None
    return min(1.0, max(0.0, recovered / expected))


def score_pdf_recovery(analysis: PDFTextRecoveryAnalysis) -> PDFRecoveryScoreSummary:
    """Score Aergia's PDF recovery checks while retaining unavailable/resource findings."""

    if analysis.status is PDFRecoveryStatus.UNAVAILABLE:
        return PDFRecoveryScoreSummary(
            status=ScoreStatus.UNAVAILABLE,
            recovery_score=None,
            scorable_fraction=0.0,
            scored_check_count=0,
            unavailable_check_count=0,
        )

    scored_weight = 0.0
    weighted_score = 0.0
    scored_count = 0
    unavailable_count = 0
    for check in analysis.checks:
        if check.code not in _PDF_WEIGHTS:
            continue
        weight = _PDF_WEIGHTS[check.code]
        value = _pdf_check_score(check.code, check.status, check.expected_count, check.recovered_count)
        if value is None:
            unavailable_count += 1
            continue
        scored_weight += weight
        weighted_score += value * weight
        scored_count += 1
    recovery_score = weighted_score / scored_weight if scored_weight > 0 else None
    return PDFRecoveryScoreSummary(
        status=ScoreStatus.AVAILABLE if recovery_score is not None else ScoreStatus.UNAVAILABLE,
        recovery_score=recovery_score,
        scorable_fraction=min(1.0, scored_weight / sum(_PDF_WEIGHTS.values())),
        scored_check_count=scored_count,
        unavailable_check_count=unavailable_count,
    )


__all__ = [
    "CLASSIFICATION_COVERAGE_WARNING_CODE",
    "CLASSIFICATION_WARNING_VERSION",
    "LEXICAL_SCORE_VERSION",
    "MINIMUM_CLASSIFICATION_COVERAGE_WARNING_FRACTION",
    "MINIMUM_JOB_FIT_SCORABLE_FRACTION",
    "PDF_SCORE_VERSION",
    "SEMANTIC_SCORE_VERSION",
    "score_lexical_analysis",
    "score_pdf_recovery",
    "score_semantic_analysis",
]
