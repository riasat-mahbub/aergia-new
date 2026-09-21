"""Cross-reference independent scanner results for user-facing explanations."""

from __future__ import annotations

from collections.abc import Sequence

from app.scanner.matching import concepts_semantically_overlap
from app.scanner.requirements import (
    AllExpression,
    AnyExpression,
    Concept,
    ExamplesExpression,
    ExpressionNode,
    Requirement,
    RequirementLeaf,
)
from app.scanner.results import (
    AnalysisStatus,
    EvidenceStatus,
    ExpressionEvaluation,
    LexicalAnalysis,
    SemanticAnalysis,
)


def _leaf_evaluations(
    expression: ExpressionNode,
    evaluation: ExpressionEvaluation,
) -> list[tuple[RequirementLeaf, EvidenceStatus]]:
    if isinstance(expression, RequirementLeaf):
        return [(expression, evaluation.status)]
    if isinstance(expression, ExamplesExpression):
        children = [expression.subject, *expression.examples]
    elif isinstance(expression, (AllExpression, AnyExpression)):
        children = expression.children
    else:  # pragma: no cover - guarded by the discriminated expression union
        return []
    return [
        pair
        for child, child_evaluation in zip(children, evaluation.children, strict=True)
        for pair in _leaf_evaluations(child, child_evaluation)
    ]


def _combined_status(statuses: Sequence[EvidenceStatus]) -> EvidenceStatus | None:
    if not statuses:
        return None
    if EvidenceStatus.SUPPORTED in statuses:
        return EvidenceStatus.SUPPORTED
    if EvidenceStatus.PARTIAL in statuses:
        return EvidenceStatus.PARTIAL
    if EvidenceStatus.CONFLICTING in statuses:
        return EvidenceStatus.CONFLICTING
    if EvidenceStatus.NOT_EVIDENCED in statuses:
        return EvidenceStatus.NOT_EVIDENCED
    return EvidenceStatus.UNVERIFIABLE


def link_lexical_semantic_support(
    lexical: LexicalAnalysis,
    requirements: Sequence[Requirement],
    semantic: SemanticAnalysis,
) -> LexicalAnalysis:
    """Add semantic context to lexical terms without changing lexical findings.

    The lexical visibility and score remain determined only by literal or
    normalized wording. This link tells the UI whether an absent term maps to
    a concept already supported semantically.
    """

    if semantic.status is not AnalysisStatus.EVALUATED:
        return lexical
    evaluations = {item.requirement_id: item.expression for item in semantic.requirements}
    leaves = [
        pair
        for requirement in requirements
        if (evaluation := evaluations.get(requirement.id)) is not None
        for pair in _leaf_evaluations(requirement.expression, evaluation)
    ]
    linked_terms = []
    for term in lexical.terms:
        term_concept = Concept(
            name=term.term,
            canonical_id=term.canonical_concept_id,
            confidence=1.0,
        )
        statuses = [
            status
            for leaf, status in leaves
            if concepts_semantically_overlap(term_concept, leaf.concept)
        ]
        linked_terms.append(term.model_copy(update={"semantic_support": _combined_status(statuses)}))
    return lexical.model_copy(update={"terms": linked_terms})


__all__ = ["link_lexical_semantic_support"]
