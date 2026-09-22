from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.matching import evaluate_semantic_coverage
from app.scanner.requirements import AnyExpression, ExperienceDurationConstraint, ExamplesExpression, RequirementLeaf
from app.scanner.results import EvidenceStatus, EvidenceStrength
from app.scanner.scoring import score_semantic_analysis


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "scanner" / "convverge"


def _load_fixture() -> tuple[str, dict[str, Any]]:
    job = json.loads((FIXTURE_DIR / "job.json").read_text(encoding="utf-8"))["description"]
    candidate = json.loads((FIXTURE_DIR / "candidate.json").read_text(encoding="utf-8"))
    return job, candidate


def _leaves(node: object) -> list[RequirementLeaf]:
    if isinstance(node, RequirementLeaf):
        return [node]
    if isinstance(node, ExamplesExpression):
        return [*_leaves(node.subject), *[leaf for item in node.examples for leaf in _leaves(item)]]
    children = getattr(node, "children", [])
    return [leaf for child in children for leaf in _leaves(child)]


def test_convverge_fixture_excludes_employer_copy_and_preserves_source_requirements() -> None:
    job, _candidate = _load_fixture()
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    source_texts = {item.source.original_text for item in extraction.requirements}

    assert not any("You'll work alongside developers" in text for text in source_texts)
    assert not any(text.startswith("In return, you’ll find") for text in source_texts)
    assert any(text.startswith("Post-secondary education") for text in source_texts)
    assert any(text.startswith("Approximately 0–2 years") for text in source_texts)
    assert len([text for text in source_texts if "documentation" in text.casefold()]) == 2


def test_convverge_fixture_evaluates_nested_logic_constraints_and_evidence_strength() -> None:
    job, candidate = _load_fixture()
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    analysis = evaluate_semantic_coverage(extraction.requirements, candidate, as_of=date(2026, 9, 22))
    evaluations = {item.requirement_id: item for item in analysis.requirements}
    education = next(item for item in extraction.requirements if item.source.original_text.startswith("Post-secondary education"))
    assert isinstance(education.expression, AnyExpression)
    assert isinstance(education.expression.children[0], AnyExpression)
    assert evaluations[education.id].status is EvidenceStatus.SUPPORTED

    years = next(item for item in extraction.requirements if item.source.original_text.startswith("Approximately 0–2 years"))
    year_leaves = _leaves(years.expression)
    assert len(year_leaves) == 1
    assert len(year_leaves[0].constraints) == 1
    assert isinstance(year_leaves[0].constraints[0], ExperienceDurationConstraint)
    assert evaluations[years.id].status is EvidenceStatus.SUPPORTED
    duration_observations = [
        constraint.observation
        for evidence in analysis.evidence
        for constraint in evidence.constraints
        if constraint.constraint_id == year_leaves[0].constraints[0].id
    ]
    assert "above_approximate_range" in duration_observations

    interest = next(item for item in extraction.requirements if item.source.original_text.startswith("Interest in Microsoft cloud"))
    assert isinstance(interest.expression, ExamplesExpression)
    assert evaluations[interest.id].status is EvidenceStatus.SUPPORTED
    assert any(
        evidence.strength is EvidenceStrength.DIRECT_DEMONSTRATION
        for evidence in analysis.evidence
        if evidence.id in evaluations[interest.id].expression.evidence_ids
    )

    documentation = [item for item in extraction.requirements if "documentation" in item.source.original_text.casefold()]
    assert len(documentation) == 2
    assert all(evaluations[item.id].status is EvidenceStatus.PARTIAL for item in documentation)
    assert all(
        evidence.strength is EvidenceStrength.PARTIAL_TRANSFER
        for item in documentation
        for evidence in analysis.evidence
        if evidence.id in evaluations[item.id].expression.evidence_ids
    )

    preferred_microsoft = next(item for item in extraction.requirements if item.source.original_text.startswith("Experience with Microsoft Azure"))
    assert isinstance(preferred_microsoft.expression, AnyExpression)
    assert evaluations[preferred_microsoft.id].status is EvidenceStatus.PARTIAL

    # The canonical exported CV currently contains no literal collaboration or
    # Agile assertion. Those remain genuine gaps; the fixture must not be
    # rewritten to force the comparison narrative.
    collaboration = next(item for item in extraction.requirements if item.source.original_text.startswith("Ability to work both"))
    agile = next(item for item in extraction.requirements if item.source.original_text.startswith("Exposure to Agile"))
    assert evaluations[collaboration.id].status is EvidenceStatus.PARTIAL
    assert evaluations[agile.id].status is EvidenceStatus.NOT_EVIDENCED


def test_convverge_fixture_produces_a_scored_job_fit_summary() -> None:
    job, candidate = _load_fixture()
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    analysis = evaluate_semantic_coverage(extraction.requirements, candidate, as_of=date(2026, 9, 22))
    summary = score_semantic_analysis(analysis, extraction.requirements)

    assert summary.status.value == "available"
    assert summary.job_fit is not None
    assert summary.classified_fraction == 1.0
    assert summary.qualification_fit.total_weight > 0
    assert summary.responsibility_alignment.total_weight > 0
    assert summary.preferred_fit.total_weight > 0
