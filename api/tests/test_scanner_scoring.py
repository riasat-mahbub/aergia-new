from __future__ import annotations

from app.scanner.analysis_links import link_lexical_semantic_support
from app.scanner.requirements import (
    AllExpression,
    AnyExpression,
    Concept,
    Expectation,
    ExpectationKind,
    ExamplesExpression,
    ExpressionModifiers,
    MinimumYearsConstraint,
    Requirement,
    RequirementFamily,
    RequirementImportance,
    RequirementLeaf,
    RequirementSource,
    SectionContext,
    SectionPurpose,
)
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
    LexicalTerm,
    LexicalVisibility,
    PDFCheck,
    PDFRecoveryStatus,
    PDFTextRecoveryAnalysis,
    RequirementEvaluation,
    SemanticAnalysis,
    ScoreStatus,
)
from app.scanner.scoring import (
    score_lexical_analysis,
    score_pdf_recovery,
    score_semantic_analysis,
)


def _leaf(
    node_id: str,
    name: str,
    *,
    optional: bool = False,
    constraints: list[object] | None = None,
) -> RequirementLeaf:
    return RequirementLeaf(
        kind="leaf",
        id=node_id,
        concept=Concept(name=name, confidence=0.95),
        expectation=Expectation(kind=ExpectationKind.FAMILIARITY, confidence=0.9),
        constraints=constraints or [],
        modifiers=ExpressionModifiers(optional=optional),
        confidence=0.9,
    )


def _requirement(
    requirement_id: str,
    expression: object,
    *,
    importance: RequirementImportance = RequirementImportance.REQUIRED,
    purpose: SectionPurpose = SectionPurpose.CANDIDATE_QUALIFICATIONS,
    family: RequirementFamily = RequirementFamily.TECHNICAL_SKILL,
    weight: float = 1.0,
) -> Requirement:
    source_text = f"Requirement {requirement_id}"
    return Requirement(
        id=requirement_id,
        source=RequirementSource(
            original_text=source_text,
            source_start=0,
            source_end=len(source_text),
            section=SectionContext(title="Requirements", purpose=purpose, confidence=0.95),
            extraction_confidence=0.95,
            extractor_version="test",
        ),
        importance=importance,
        family=family,
        weight=weight,
        expression=expression,
    )


def _leaf_result(leaf: RequirementLeaf, status: EvidenceStatus) -> ExpressionEvaluation:
    optional = leaf.modifiers.optional
    return ExpressionEvaluation(
        node_id=leaf.id,
        status=status,
        optional=optional,
        mandatory_total=0 if optional else 1,
        mandatory_supported=int(not optional and status is EvidenceStatus.SUPPORTED),
    )


def _semantic(
    requirements: list[Requirement],
    evaluations: list[ExpressionEvaluation],
    *,
    evidence: list[Evidence] | None = None,
) -> SemanticAnalysis:
    return SemanticAnalysis(
        status=AnalysisStatus.EVALUATED,
        requirements=[
            RequirementEvaluation(
                requirement_id=requirement.id,
                status=evaluation.status,
                expression=evaluation,
            )
            for requirement, evaluation in zip(requirements, evaluations, strict=True)
        ],
        evidence=evidence or [],
    )


def _all_evaluation(
    expression: AllExpression,
    statuses: list[EvidenceStatus],
    *,
    status: EvidenceStatus | None = None,
) -> ExpressionEvaluation:
    children = [_leaf_result(leaf, child_status) for leaf, child_status in zip(expression.children, statuses, strict=True)]
    selected_status = status or (
        EvidenceStatus.SUPPORTED
        if all(item is EvidenceStatus.SUPPORTED for item in statuses if item is not EvidenceStatus.UNVERIFIABLE)
        else EvidenceStatus.PARTIAL
    )
    return ExpressionEvaluation(
        node_id=expression.id,
        status=selected_status,
        mandatory_total=sum(not child.optional for child in children),
        mandatory_supported=sum(child.mandatory_supported for child in children),
        children=children,
    )


def test_all_score_averages_leaf_coverage_and_maps_partial_to_half() -> None:
    expression = AllExpression(
        kind="all",
        id="all-skills",
        confidence=0.9,
        children=[_leaf(f"skill-{index}", f"Skill {index}") for index in range(4)],
    )
    requirement = _requirement("skills", expression, weight=2.0)
    evaluation = _all_evaluation(
        expression,
        [
            EvidenceStatus.SUPPORTED,
            EvidenceStatus.SUPPORTED,
            EvidenceStatus.PARTIAL,
            EvidenceStatus.NOT_EVIDENCED,
        ],
        status=EvidenceStatus.PARTIAL,
    )

    summary = score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement])

    assert summary.job_fit == 0.625
    assert summary.qualification_fit.score == 0.625
    assert summary.qualification_fit.total_weight == 2.0


def test_low_classification_coverage_adds_caution_without_changing_job_fit() -> None:
    classified = _requirement("known", _leaf("python", "Python"))
    unclassified = _requirement(
        "unknown",
        _leaf("misc", "miscellaneous"),
        importance=RequirementImportance.UNKNOWN,
        purpose=SectionPurpose.UNKNOWN,
        family=RequirementFamily.OTHER,
    )
    evaluations = [
        _leaf_result(classified.expression, EvidenceStatus.SUPPORTED),
        _leaf_result(unclassified.expression, EvidenceStatus.NOT_EVIDENCED),
    ]

    summary = score_semantic_analysis(
        _semantic([classified, unclassified], evaluations),
        [classified, unclassified],
    )

    assert summary.status is ScoreStatus.AVAILABLE
    assert summary.job_fit == 1.0
    assert summary.classified_fraction == 0.5
    assert summary.evidence_scorable_fraction == 1.0
    assert summary.classification_warning_code == "low_requirement_classification_coverage"


def test_stronger_leaf_evidence_never_lowers_job_fit() -> None:
    leaf = _leaf("python", "Python")
    requirement = _requirement("python", leaf)

    def score(status: EvidenceStatus) -> float:
        evaluation = _leaf_result(leaf, status)
        return score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement]).job_fit or 0.0

    assert score(EvidenceStatus.SUPPORTED) > score(EvidenceStatus.PARTIAL)
    assert score(EvidenceStatus.PARTIAL) > score(EvidenceStatus.NOT_EVIDENCED)


def test_any_uses_best_complete_alternative_without_penalizing_other_options() -> None:
    expression = AnyExpression(
        kind="any",
        id="language-choice",
        confidence=0.9,
        children=[_leaf("python", "Python"), _leaf("java", "Java"), _leaf("csharp", "C#")],
    )
    requirement = _requirement("language", expression)
    evaluation = ExpressionEvaluation(
        node_id=expression.id,
        status=EvidenceStatus.SUPPORTED,
        mandatory_total=1,
        mandatory_supported=1,
        children=[
            _leaf_result(expression.children[0], EvidenceStatus.SUPPORTED),
            _leaf_result(expression.children[1], EvidenceStatus.NOT_EVIDENCED),
            _leaf_result(expression.children[2], EvidenceStatus.NOT_EVIDENCED),
        ],
    )

    summary = score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement])

    assert summary.job_fit == 1.0
    assert summary.scorable_fraction == 1.0


def test_optional_components_are_excluded_from_mandatory_score() -> None:
    required = _leaf("python", "Python")
    optional = _leaf("ruby", "Ruby", optional=True)
    expression = AllExpression(kind="all", id="languages", children=[required, optional], confidence=0.9)
    requirement = _requirement("languages", expression)
    evaluation = _all_evaluation(
        expression,
        [EvidenceStatus.SUPPORTED, EvidenceStatus.NOT_EVIDENCED],
        status=EvidenceStatus.SUPPORTED,
    )

    summary = score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement])

    assert summary.job_fit == 1.0
    assert summary.qualification_fit.scorable_fraction == 1.0
    assert summary.qualification_fit.total_weight == 1.0


def test_unverifiable_leaf_is_excluded_and_reduces_scorable_coverage() -> None:
    expression = AllExpression(
        kind="all",
        id="two-skills",
        children=[_leaf("python", "Python"), _leaf("clearance", "Security clearance")],
        confidence=0.9,
    )
    requirement = _requirement("two-skills", expression)
    evaluation = _all_evaluation(
        expression,
        [EvidenceStatus.SUPPORTED, EvidenceStatus.UNVERIFIABLE],
        status=EvidenceStatus.PARTIAL,
    )

    summary = score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement])

    assert summary.job_fit is None
    assert summary.status is ScoreStatus.INSUFFICIENT_SCORABLE_EVIDENCE
    assert summary.scorable_fraction == 0.5
    assert summary.evidence_scorable_fraction == 0.5
    assert summary.unverifiable_requirement_count == 0
    assert summary.unverifiable_component_count == 1
    assert summary.qualification_fit.score == 1.0


def test_examples_score_as_one_obligation_not_one_per_example() -> None:
    subject = _leaf("team-rituals", "team rituals")
    examples = [_leaf("standups", "standups", optional=True), _leaf("demos", "demos", optional=True)]
    expression = ExamplesExpression(
        kind="examples",
        id="rituals",
        subject=subject,
        examples=examples,
        min_supporting_examples=2,
        confidence=0.8,
    )
    requirement = _requirement("rituals", expression)
    evaluation = ExpressionEvaluation(
        node_id=expression.id,
        status=EvidenceStatus.PARTIAL,
        mandatory_total=1,
        mandatory_supported=0,
        children=[
            _leaf_result(subject, EvidenceStatus.NOT_EVIDENCED),
            _leaf_result(examples[0], EvidenceStatus.SUPPORTED),
            _leaf_result(examples[1], EvidenceStatus.NOT_EVIDENCED),
        ],
    )

    summary = score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement])

    assert summary.job_fit == 0.5
    assert summary.qualification_fit.total_weight == 1.0


def test_bucket_weights_make_preferred_gaps_less_influential_than_required_gaps() -> None:
    qualification = _requirement("qualification", _leaf("python", "Python"))
    responsibility = _requirement(
        "responsibility",
        _leaf("testing", "automated testing"),
        purpose=SectionPurpose.CANDIDATE_RESPONSIBILITIES,
        family=RequirementFamily.RESPONSIBILITY,
    )
    preferred = _requirement(
        "preferred",
        _leaf("french", "French"),
        importance=RequirementImportance.PREFERRED,
    )

    def summary_for(statuses: list[EvidenceStatus]) -> float:
        requirements = [qualification, responsibility, preferred]
        evaluations = [
            _leaf_result(requirement.expression, status)
            for requirement, status in zip(requirements, statuses, strict=True)
        ]
        analysis = _semantic(requirements, evaluations)
        return score_semantic_analysis(analysis, requirements).job_fit or 0.0

    all_supported = summary_for([EvidenceStatus.SUPPORTED] * 3)
    preferred_gap = summary_for([EvidenceStatus.SUPPORTED, EvidenceStatus.SUPPORTED, EvidenceStatus.NOT_EVIDENCED])
    qualification_gap = summary_for([EvidenceStatus.NOT_EVIDENCED, EvidenceStatus.SUPPORTED, EvidenceStatus.SUPPORTED])

    assert all_supported == 1.0
    assert preferred_gap == 0.95
    assert qualification_gap == 0.30
    assert 1.0 - preferred_gap < 1.0 - qualification_gap


def test_absent_bucket_weights_redistribute_across_present_buckets() -> None:
    qualification = _requirement("qualification", _leaf("python", "Python"))
    responsibility = _requirement(
        "responsibility",
        _leaf("testing", "automated testing"),
        purpose=SectionPurpose.CANDIDATE_RESPONSIBILITIES,
        family=RequirementFamily.RESPONSIBILITY,
    )
    evaluation = [
        _leaf_result(qualification.expression, EvidenceStatus.NOT_EVIDENCED),
        _leaf_result(responsibility.expression, EvidenceStatus.SUPPORTED),
    ]

    summary = score_semantic_analysis(_semantic([qualification, responsibility], evaluation), [qualification, responsibility])

    assert summary.job_fit == 0.25 / 0.95


def test_unknown_importance_is_visible_but_excluded_from_headline_score() -> None:
    requirement = _requirement(
        "unknown",
        _leaf("python", "Python"),
        importance=RequirementImportance.UNKNOWN,
    )
    evaluation = _leaf_result(requirement.expression, EvidenceStatus.SUPPORTED)

    summary = score_semantic_analysis(_semantic([requirement], [evaluation]), [requirement])

    assert summary.status is ScoreStatus.INSUFFICIENT_SCORABLE_EVIDENCE
    assert summary.job_fit is None
    assert summary.unclassified_requirement_count == 1
    assert summary.supported_count == 1
    assert summary.classified_fraction == 0.0
    assert summary.evidence_scorable_fraction == 0.0


def test_classification_and_cv_evidence_coverage_are_reported_separately() -> None:
    classified = _requirement("classified", _leaf("python", "Python"), weight=2.0)
    unknown = _requirement(
        "unknown",
        _leaf("docker", "Docker"),
        importance=RequirementImportance.UNKNOWN,
        weight=1.0,
    )
    analysis = _semantic(
        [classified, unknown],
        [
            _leaf_result(classified.expression, EvidenceStatus.SUPPORTED),
            _leaf_result(unknown.expression, EvidenceStatus.UNVERIFIABLE),
        ],
    )

    summary = score_semantic_analysis(analysis, [classified, unknown])

    assert summary.classified_fraction == 2 / 3
    assert summary.evidence_scorable_fraction == 1.0
    assert summary.scorable_fraction == summary.evidence_scorable_fraction
    assert summary.job_fit == 1.0
    assert summary.unverifiable_requirement_count == 1


def test_repeated_source_requirements_share_concept_weight_without_being_merged() -> None:
    as_built = _requirement("as-built", _leaf("as-built-docs", "documentation"), purpose=SectionPurpose.CANDIDATE_RESPONSIBILITIES)
    support = _requirement("support-docs", _leaf("support-docs", "documentation"), purpose=SectionPurpose.CANDIDATE_RESPONSIBILITIES)
    as_built = as_built.model_copy(update={"concept_group_id": "documentation"})
    support = support.model_copy(update={"concept_group_id": "documentation"})
    analysis = _semantic(
        [as_built, support],
        [
            _leaf_result(as_built.expression, EvidenceStatus.SUPPORTED),
            _leaf_result(support.expression, EvidenceStatus.PARTIAL),
        ],
    )

    summary = score_semantic_analysis(analysis, [as_built, support])

    assert summary.responsibility_alignment.requirement_count == 2
    assert summary.responsibility_alignment.total_weight == 1.0
    assert summary.responsibility_alignment.score == 0.75


def test_candidate_expectations_are_scored_as_lower_weight_qualifications() -> None:
    expectation = _requirement("expectation", _leaf("questions", "asking thoughtful questions")).model_copy(
        update={"importance": RequirementImportance.UNKNOWN, "classification": "candidate_expectation", "weight": 0.5}
    )
    analysis = _semantic([expectation], [_leaf_result(expectation.expression, EvidenceStatus.PARTIAL)])

    summary = score_semantic_analysis(analysis, [expectation])

    assert summary.unclassified_requirement_count == 0
    assert summary.qualification_fit.total_weight == 0.5
    assert summary.qualification_fit.score == 0.5


def test_required_constraint_conflicts_are_reported_as_a_flag() -> None:
    constraint = MinimumYearsConstraint(
        id="python-years",
        kind="minimum_years",
        years=5,
        source_text="at least five years",
        confidence=0.9,
    )
    leaf = _leaf("python-experience", "Python", constraints=[constraint])
    requirement = _requirement("python-experience", leaf)
    evidence = Evidence(
        id="ev-python-experience-001",
        locations=[
            CVLocation(
                field_path="experience[0].description",
                excerpt="Built Python services for three years.",
            )
        ],
        concept_status=EvidenceStatus.SUPPORTED,
        expectation_status=EvidenceStatus.SUPPORTED,
        constraints=[
            ConstraintEvidence(
                constraint_id=constraint.id,
                status=EvidenceStatus.CONFLICTING,
                evidence_text="3 years",
            )
        ],
        confidence=0.9,
        method=EvidenceMethod.DERIVED_STRUCTURED_CALCULATION,
    )
    evaluation = _leaf_result(leaf, EvidenceStatus.CONFLICTING)

    summary = score_semantic_analysis(_semantic([requirement], [evaluation], evidence=[evidence]), [requirement])

    assert summary.required_constraint_conflicts == 1
    assert summary.job_fit == 0.0


def _lexical_term(
    term_id: str,
    text: str,
    visibility: LexicalVisibility,
    *,
    semantic_support: EvidenceStatus | None = None,
    importance: RequirementImportance = RequirementImportance.REQUIRED,
    purpose: str = "candidate_qualifications",
) -> LexicalTerm:
    return LexicalTerm(
        id=term_id,
        term=text,
        canonical_concept_id=None,
        importance=importance,
        source_locations=[
            JobTextLocation(
                source_start=0,
                source_end=len(text),
                section_purpose=purpose,
            )
        ],
        visibility=visibility,
        semantic_support=semantic_support,
    )


def test_lexical_score_is_independent_of_semantic_support() -> None:
    supported_semantics = LexicalAnalysis(
        status=AnalysisStatus.EVALUATED,
        terms=[
            _lexical_term("genai", "GenAI", LexicalVisibility.ABSENT, semantic_support=EvidenceStatus.SUPPORTED),
            _lexical_term("testing", "automated testing", LexicalVisibility.VARIANT),
        ],
    )
    unsupported_semantics = supported_semantics.model_copy(
        update={
            "terms": [
                supported_semantics.terms[0].model_copy(update={"semantic_support": EvidenceStatus.NOT_EVIDENCED}),
                supported_semantics.terms[1],
            ]
        }
    )

    assert score_lexical_analysis(supported_semantics) == score_lexical_analysis(unsupported_semantics)
    assert score_lexical_analysis(supported_semantics).visibility_score == 0.4


def test_illustrative_example_terms_are_excluded_from_lexical_score_and_counts() -> None:
    umbrella = _lexical_term("rituals", "team rituals", LexicalVisibility.ABSENT)
    example = _lexical_term("standups", "standups", LexicalVisibility.ABSENT).model_copy(
        update={
            "illustrative_example": True,
            "source_locations": [
                _lexical_term("standups", "standups", LexicalVisibility.ABSENT).source_locations[0].model_copy(
                    update={"illustrative_example": True}
                )
            ],
        }
    )
    analysis = LexicalAnalysis(
        status=AnalysisStatus.EVALUATED,
        terms=[umbrella, example],
    )

    summary = score_lexical_analysis(analysis)

    assert len(analysis.terms) == 2
    assert summary.absent_count == 1
    assert summary.scorable_fraction == 1.0
    assert summary.visibility_score == 0.0


def test_lexical_term_can_show_semantic_support_without_changing_visibility() -> None:
    requirement = _requirement("ai-tools", _leaf("ai-tools-leaf", "AI tools"))
    evaluation = _leaf_result(requirement.expression, EvidenceStatus.PARTIAL)
    semantic = _semantic([requirement], [evaluation])
    lexical = LexicalAnalysis(
        status=AnalysisStatus.EVALUATED,
        terms=[
            LexicalTerm(
                id="genai",
                term="GenAI",
                canonical_concept_id="scanner:genai",
                importance=RequirementImportance.REQUIRED,
                source_locations=[
                    JobTextLocation(source_start=0, source_end=5, section_purpose="candidate_qualifications")
                ],
                visibility=LexicalVisibility.ABSENT,
            )
        ],
    )

    linked = link_lexical_semantic_support(lexical, [requirement], semantic)

    assert linked.terms[0].visibility is LexicalVisibility.ABSENT
    assert linked.terms[0].semantic_support is EvidenceStatus.PARTIAL
    assert score_lexical_analysis(linked).visibility_score == score_lexical_analysis(lexical).visibility_score


def test_preferred_terms_receive_lower_weight_than_qualification_terms() -> None:
    analysis = LexicalAnalysis(
        status=AnalysisStatus.EVALUATED,
        terms=[
            _lexical_term("python", "Python", LexicalVisibility.EXACT),
            _lexical_term(
                "french",
                "French",
                LexicalVisibility.ABSENT,
                importance=RequirementImportance.PREFERRED,
            ),
        ],
    )

    summary = score_lexical_analysis(analysis)

    assert summary.visibility_score == 1.0 / 1.35


def test_pdf_score_uses_weighted_checks_and_renormalizes_unavailable_checks() -> None:
    analysis = PDFTextRecoveryAnalysis(
        status=PDFRecoveryStatus.WARNING,
        checks=[
            PDFCheck(code="text_retention", status=PDFRecoveryStatus.WARNING, expected_count=10, recovered_count=9),
            PDFCheck(code="reading_order", status=PDFRecoveryStatus.WARNING, expected_count=10, recovered_count=8),
            PDFCheck(code="contact_recovery", status=PDFRecoveryStatus.PASS, expected_count=1, recovered_count=1),
            PDFCheck(code="section_heading_recovery", status=PDFRecoveryStatus.PASS, expected_count=2, recovered_count=2),
            PDFCheck(code="entry_recovery", status=PDFRecoveryStatus.WARNING, expected_count=2, recovered_count=1),
            PDFCheck(code="link_recovery", status=PDFRecoveryStatus.UNAVAILABLE),
            PDFCheck(code="input_size_limit", status=PDFRecoveryStatus.WARNING),
        ],
    )

    summary = score_pdf_recovery(analysis)

    assert summary.recovery_score == (0.35 * 0.9 + 0.25 * 0.8 + 0.15 + 0.10 + 0.10 * 0.5) / 0.95
    assert summary.scorable_fraction == 0.95
    assert summary.scored_check_count == 5
    assert summary.unavailable_check_count == 1


def test_pdf_resource_limit_without_recovery_checks_has_no_numeric_score() -> None:
    analysis = PDFTextRecoveryAnalysis(
        status=PDFRecoveryStatus.WARNING,
        checks=[PDFCheck(code="input_size_limit", status=PDFRecoveryStatus.WARNING)],
    )

    summary = score_pdf_recovery(analysis)

    assert summary.status is ScoreStatus.UNAVAILABLE
    assert summary.recovery_score is None
