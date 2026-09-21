"""Recursive, status-based aggregation for requirement evidence.

The aggregation layer never invents or joins raw evidence. The matcher may
place several related CV locations in one Evidence bundle; unrelated bundles
remain separate so that weak matches cannot accumulate into accidental proof.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.scanner.requirements import AllExpression, AnyExpression, ExpressionNode, Requirement, RequirementLeaf
from app.scanner.results import (
    Evidence,
    EvidenceStatus,
    ExpressionEvaluation,
    RequirementEvaluation,
)


_SUPPORTED_DIMENSION_STATUSES = {EvidenceStatus.SUPPORTED}
_MEANINGFUL_DIMENSION_STATUSES = {
    EvidenceStatus.SUPPORTED,
    EvidenceStatus.PARTIAL,
    EvidenceStatus.CONFLICTING,
}


def _evidence_status(leaf: RequirementLeaf, evidence: Sequence[Evidence]) -> EvidenceStatus:
    if not evidence:
        return EvidenceStatus.NOT_EVIDENCED

    statuses: list[EvidenceStatus] = []
    for item in evidence:
        dimensions = [item.concept_status, item.expectation_status]
        if leaf.constraints:
            constraint_statuses = {support.constraint_id: support.status for support in item.constraints}
            dimensions.extend(
                constraint_statuses.get(constraint.id, EvidenceStatus.UNVERIFIABLE)
                for constraint in leaf.constraints
            )

        if EvidenceStatus.CONFLICTING in dimensions:
            statuses.append(EvidenceStatus.CONFLICTING)
        elif all(status in _SUPPORTED_DIMENSION_STATUSES for status in dimensions):
            statuses.append(EvidenceStatus.SUPPORTED)
        elif any(status in _MEANINGFUL_DIMENSION_STATUSES for status in dimensions):
            statuses.append(EvidenceStatus.PARTIAL)
        elif EvidenceStatus.UNVERIFIABLE in dimensions:
            statuses.append(EvidenceStatus.UNVERIFIABLE)
        else:
            statuses.append(EvidenceStatus.NOT_EVIDENCED)

    if EvidenceStatus.CONFLICTING in statuses:
        return EvidenceStatus.CONFLICTING
    if EvidenceStatus.SUPPORTED in statuses:
        return EvidenceStatus.SUPPORTED
    if EvidenceStatus.PARTIAL in statuses:
        return EvidenceStatus.PARTIAL
    if EvidenceStatus.UNVERIFIABLE in statuses:
        return EvidenceStatus.UNVERIFIABLE
    return EvidenceStatus.NOT_EVIDENCED


def _unique_evidence_ids(evaluations: Sequence[ExpressionEvaluation]) -> list[str]:
    seen: set[str] = set()
    evidence_ids: list[str] = []
    for evaluation in evaluations:
        for evidence_id in evaluation.evidence_ids:
            if evidence_id not in seen:
                seen.add(evidence_id)
                evidence_ids.append(evidence_id)
    return evidence_ids


def _all_status(children: Sequence[ExpressionEvaluation]) -> EvidenceStatus:
    statuses = [child.status for child in children if not child.optional]
    if not statuses:
        return EvidenceStatus.SUPPORTED
    if all(status is EvidenceStatus.SUPPORTED for status in statuses):
        return EvidenceStatus.SUPPORTED
    if EvidenceStatus.CONFLICTING in statuses:
        return EvidenceStatus.CONFLICTING
    if any(status in {EvidenceStatus.SUPPORTED, EvidenceStatus.PARTIAL} for status in statuses):
        return EvidenceStatus.PARTIAL
    if EvidenceStatus.UNVERIFIABLE in statuses:
        return EvidenceStatus.UNVERIFIABLE
    return EvidenceStatus.NOT_EVIDENCED


def _any_status(children: Sequence[ExpressionEvaluation]) -> EvidenceStatus:
    statuses = [child.status for child in children if not child.optional]
    if not statuses:
        return EvidenceStatus.SUPPORTED
    if any(status is EvidenceStatus.SUPPORTED for status in statuses):
        return EvidenceStatus.SUPPORTED
    if statuses and all(status is EvidenceStatus.CONFLICTING for status in statuses):
        return EvidenceStatus.CONFLICTING
    if statuses and all(status is EvidenceStatus.NOT_EVIDENCED for status in statuses):
        return EvidenceStatus.NOT_EVIDENCED
    if statuses and all(
        status in {EvidenceStatus.NOT_EVIDENCED, EvidenceStatus.UNVERIFIABLE} for status in statuses
    ):
        return EvidenceStatus.UNVERIFIABLE
    return EvidenceStatus.PARTIAL


def evaluate_expression(
    expression: ExpressionNode,
    evidence_by_node: Mapping[str, Sequence[Evidence]],
) -> ExpressionEvaluation:
    """Evaluate leaves and recursively apply ALL/ANY semantics.

    Evidence from separate bundles is never merged here. A matcher may bundle
    multiple CV locations when they jointly establish one coherent fact.
    """

    if isinstance(expression, RequirementLeaf):
        evidence = tuple(evidence_by_node.get(expression.id, ()))
        status = _evidence_status(expression, evidence)
        relevant_ids = [item.id for item in evidence if item.id]
        optional = expression.modifiers.optional
        return ExpressionEvaluation(
            node_id=expression.id,
            status=status,
            optional=optional,
            mandatory_total=0 if optional else 1,
            mandatory_supported=int(not optional and status is EvidenceStatus.SUPPORTED),
            evidence_ids=relevant_ids,
        )

    child_evaluations = [evaluate_expression(child, evidence_by_node) for child in expression.children]
    if isinstance(expression, AllExpression):
        status = _all_status(child_evaluations)
        mandatory_total = sum(child.mandatory_total for child in child_evaluations if not child.optional)
        mandatory_supported = sum(
            child.mandatory_supported for child in child_evaluations if not child.optional
        )
    elif isinstance(expression, AnyExpression):
        status = _any_status(child_evaluations)
        optional = expression.modifiers.optional
        mandatory_total = 0 if optional else 1
        mandatory_supported = int(not optional and status is EvidenceStatus.SUPPORTED)
    else:  # pragma: no cover - guarded by the discriminated expression union
        raise TypeError(f"Unsupported expression node: {type(expression).__name__}")

    return ExpressionEvaluation(
        node_id=expression.id,
        status=status,
        optional=expression.modifiers.optional,
        mandatory_total=mandatory_total,
        mandatory_supported=mandatory_supported,
        evidence_ids=_unique_evidence_ids(child_evaluations),
        children=child_evaluations,
    )


def evaluate_requirement(
    requirement: Requirement,
    evidence_by_node: Mapping[str, Sequence[Evidence]],
) -> RequirementEvaluation:
    """Return one parent result without multiplying its source requirement weight."""

    expression = evaluate_expression(requirement.expression, evidence_by_node)
    return RequirementEvaluation(
        requirement_id=requirement.id,
        status=expression.status,
        expression=expression,
    )


__all__ = ["evaluate_expression", "evaluate_requirement"]
