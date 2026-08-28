"""Contracts for requirement-v1 extraction, matching, and selection."""

from app.services.relevance import (
    evaluate_requirement_relevance,
    extract_requirements,
    select_requirement_library_rows,
)


def test_extraction_is_atomic_and_respects_required_preferred_and_negation():
    requirements = extract_requirements(
        "Backend Engineer",
        "Requirements:\nPython\nPostgres\nPreferred:\nKubernetes\nNot required:\nRust",
    )

    by_name = {requirement.canonical or requirement.normalized: requirement for requirement in requirements}
    assert by_name["python"].required is True
    assert by_name["postgresql"].required is True
    assert by_name["kubernetes"].required is False
    assert by_name["rust"].required is False
    assert len(requirements) == 4


def test_constraints_use_experience_dates_and_degree_level():
    requirements = extract_requirements(
        "Engineer",
        "5+ years of experience\nBachelor's degree in Computer Science",
    )
    result = evaluate_requirement_relevance(
        requirements,
        [
            {
                "type": "experience",
                "enabled": True,
                "data": [{"company": "Acme", "start_date": "2018-01", "current": True}],
            },
            {
                "type": "education",
                "enabled": True,
                "data": [{"degree": "Bachelor of Science"}],
            },
        ],
    )

    assert result.score == 100
    assert all(match.covered for match in result.requirements)
    assert {match.best_evidence.method for match in result.requirements if match.best_evidence} == {"constraint"}


def test_fuzzy_spelling_is_bounded_and_explainable():
    requirements = extract_requirements("Engineer", "Kubernets")
    result = evaluate_requirement_relevance(
        requirements,
        [{"type": "skills", "enabled": True, "data": [{"category": "Cloud", "items": ["Kubernetes"]}]}],
    )

    match = result.requirements[0]
    assert match.covered is True
    assert match.best_evidence is not None
    assert match.best_evidence.method == "fuzzy"


def test_disabled_sections_do_not_provide_relevance_evidence():
    requirements = extract_requirements("Engineer", "Python")
    result = evaluate_requirement_relevance(
        requirements,
        [{"type": "skills", "enabled": False, "data": [{"items": ["Python"]}]}],
    )

    assert result.score == 0
    assert result.covered_requirements == 0
    assert result.requirements[0].best_evidence is None


def test_greedy_selection_avoids_duplicate_rows_after_coverage():
    requirements = extract_requirements("Engineer", "Python")
    rows = select_requirement_library_rows(
        requirements,
        [
            {"id": "first", "kind": "skill", "payload": [{"id": "row-1", "items": ["Python"]}]},
            {"id": "second", "kind": "skill", "payload": [{"id": "row-2", "items": ["Python"]}]},
        ],
    )

    assert [row.source_row_id for row in rows] == ["row-1"]
    assert rows[0].covered_requirement_ids == ("req-001",)
