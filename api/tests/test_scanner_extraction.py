import json
from pathlib import Path
from typing import Any

import pytest

from app.scanner.extraction import (
    SCANNER_EXTRACTOR_VERSION,
    ScannerRequirementExtractor,
    candidate_facing_segments,
    extract_requirements_from_entities,
)
from app.scanner.requirements import (
    AllExpression,
    AnyExpression,
    CandidateFacingKind,
    ExamplesExpression,
    ExpectationKind,
    ExperienceDurationConstraint,
    MinimumYearsConstraint,
    RequirementImportance,
    RequirementLeaf,
    SectionPurpose,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "scanner" / "alayacare"


def _span(source: str, label: str, phrase: str, *, occurrence: int = 0, confidence: float = 0.92) -> dict[str, Any]:
    start = -1
    for _ in range(occurrence + 1):
        start = source.index(phrase, start + 1)
    return {"text": phrase, "start": start, "end": start + len(phrase), "confidence": confidence}


def test_typed_concept_spans_do_not_promote_employer_copy() -> None:
    source = "About the Company\nOur cloud platform uses Python and Docker for home care.\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "hard_skill": [_span(source, "hard_skill", "Python"), _span(source, "hard_skill", "Docker")],
            }
        },
    )

    assert result.requirements == []
    assert result.warnings == ["concept_spans_not_promoted:18"]


def test_configured_model_version_includes_requirement_normalization_contract(monkeypatch) -> None:
    class Provider:
        model_name = "example/model"
        revision = "abc123"

        def extract_raw_spans(self, _source):
            return []

    monkeypatch.setattr("app.scanner.extraction.get_requirement_extractor", lambda: Provider())

    result = ScannerRequirementExtractor().extract("What You Bring\nFamiliarity with Python.")

    assert SCANNER_EXTRACTOR_VERSION == "gliner2.5-structured-v7"
    assert result.extractor_version == f"example/model@abc123+{SCANNER_EXTRACTOR_VERSION}"


def test_candidate_section_and_concept_span_jointly_recover_implicit_skill_list() -> None:
    source = "Qualifications\nPython or Java.\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "hard_skill": [
                    _span(source, "hard_skill", "Python"),
                    _span(source, "hard_skill", "Java"),
                ]
            }
        },
    )

    assert len(result.requirements) == 1
    assert result.requirements[0].source.original_text == "Python or Java."
    assert result.requirements[0].source.candidate_signals[-1].kind.value == "concept_in_candidate_section"


def test_concept_spans_in_unknown_section_do_not_admit_implicit_skill_list() -> None:
    source = "Technical toolkit\nPython or Java.\n"
    result = extract_requirements_from_entities(
        source,
        {"entities": {"hard_skill": [_span(source, "hard_skill", "Python")] }},
    )

    assert result.requirements == []


def test_candidate_facing_lexical_segments_include_bare_candidate_skill_lists() -> None:
    source = "Qualifications\nPython, Java, and Docker.\nTechnical Toolkit\nOur platform uses Kotlin.\n"

    segments = candidate_facing_segments(source)

    assert [segment.text for segment in segments] == ["Python, Java, and Docker."]


def test_unknown_heading_remains_conservative_for_concept_only_skill_lists() -> None:
    source = "Technical toolkit\nPython or Java.\n"
    result = extract_requirements_from_entities(
        source,
        {"entities": {"hard_skill": [_span(source, "hard_skill", "Python")] }},
    )

    assert result.requirements == []


def test_unknown_or_candidate_section_alone_does_not_admit_every_sentence() -> None:
    source = "Qualifications\nOur team values kindness and transparency.\n"
    result = extract_requirements_from_entities(source, {"entities": {}})

    assert result.requirements == []


def test_candidate_sentence_signal_can_override_a_non_authoritative_section() -> None:
    source = "About the Company\nYou must be able to use Python for customer implementation.\n"
    result = extract_requirements_from_entities(
        source,
        {"entities": {"hard_skill": [_span(source, "hard_skill", "Python")]}},
    )

    assert len(result.requirements) == 1
    assert result.requirements[0].source.original_text == "You must be able to use Python for customer implementation."
    assert result.requirements[0].source.section.purpose is SectionPurpose.EMPLOYER_INFORMATION


def test_nested_any_and_all_structure_is_built_from_conjunction_scope() -> None:
    source = "Candidate Requirements\nExperience with Python or Java, and React.\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "hard_skill": [
                    _span(source, "hard_skill", "Python"),
                    _span(source, "hard_skill", "Java"),
                    _span(source, "hard_skill", "React"),
                ]
            }
        },
    )

    requirement = result.requirements[0]
    assert isinstance(requirement.expression, AllExpression)
    alternatives, react = requirement.expression.children
    assert isinstance(alternatives, AnyExpression)
    assert [item.concept.name for item in alternatives.children] == ["python", "java"]
    assert isinstance(react, RequirementLeaf)
    assert react.concept.name == "react"
    assert requirement.source.original_text == source[requirement.source.source_start : requirement.source.source_end]


def _logical_requirement(expression_text: str, concepts: list[str]):
    source = f"Qualifications\nExperience with {expression_text}.\n"
    sentence_start = source.index(expression_text)
    spans = []
    for concept in concepts:
        start = source.index(concept, sentence_start)
        spans.append({"text": concept, "start": start, "end": start + len(concept), "confidence": 0.92})
    return extract_requirements_from_entities(
        source,
        {"entities": {"hard_skill": spans}},
    ).requirements[0]


def test_logical_expression_parser_preserves_nested_alternatives_and_groups() -> None:
    assert isinstance(_logical_requirement("A or B", ["A", "B"]).expression, AnyExpression)

    comma_or = _logical_requirement("A, B, or C", ["A", "B", "C"]).expression
    assert isinstance(comma_or, AnyExpression)
    assert [child.concept.name for child in comma_or.children] == ["A", "B", "C"]

    parenthesized_or = _logical_requirement("(A OR B) OR D", ["A", "B", "D"]).expression
    assert isinstance(parenthesized_or, AnyExpression)
    assert [child.concept.name for child in parenthesized_or.children] == ["A", "B", "D"]

    and_inside_or = _logical_requirement("(A AND B) OR C", ["A", "B", "C"]).expression
    assert isinstance(and_inside_or, AnyExpression)
    assert isinstance(and_inside_or.children[0], AllExpression)
    assert [child.concept.name for child in and_inside_or.children[0].children] == ["A", "B"]

    or_inside_and = _logical_requirement("A AND (B OR C)", ["A", "B", "C"]).expression
    assert isinstance(or_inside_and, AllExpression)
    assert isinstance(or_inside_and.children[1], AnyExpression)


def test_education_alternatives_are_nested_and_a_computer_science_degree_can_satisfy_one_branch() -> None:
    source = (
        "Qualifications and Experience\n"
        "Post-secondary education in Computer Science, Software Development, Information Technology, "
        "or a related program, or equivalent practical experience.\n"
    )
    requirement = extract_requirements_from_entities(source, {"entities": {}}).requirements[0]

    assert requirement.family.value == "education"
    assert isinstance(requirement.expression, AnyExpression)
    education_fields, equivalent = requirement.expression.children
    assert isinstance(education_fields, AnyExpression)
    assert [child.concept.name for child in education_fields.children] == [
        "Computer Science",
        "Software Development",
        "Information Technology",
        "related program",
    ]
    assert equivalent.concept.name == "equivalent practical experience"


@pytest.mark.parametrize(
    ("duration_text", "constraint_type"),
    [
        ("0–2 years", ExperienceDurationConstraint),
        ("approximately 0–2 years", ExperienceDurationConstraint),
        ("1+ years", MinimumYearsConstraint),
        ("at least 2 years", MinimumYearsConstraint),
        ("2–4 years", ExperienceDurationConstraint),
        ("up to 3 years", ExperienceDurationConstraint),
        ("less than 5 years", ExperienceDurationConstraint),
        ("3 years preferred", MinimumYearsConstraint),
    ],
)
def test_numeric_experience_phrases_become_constraints_not_requirement_children(duration_text: str, constraint_type: type) -> None:
    source = f"Qualifications\n{duration_text} of software development experience.\n"
    requirement = extract_requirements_from_entities(source, {"entities": {}}).requirements[0]
    leaves = _walk_leaves(requirement.expression)

    assert len(leaves) == 1
    assert leaves[0].concept.name == "software development experience"
    assert len(leaves[0].constraints) == 1
    assert isinstance(leaves[0].constraints[0], constraint_type)


def test_convverge_duration_keeps_bounds_and_allowed_evidence_sources() -> None:
    source = (
        "Qualifications\nApproximately 0–2 years of software development experience, including "
        "internships, co-op placements, academic projects, personal projects, or professional experience.\n"
    )
    requirement = extract_requirements_from_entities(source, {"entities": {}}).requirements[0]
    constraint = _walk_leaves(requirement.expression)[0].constraints[0]

    assert isinstance(constraint, ExperienceDurationConstraint)
    assert (constraint.min_years, constraint.max_years, constraint.approximate) == (0, 2, True)
    assert constraint.allowed_evidence_sources == [
        "internship",
        "co-op placement",
        "academic project",
        "personal project",
        "professional experience",
    ]


def test_candidate_facing_classifier_separates_employer_copy_and_expectations() -> None:
    source = (
        "About Our Team\nYou'll work alongside developers, architects, and designers.\n"
        "Benefits\nWe offer mentorship and professional development.\n"
        "About You\nWe are looking for someone who asks thoughtful questions.\n"
        "What We Expect\nYou bring strong fundamentals.\n"
        "Key Responsibilities\nYou will be responsible for testing fixes.\n"
    )
    requirements = extract_requirements_from_entities(source, {"entities": {}}).requirements
    by_text = {item.source.original_text: item for item in requirements}

    assert "You'll work alongside developers, architects, and designers." not in by_text
    assert "We offer mentorship and professional development." not in by_text
    assert by_text["We are looking for someone who asks thoughtful questions."].classification is CandidateFacingKind.CANDIDATE_REQUIREMENT
    assert by_text["You bring strong fundamentals."].classification is CandidateFacingKind.CANDIDATE_EXPECTATION
    assert by_text["You will be responsible for testing fixes."].classification is CandidateFacingKind.JOB_RESPONSIBILITY


def test_candidate_expectation_sentence_is_decomposed_into_provenanced_traits() -> None:
    source = (
        "What We Expect\nYou may be early in your career, but you bring strong fundamentals, "
        "a willingness to ask thoughtful questions, and a commitment to building reliable, high-quality work.\n"
    )
    requirement = extract_requirements_from_entities(source, {"entities": {}}).requirements[0]
    leaves = _walk_leaves(requirement.expression)

    assert requirement.classification is CandidateFacingKind.CANDIDATE_EXPECTATION
    assert [leaf.concept.name for leaf in leaves] == [
        "strong fundamentals",
        "a willingness to ask thoughtful questions",
        "a commitment to building reliable, high-quality work",
    ]
    assert all(leaf.concept.source_text for leaf in leaves)


def test_explicit_at_least_one_requirement_builds_any_and_keeps_examples() -> None:
    source = "What You Bring\nFamiliarity with at least one programming language (e.g., Python, TypeScript, JavaScript, PHP, or similar).\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "hard_skill": [
                    _span(source, "hard_skill", "Python"),
                    _span(source, "hard_skill", "TypeScript"),
                    _span(source, "hard_skill", "JavaScript"),
                    _span(source, "hard_skill", "PHP"),
                ]
            }
        },
    )

    requirement = result.requirements[0]
    assert isinstance(requirement.expression, AnyExpression)
    assert requirement.expression.modifiers.list_semantics == "examples"
    assert len(requirement.expression.children) == 4
    assert requirement.importance is RequirementImportance.REQUIRED
    assert requirement.expression.children[0].expectation.kind.value == "familiarity"


def test_such_as_list_is_an_umbrella_with_nonmandatory_examples() -> None:
    source = "What You’ll Do\nParticipate in team rituals such as standups, demos, and retrospectives.\n"
    result = extract_requirements_from_entities(source, {"entities": {}})

    expression = result.requirements[0].expression
    assert isinstance(expression, ExamplesExpression)
    assert isinstance(expression.subject, RequirementLeaf)
    assert expression.subject.concept.name == "team rituals"
    assert [item.concept.name for item in expression.examples] == ["standups", "demos", "retrospectives"]
    assert all(item.modifiers.optional for item in expression.examples)
    assert expression.min_supporting_examples == 2


def test_one_item_example_list_requires_only_one_example() -> None:
    source = "What You Bring\nFamiliarity with programming languages such as Python.\n"
    result = extract_requirements_from_entities(
        source,
        {"entities": {"hard_skill": [_span(source, "hard_skill", "Python")]}},
    )

    expression = result.requirements[0].expression

    assert isinstance(expression, ExamplesExpression)
    assert len(expression.examples) == 1
    assert expression.min_supporting_examples == 1


def test_scoped_behavioral_domains_form_one_scored_obligation() -> None:
    source = (
        "What You Bring\nCuriosity about current industry trends in technology, performance, "
        "and software development practices.\n"
    )
    result = extract_requirements_from_entities(source, {"entities": {}})

    assert len(result.requirements) == 1
    expression = result.requirements[0].expression
    assert isinstance(expression, RequirementLeaf)
    assert expression.concept.name == "industry trends"
    assert expression.expectation.kind is ExpectationKind.CURIOSITY
    assert expression.modifiers.scope == "technology, performance, and software development practices"


def test_scoped_expectation_patterns_do_not_score_domains_as_separate_skills() -> None:
    examples = [
        ("Knowledge of trends in cloud infrastructure and security tooling.", ExpectationKind.KNOWLEDGE),
        ("Knowledge of trends in emerging specialisms and next-generation methods.", ExpectationKind.KNOWLEDGE),
        ("Interest in developments across backend services and data platforms.", ExpectationKind.INTEREST),
        ("Awareness of issues related to accessibility and performance.", ExpectationKind.KNOWLEDGE),
        ("Curiosity about advances in AI and software performance.", ExpectationKind.CURIOSITY),
    ]

    for sentence, expectation in examples:
        result = extract_requirements_from_entities(f"What You Bring\n{sentence}\n", {"entities": {}})
        expression = result.requirements[0].expression

        assert isinstance(expression, RequirementLeaf), sentence
        assert expression.expectation.kind is expectation, sentence
        assert expression.modifiers.scope, sentence


def test_experience_areas_such_as_remain_one_umbrella_with_examples() -> None:
    source = "What You Bring\nExperience working in areas such as cloud platforms, databases, and APIs.\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "hard_skill": [
                    _span(source, "hard_skill", "cloud platforms"),
                    _span(source, "hard_skill", "databases"),
                    _span(source, "hard_skill", "APIs"),
                ]
            }
        },
    )

    expression = result.requirements[0].expression

    assert isinstance(expression, ExamplesExpression)
    assert expression.subject.concept.name == "working in areas"
    assert all(item.modifiers.optional for item in expression.examples)


def test_genuine_coordinated_skills_remain_independent_all_obligations() -> None:
    source = "What You Bring\nExperience with Python, Docker, and PostgreSQL.\n"
    result = extract_requirements_from_entities(source, {"entities": {}})

    expression = result.requirements[0].expression
    assert isinstance(expression, AllExpression)
    assert [leaf.concept.name for leaf in _walk_leaves(expression)] == ["python", "docker", "postgresql"]


def test_examples_expression_preserves_independent_preceding_skill() -> None:
    source = (
        "What You Bring\nStrong Python skills and familiarity with cloud platforms "
        "such as AWS and Azure.\n"
    )
    result = extract_requirements_from_entities(source, {"entities": {}})

    expression = result.requirements[0].expression
    assert isinstance(expression, AllExpression)
    assert isinstance(expression.children[0], RequirementLeaf)
    assert expression.children[0].concept.name == "python"
    examples = expression.children[1]
    assert isinstance(examples, ExamplesExpression)
    assert examples.subject.concept.name == "cloud platforms"
    assert [item.concept.name for item in examples.examples] == ["aws", "azure"]
    assert all(item.modifiers.optional for item in examples.examples)

    source_start = source.index("Strong Python skills")
    model_output = {
        "entities": {
            "hard_skill": [
                _span(source, "hard_skill", "Python"),
                _span(source, "hard_skill", "AWS"),
                _span(source, "hard_skill", "Azure"),
            ],
            "domain_knowledge": [
                {
                    "text": "cloud platforms",
                    "start": source.index("cloud platforms", source_start),
                    "end": source.index("cloud platforms", source_start) + len("cloud platforms"),
                    "confidence": 0.92,
                }
            ],
        }
    }
    typed_result = extract_requirements_from_entities(source, model_output)
    typed_expression = typed_result.requirements[0].expression

    assert isinstance(typed_expression, AllExpression)
    assert isinstance(typed_expression.children[0], RequirementLeaf)
    assert typed_expression.children[0].concept.name == "python"
    typed_examples = typed_expression.children[1]
    assert isinstance(typed_examples, ExamplesExpression)
    assert typed_examples.subject.concept.name == "cloud platforms"


def _including_requirement(source: str, concepts: list[str]):
    sentence = source.split("\n", 1)[1].strip()
    sentence_start = source.index(sentence)

    def sentence_span(label: str, phrase: str) -> dict[str, Any]:
        start = source.index(phrase, sentence_start)
        return {"text": phrase, "start": start, "end": start + len(phrase), "confidence": 0.92}

    entities: dict[str, list[dict[str, Any]]] = {
        "candidate_requirement": [_span(source, "candidate_requirement", sentence)],
        "hard_skill": [sentence_span("hard_skill", concept) for concept in concepts],
    }
    if "cloud technologies" in sentence:
        entities["domain_knowledge"] = [sentence_span("domain_knowledge", "cloud technologies")]
    return extract_requirements_from_entities(source, {"entities": entities}).requirements[0]


def test_including_list_keeps_its_umbrella_and_marks_members_illustrative() -> None:
    source = "What You Bring\nLearn practices, including A, B, and C.\n"
    requirement = _including_requirement(source, ["A", "B", "C"])

    assert isinstance(requirement.expression, ExamplesExpression)
    assert requirement.expression.subject.concept.name == "Learn practices"
    assert [child.concept.name for child in requirement.expression.examples] == ["A", "B", "C"]
    assert all(child.modifiers.optional for child in requirement.expression.examples)
    assert requirement.expression.min_supporting_examples == 1


def test_including_list_preserves_independent_prefix_and_cloud_umbrella() -> None:
    source = "What You Bring\nExperience with cloud technologies, including AWS and Azure.\n"
    requirement = _including_requirement(source, ["AWS", "Azure"])

    assert isinstance(requirement.expression, ExamplesExpression)
    assert requirement.expression.subject.concept.name == "cloud technologies"
    assert [child.concept.name for child in requirement.expression.examples] == ["aws", "azure"]

    source_with_independent_concept = (
        "What You Bring\nExperience with Python and cloud technologies, including AWS and Azure.\n"
    )
    requirement_with_independent_concept = _including_requirement(
        source_with_independent_concept,
        ["Python", "AWS", "Azure"],
    )

    assert isinstance(requirement_with_independent_concept.expression, AllExpression)
    prefix, examples = requirement_with_independent_concept.expression.children
    assert prefix.concept.name == "python"
    assert isinstance(examples, ExamplesExpression)
    assert examples.subject.concept.name == "cloud technologies"


def test_alayacare_including_span_is_not_a_mandatory_sibling() -> None:
    sentence = (
        "Learn and apply modern development practices, including Implementing with AI, CI/CD, "
        "containerization, and monitoring."
    )
    source = f"What You’ll Do\n{sentence}\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "candidate_requirement": [_span(source, "candidate_requirement", sentence)],
                "domain_knowledge": [_span(source, "domain_knowledge", "modern development practices")],
            }
        },
    )

    expression = result.requirements[0].expression
    assert isinstance(expression, ExamplesExpression)
    assert expression.subject.concept.name == "modern development practices"
    assert [leaf.concept.name for leaf in expression.examples] == [
        "AI-assisted development",
        "ci/cd",
        "containerization",
        "monitoring",
    ]


def test_demonstrated_ai_interest_preserves_the_application_expectation() -> None:
    source = (
        "What You Bring\n"
        "Demonstrated interest in AI tools, with a proactive mindset toward integrating them into day-to-day work to drive efficiency and innovation.\n"
    )
    result = extract_requirements_from_entities(source, {"entities": {}})

    expression = result.requirements[0].expression
    assert isinstance(expression, AllExpression)
    assert [item.expectation.kind for item in expression.children] == [
        ExpectationKind.INTEREST,
        ExpectationKind.DEMONSTRATED_APPLICATION,
    ]
    assert all(item.concept.name == "AI tools" for item in expression.children)
    assert "day-to-day work" in expression.children[1].expectation.qualifier


def test_asset_language_phrase_is_preferred_and_languages_get_constraints() -> None:
    source = "What You Bring to the Team\nBilingual in French and English is considered an asset.\n"
    result = extract_requirements_from_entities(
        source,
        {
            "entities": {
                "hard_skill": [
                    _span(source, "hard_skill", "French"),
                    _span(source, "hard_skill", "English"),
                ]
            }
        },
    )

    requirement = result.requirements[0]
    assert requirement.importance is RequirementImportance.PREFERRED
    assert isinstance(requirement.expression, AllExpression)
    for language in requirement.expression.children:
        assert any(constraint.kind == "language_proficiency" for constraint in language.constraints)


def test_guidance_supervision_and_learning_purpose_are_context_not_requirements() -> None:
    source = (
        "What You’ll Do\n"
        "Write and maintain automated tests with guidance from team members.\n"
        "Help investigate, reproduce, and resolve bugs under supervision.\n"
        "Pair-program with senior developers and participate in code reviews to learn best practices.\n"
    )
    result = extract_requirements_from_entities(source, {"entities": {}})
    by_source = {item.source.original_text: item for item in result.requirements}

    assert [item.kind.value for item in by_source[source.splitlines()[1]].contextual_modifiers] == ["guidance"]
    assert [item.kind.value for item in by_source[source.splitlines()[2]].contextual_modifiers] == ["supervision"]
    assert [item.kind.value for item in by_source[source.splitlines()[3]].contextual_modifiers] == ["learning_purpose"]
    assert all(
        leaf.expectation.kind.value != "other"
        for item in result.requirements
        for leaf in _walk_leaves(item.expression)
    )


def test_low_confidence_about_role_section_does_not_make_every_duty_required() -> None:
    source = (
        "About the Role\n"
        "As a Junior Developer, you will work closely with experienced developers to contribute to real product features.\n"
        "You will contribute to meaningful projects while learning modern development practices, tools, and workflows.\n"
    )
    result = extract_requirements_from_entities(source, {"entities": {}})

    assert len(result.requirements) == 2
    assert all(item.importance is RequirementImportance.UNKNOWN for item in result.requirements)


def test_year_constraint_is_attached_to_taxonomy_hard_skill_component() -> None:
    source = "What You Bring\nMust have at least 3 years of Python experience.\n"
    result = extract_requirements_from_entities(
        source,
        {"entities": {"hard_skill": [_span(source, "hard_skill", "Python")]}},
    )

    leaf = _walk_leaves(result.requirements[0].expression)[0]
    assert any(item.kind == "minimum_years" and item.years == 3 for item in leaf.constraints)


def test_alayacare_company_hiring_and_accommodation_spans_are_not_requirements() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    hiring_start = job.index("AlayaCare uses AI tools during our hiring process")
    accommodation_start = job.index("accommodation during the application process")
    company_start = job.index("Our cloud-based platform")
    output = {
        "entities": {
            "hard_skill": [
                {"text": "AI tools", "start": hiring_start + len("AlayaCare uses "), "end": hiring_start + len("AlayaCare uses AI tools"), "confidence": 0.99},
                {"text": "accommodation", "start": accommodation_start, "end": accommodation_start + len("accommodation"), "confidence": 0.98},
                {"text": "cloud-based platform", "start": company_start, "end": company_start + len("cloud-based platform"), "confidence": 0.97},
            ]
        }
    }

    result = extract_requirements_from_entities(job, output)

    assert all(
        requirement.source.original_text not in {item["source_text"] for item in json.loads((FIXTURE_DIR / "annotations.json").read_text())["expected_non_requirements"]}
        for requirement in result.requirements
    )
    assert not any("hiring process" in requirement.source.original_text for requirement in result.requirements)
    assert not any("accommodation" in requirement.source.original_text for requirement in result.requirements)


def test_alayacare_compound_and_importance_regressions_normalize_without_model_spans() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    result = extract_requirements_from_entities(job, {"entities": {}})
    requirements = {item.source.original_text: item for item in result.requirements}

    modern_text = "Learn and apply modern development practices, including Implementing with AI, CI/CD, containerization, and monitoring."
    modern = requirements[modern_text]
    assert isinstance(modern.expression, ExamplesExpression)
    modern_names = [leaf.concept.name for leaf in modern.expression.examples]
    assert modern_names == ["AI-assisted development", "ci/cd", "containerization", "monitoring"]

    asset_text = "Bilingual in French and English is considered an asset."
    assert requirements[asset_text].importance is RequirementImportance.PREFERRED

    excluded_fragments = ("At AlayaCare, we are more than", "Our cloud-based platform", "during our hiring process", "accommodation during the application process")
    assert not any(any(fragment in text for fragment in excluded_fragments) for text in requirements)
    assert not any("This role is based in the Greater Montreal Area" in text for text in requirements)

    role_overview = next(item for item in result.requirements if item.source.original_text.startswith("As a Junior Fullstack Developer"))
    assert role_overview.family.value == "responsibility"
    assert "python" not in [leaf.concept.name for leaf in _walk_leaves(role_overview.expression)]


def _walk_leaves(expression: Any) -> list[RequirementLeaf]:
    if isinstance(expression, RequirementLeaf):
        return [expression]
    if isinstance(expression, ExamplesExpression):
        return [
            *_walk_leaves(expression.subject),
            *[leaf for item in expression.examples for leaf in _walk_leaves(item)],
        ]
    return [leaf for child in expression.children for leaf in _walk_leaves(child)]
