"""Contracts for requirement-v2 extraction, matching, and selection."""

from app.services.relevance import (
    evaluate_requirement_relevance,
    extract_requirements,
    requirement_row_removal_loss,
    select_requirement_library_rows,
)
from app.services.requirement_extractor import requirements_from_model_output, to_job_requirements


def _span(source: str, value: str) -> dict[str, object]:
    start = source.index(value)
    return {"text": value, "start": start, "end": start + len(value), "confidence": 0.9}


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


def test_demonstrated_skill_evidence_outweighs_a_skills_list_match():
    requirements = extract_requirements("Engineer", "Python")
    skills_result = evaluate_requirement_relevance(
        requirements,
        [{"type": "skills", "enabled": True, "data": [{"items": ["Python"]}]}],
    )
    project_result = evaluate_requirement_relevance(
        requirements,
        [{"type": "projects", "enabled": True, "data": [{"name": "API", "description": "Built Python service"}]}],
    )

    assert project_result.requirements[0].score > skills_result.requirements[0].score
    assert project_result.score == 100
    assert skills_result.score == 85


def test_logical_any_group_accepts_one_selected_skill_but_not_an_unrelated_one():
    source = "You need either Python or Kotlin."
    extracted = requirements_from_model_output(
        source,
        {
            "entities": {
                "candidate_requirement": [_span(source, source)],
                "hard_skill": [_span(source, "Python"), _span(source, "Kotlin")],
            }
        },
    )
    requirements = to_job_requirements(extracted)

    kotlin = evaluate_requirement_relevance(
        requirements,
        [{"type": "skills", "enabled": True, "data": [{"items": ["Kotlin"]}]}],
    )
    unrelated = evaluate_requirement_relevance(
        requirements,
        [{"type": "skills", "enabled": True, "data": [{"items": ["Java"]}]}],
    )

    assert kotlin.requirements[0].covered is True
    assert unrelated.requirements[0].covered is False


def test_logical_all_group_retains_partial_credit_without_calling_it_covered():
    source = "Python and AWS experience required."
    extracted = requirements_from_model_output(
        source,
        {
            "entities": {
                "candidate_requirement": [_span(source, source)],
                "hard_skill": [_span(source, "Python"), _span(source, "AWS")],
            }
        },
    )
    requirements = to_job_requirements(extracted)
    result = evaluate_requirement_relevance(
        requirements,
        [{"type": "skills", "enabled": True, "data": [{"items": ["Python"]}]}],
    )

    assert 0 < result.requirements[0].score < 0.65
    assert result.requirements[0].covered is False


def test_years_below_minimum_can_rank_but_cannot_be_covered():
    requirements = extract_requirements("Engineer", "5+ years of experience")
    result = evaluate_requirement_relevance(
        requirements,
        [{"type": "experience", "enabled": True, "data": [{"description": "3 years of experience"}]}],
    )

    assert 0 < result.requirements[0].score < 0.65
    assert result.requirements[0].covered is False


def test_lower_degree_level_receives_partial_credit_without_full_coverage():
    requirements = extract_requirements("Engineer", "Master's degree required")
    result = evaluate_requirement_relevance(
        requirements,
        [{"type": "education", "enabled": True, "data": [{"degree": "Bachelor of Science"}]}],
    )

    assert 0 < result.requirements[0].score < 0.65
    assert result.requirements[0].covered is False


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

    assert [row.kind for row in rows] == ["education", "project"]
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
