from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.scanner.requirements import (
    AllExpression,
    AnyExpression,
    Concept,
    Expectation,
    ExpectationKind,
    ExamplesExpression,
    MinimumYearsConstraint,
    Requirement,
    RequirementImportance,
    RequirementLeaf,
)
from app.scanner.aggregation import evaluate_expression
from app.scanner.results import (
    AnalysisStatus,
    CVLocation,
    ConstraintEvidence,
    Evidence,
    EvidenceMethod,
    EvidenceStatus,
    ExpressionEvaluation,
    JobTextLocation,
    LexicalAnalysis,
    LexicalEvidence,
    LexicalTerm,
    LexicalVisibility,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
    PresentationQualityAnalysis,
    RequirementEvaluation,
    ScanInputFingerprints,
    ScanResult,
    ScannerVersions,
    SemanticAnalysis,
)


def _leaf(node_id: str, concept_name: str) -> RequirementLeaf:
    return RequirementLeaf(
        kind="leaf",
        id=node_id,
        concept=Concept(name=concept_name, confidence=0.9),
        expectation=Expectation(kind=ExpectationKind.PRIOR_EXPERIENCE, confidence=0.8),
        confidence=0.85,
    )


def _evidence(
    evidence_id: str,
    *,
    concept: EvidenceStatus = EvidenceStatus.SUPPORTED,
    expectation: EvidenceStatus = EvidenceStatus.SUPPORTED,
    constraints: list[ConstraintEvidence] | None = None,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        locations=[CVLocation(field_path="experience[0].description", excerpt="Relevant CV evidence")],
        concept_status=concept,
        expectation_status=expectation,
        constraints=constraints or [],
        confidence=0.9,
        method=EvidenceMethod.STRUCTURED,
    )


def test_requirement_expression_preserves_nested_all_any_structure() -> None:
    requirement = Requirement.model_validate(
        {
            "id": "req-1",
            "source": {
                "original_text": "Experience with Python or Java, and React",
                "source_start": 12,
                "source_end": 53,
                "extraction_confidence": 0.92,
                "extractor_version": "fixture-v1",
            },
            "importance": "required",
            "weight": 2.0,
            "expression": {
                "kind": "all",
                "id": "all-1",
                "confidence": 0.9,
                "children": [
                    {
                        "kind": "any",
                        "id": "any-1",
                        "confidence": 0.88,
                        "children": [
                            _leaf("python", "Python").model_dump(mode="json"),
                            _leaf("java", "Java").model_dump(mode="json"),
                        ],
                    },
                    _leaf("react", "React").model_dump(mode="json"),
                ],
            },
        }
    )

    assert isinstance(requirement.expression, AllExpression)
    alternatives = requirement.expression.children[0]
    assert isinstance(alternatives, AnyExpression)
    assert [child.concept.name for child in alternatives.children] == ["Python", "Java"]
    assert requirement.weight == 2.0


def test_concept_expectation_and_constraint_are_distinct_dimensions() -> None:
    leaf = RequirementLeaf(
        kind="leaf",
        id="python-experience",
        concept=Concept(name="Python", confidence=0.95),
        expectation=Expectation(
            kind=ExpectationKind.PRIOR_EXPERIENCE,
            qualifier="in production software",
            confidence=0.88,
        ),
        constraints=[
            MinimumYearsConstraint(
                id="python-years",
                kind="minimum_years",
                years=3,
                source_text="at least three years",
                confidence=0.99,
            )
        ],
        confidence=0.91,
    )

    assert leaf.concept.name == "Python"
    assert leaf.expectation.kind is ExpectationKind.PRIOR_EXPERIENCE
    assert isinstance(leaf.constraints[0], MinimumYearsConstraint)
    assert leaf.constraints[0].years == 3


def test_numeric_range_constraint_rejects_incomplete_bounds() -> None:
    with pytest.raises(ValidationError, match="range thresholds require ordered minimum and maximum"):
        RequirementLeaf.model_validate(
            {
                "kind": "leaf",
                "id": "threshold",
                "concept": {"name": "score", "confidence": 0.8},
                "expectation": {"kind": "proficiency", "confidence": 0.8},
                "constraints": [
                    {
                        "kind": "numeric_threshold",
                        "id": "score-range",
                        "operator": "range",
                        "minimum": 2,
                        "source_text": "between 2 and 4",
                        "confidence": 0.9,
                    }
                ],
                "confidence": 0.9,
            }
        )


def test_evidence_keeps_concept_overlap_separate_from_expectation_support() -> None:
    evidence = Evidence(
        id="cv-title-1",
        locations=[
            CVLocation(
                section_id="experience-1",
                section_type="experience",
                entry_id="job-1",
                field_path="position",
                excerpt="Associate Software Engineer",
            )
        ],
        concept_status=EvidenceStatus.SUPPORTED,
        expectation_status=EvidenceStatus.NOT_EVIDENCED,
        confidence=0.94,
        method=EvidenceMethod.TAXONOMY,
    )
    result = RequirementEvaluation(
        requirement_id="industry-curiosity",
        status=EvidenceStatus.PARTIAL,
        expression=ExpressionEvaluation(
            node_id="interest-leaf",
            status=EvidenceStatus.PARTIAL,
            evidence_ids=[evidence.id],
        ),
    )

    assert evidence.concept_status is EvidenceStatus.SUPPORTED
    assert evidence.expectation_status is EvidenceStatus.NOT_EVIDENCED
    assert result.status is EvidenceStatus.PARTIAL


def test_concept_alias_alone_cannot_support_the_requirement() -> None:
    expression = _leaf("curiosity", "software development")

    result = evaluate_expression(
        expression,
        {
            "curiosity": [
                _evidence(
                    "title-overlap",
                    concept=EvidenceStatus.SUPPORTED,
                    expectation=EvidenceStatus.NOT_EVIDENCED,
                )
            ]
        },
    )

    assert result.status is EvidenceStatus.PARTIAL
    assert result.mandatory_supported == 0
    assert result.mandatory_total == 1


def test_all_expression_reports_supported_mandatory_component_count() -> None:
    expression = AllExpression(
        kind="all",
        id="modern-practices",
        confidence=0.9,
        children=[_leaf("ai", "AI-assisted development"), _leaf("cicd", "CI/CD"), _leaf("containers", "containerization"), _leaf("monitoring", "monitoring")],
    )
    evidence = {
        "ai": [_evidence("ai-evidence")],
        "cicd": [_evidence("cicd-evidence")],
        "containers": [_evidence("container-evidence")],
    }

    result = evaluate_expression(expression, evidence)

    assert result.status is EvidenceStatus.PARTIAL
    assert (result.mandatory_supported, result.mandatory_total) == (3, 4)
    assert result.children[-1].status is EvidenceStatus.NOT_EVIDENCED


def test_optional_child_is_reported_but_does_not_block_all_expression() -> None:
    expression = AllExpression(
        kind="all",
        id="all-tools",
        confidence=0.9,
        children=[
            _leaf("python", "Python"),
            RequirementLeaf.model_validate(
                {
                    **_leaf("ruby", "Ruby").model_dump(mode="python"),
                    "modifiers": {"optional": True},
                }
            ),
        ],
    )

    result = evaluate_expression(expression, {"python": [_evidence("python-evidence")]})

    assert result.status is EvidenceStatus.SUPPORTED
    assert (result.mandatory_supported, result.mandatory_total) == (1, 1)
    assert result.children[1].optional is True
    assert result.children[1].status is EvidenceStatus.NOT_EVIDENCED


def test_any_expression_accepts_one_complete_alternative() -> None:
    expression = AnyExpression(
        kind="any",
        id="python-or-java",
        confidence=0.9,
        children=[_leaf("python", "Python"), _leaf("java", "Java")],
    )

    result = evaluate_expression(expression, {"python": [_evidence("python-evidence")]})

    assert result.status is EvidenceStatus.SUPPORTED
    assert (result.mandatory_supported, result.mandatory_total) == (1, 1)
    assert result.children[1].status is EvidenceStatus.NOT_EVIDENCED


def test_examples_expression_needs_breadth_but_counts_as_one_requirement() -> None:
    expression = ExamplesExpression(
        kind="examples",
        id="team-rituals",
        subject=_leaf("rituals", "team rituals"),
        examples=[
            RequirementLeaf.model_validate(
                {**_leaf(node_id, name).model_dump(mode="python"), "modifiers": {"optional": True, "list_semantics": "examples"}}
            )
            for node_id, name in (("standups", "standups"), ("demos", "demos"), ("retros", "retrospectives"))
        ],
        min_supporting_examples=2,
        confidence=0.9,
    )

    one_example = evaluate_expression(
        expression,
        {"standups": [_evidence("standup-evidence")]},
    )
    two_examples = evaluate_expression(
        expression,
        {
            "standups": [_evidence("standup-evidence")],
            "demos": [_evidence("demo-evidence")],
        },
    )

    assert one_example.status is EvidenceStatus.PARTIAL
    assert (one_example.mandatory_supported, one_example.mandatory_total) == (0, 1)
    assert two_examples.status is EvidenceStatus.SUPPORTED
    assert (two_examples.mandatory_supported, two_examples.mandatory_total) == (1, 1)
    assert all(item.mandatory_total == 0 for item in two_examples.children[1:])


def test_examples_expression_caps_threshold_to_available_items() -> None:
    expression = ExamplesExpression(
        kind="examples",
        id="one-language-example",
        subject=_leaf("languages", "programming languages"),
        examples=[
            RequirementLeaf.model_validate(
                {**_leaf("python", "Python").model_dump(mode="python"), "modifiers": {"optional": True}}
            )
        ],
        min_supporting_examples=2,
        confidence=0.9,
    )

    result = evaluate_expression(
        expression,
        {"python": [_evidence("python-evidence")]},
    )

    assert expression.min_supporting_examples == 1
    assert result.status is EvidenceStatus.SUPPORTED


def test_optional_any_alternative_cannot_satisfy_a_mandatory_alternative() -> None:
    expression = AnyExpression(
        kind="any",
        id="python-or-optional-java",
        confidence=0.9,
        children=[
            _leaf("python", "Python"),
            RequirementLeaf.model_validate(
                {
                    **_leaf("java", "Java").model_dump(mode="python"),
                    "modifiers": {"optional": True},
                }
            ),
        ],
    )

    result = evaluate_expression(expression, {"java": [_evidence("java-evidence")]})

    assert result.status is EvidenceStatus.NOT_EVIDENCED
    assert result.children[1].status is EvidenceStatus.SUPPORTED
    assert result.children[1].optional is True


def test_evidence_from_separate_bundles_is_not_combined_automatically() -> None:
    expression = _leaf("python", "Python")
    evidence = {
        "python": [
            _evidence("concept-only", expectation=EvidenceStatus.NOT_EVIDENCED),
            _evidence("expectation-only", concept=EvidenceStatus.NOT_EVIDENCED),
        ]
    }

    result = evaluate_expression(expression, evidence)

    assert result.status is EvidenceStatus.PARTIAL
    assert result.status is not EvidenceStatus.SUPPORTED


def test_unknown_required_constraint_prevents_full_support() -> None:
    expression = RequirementLeaf.model_validate(
        {
            **_leaf("python-years", "Python").model_dump(mode="python"),
            "constraints": [
                {
                    "kind": "minimum_years",
                    "id": "python-years",
                    "years": 3,
                    "source_text": "three years of Python",
                    "confidence": 0.95,
                }
            ],
        }
    )

    result = evaluate_expression(
        expression,
        {
            "python-years": [
                _evidence(
                    "years-unknown",
                    constraints=[
                        ConstraintEvidence(
                            constraint_id="python-years",
                            status=EvidenceStatus.UNVERIFIABLE,
                        )
                    ],
                )
            ]
        },
    )

    assert result.status is EvidenceStatus.PARTIAL
    assert result.mandatory_supported == 0


def test_scan_result_keeps_subsystem_results_and_versions_independent() -> None:
    result = ScanResult(
        created_at=datetime(2026, 9, 20, tzinfo=UTC),
        input_fingerprints=ScanInputFingerprints(
            job_description_sha256="a" * 64,
            cv_content_sha256="b" * 64,
            pdf_sha256="c" * 64,
        ),
        versions=ScannerVersions(
            extractor_version="extractor-v1",
            matcher_version="matcher-v1",
            lexical_version="lexical-v1",
            quality_version="quality-v1",
            pdf_analysis_version="pdf-v1",
        ),
        requirement_extraction={
            "status": "evaluated",
            "source_hash": "a" * 64,
            "extractor_version": "extractor-v1",
            "requirements": [],
        },
        semantic=SemanticAnalysis(status=AnalysisStatus.EVALUATED),
        lexical=LexicalAnalysis(
            status=AnalysisStatus.EVALUATED,
            terms=[
                LexicalTerm(
                    id="term-cicd",
                    term="CI/CD",
                    importance=RequirementImportance.REQUIRED,
                    source_locations=[JobTextLocation(source_start=20, source_end=25)],
                    visibility=LexicalVisibility.ABSENT,
                )
            ],
        ),
        presentation_quality=PresentationQualityAnalysis(status=AnalysisStatus.NOT_EVALUATED),
        pdf_recovery=PDFTextRecoveryAnalysis(status=PDFRecoveryStatus.UNAVAILABLE),
    )

    payload = result.model_dump(mode="json")
    assert payload["schema_version"] == "scanner-v1"
    assert payload["semantic"]["status"] == "evaluated"
    assert payload["semantic"].get("summary") is None
    assert payload["lexical"]["terms"][0]["visibility"] == "absent"
    assert payload["lexical"].get("summary") is None
    assert payload["presentation_quality"]["status"] == "not_evaluated"
    assert payload["pdf_recovery"]["status"] == "unavailable"
    assert payload["pdf_recovery"].get("summary") is None
    assert result.versions.semantic_score_version is None


def test_lexical_variant_requires_evidence_and_cv_location() -> None:
    term = LexicalTerm(
        id="automated-testing",
        term="automated testing",
        variants=["unit tests", "integration tests"],
        source_locations=[JobTextLocation(source_start=0, source_end=18)],
        visibility=LexicalVisibility.VARIANT,
        evidence=[
            LexicalEvidence(
                location=CVLocation(field_path="experience[0].description", excerpt="Added unit tests"),
                matched_text="unit tests",
                visibility="variant",
            )
        ],
    )

    assert term.visibility is LexicalVisibility.VARIANT
    assert term.evidence[0].location.field_path == "experience[0].description"
