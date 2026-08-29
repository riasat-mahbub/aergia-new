"""Contracts for requirement-v2 extraction, matching, and selection."""

from app.services.relevance import (
    evaluate_requirement_relevance,
    extract_requirements,
    requirement_row_removal_loss,
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
    assert result.coverage_score == 100
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


def test_section_cues_classify_certifications_and_research():
    requirements = extract_requirements(
        "Network Engineer",
        "CCNA certification required\nResearch publications preferred",
    )

    assert {item.type for item in requirements} == {"certification", "research"}
    assert {item.canonical for item in requirements} == {"ccna", "research"}


def test_education_is_a_baseline_and_job_evidence_drives_other_sections():
    requirements = extract_requirements("Frontend Engineer", "React")
    rows = select_requirement_library_rows(
        requirements,
        [
            {"id": "education", "kind": "education", "payload": [{"id": "edu", "degree": "BSc"}]},
            {"id": "skill", "kind": "skill", "payload": [{"id": "skill", "items": ["React"]}]},
            {
                "id": "project",
                "kind": "project",
                "payload": [{"id": "project", "name": "Dashboard", "tech_stack": ["React"]}],
            },
            {"id": "research", "kind": "research", "payload": [{"id": "research", "title": "History"}]},
        ],
    )

    assert [row.kind for row in rows] == ["education", "skill", "project"]
    assert rows[0].selection_reasons == ("baseline_education",)


def test_specific_certification_and_research_evidence_can_drive_selection():
    certification_requirements = extract_requirements("Network Engineer", "CCNA required")
    certification_rows = select_requirement_library_rows(
        certification_requirements,
        [
            {"id": "experience", "kind": "experience", "payload": [{"id": "exp", "description": "Networking"}]},
            {"id": "certification", "kind": "certification", "payload": [{"id": "cert", "name": "CCNA"}]},
        ],
    )
    assert [row.kind for row in certification_rows] == ["certification"]

    research_requirements = extract_requirements("Research Scientist", "Research publications required")
    research_rows = select_requirement_library_rows(
        research_requirements,
        [
            {"id": "project", "kind": "project", "payload": [{"id": "project", "description": "Research"}]},
            {"id": "research", "kind": "research", "payload": [{"id": "research", "title": "Research publication"}]},
        ],
    )
    assert [row.kind for row in research_rows][0] == "research"


def test_required_evidence_is_protected_from_fit_removal():
    requirements = extract_requirements("Network Engineer", "CCNA required")
    rows = select_requirement_library_rows(
        requirements,
        [
            {"id": "certification", "kind": "certification", "payload": [{"id": "cert", "name": "CCNA"}]},
        ],
    )
    certification = next(row for row in rows if row.kind == "certification")

    assert requirement_row_removal_loss(requirements, certification, []) == float("inf")
