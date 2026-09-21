import json
from pathlib import Path
from typing import Any

from app.scanner.extraction import candidate_facing_segments, extract_requirements_from_entities
from app.scanner.requirements import AllExpression, AnyExpression, RequirementImportance, RequirementLeaf, SectionPurpose


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
    assert isinstance(modern.expression, AllExpression)
    modern_names = [leaf.concept.name for leaf in _walk_leaves(modern.expression)]
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
    return [leaf for child in expression.children for leaf in _walk_leaves(child)]
