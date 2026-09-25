from datetime import date
from types import SimpleNamespace

from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.matching import evaluate_semantic_coverage
from app.scanner.results import EvidenceStatus
from app.services.candidate_evidence import iter_candidate_sources
from app.services.tailoring_opportunities import map_tailoring_opportunities


def test_library_git_is_recoverable_without_inflating_linked_cv_fit() -> None:
    extraction = extract_requirements_from_entities(
        "Qualifications\nBasic familiarity with version control tools such as Git.",
        {"entities": {}},
    )
    linked_cv = {"sections": [{"id": "skills", "type": "skills", "enabled": True, "data": [
        {"id": "tools", "category": "Tools", "items": ["Python"]}
    ]}]}
    library = [{"id": "brain-station", "kind": "experience", "payload": [{
        "id": "brain-station-role", "company": "Brain Station 23", "position": "Associate Software Engineer",
        "description": "Provisioned Linux environments and deployed containerized applications using Docker, Git, and CI/CD pipelines.",
    }]}]
    sources = iter_candidate_sources(library)
    before = evaluate_semantic_coverage(extraction.requirements, linked_cv, as_of=date(2026, 9, 22))
    opportunities, retrieved = map_tailoring_opportunities(extraction, None, linked_cv, sources)
    after = evaluate_semantic_coverage(extraction.requirements, linked_cv, as_of=date(2026, 9, 22))

    assert before.requirements == after.requirements
    assert before.requirements[0].status is EvidenceStatus.NOT_EVIDENCED
    git = next(item for item in opportunities if "git" in item["missing_skills"])
    assert git["operation"] == "SURFACE"
    assert git["source_ids"] == [sources[0].source_id]
    assert retrieved[0]["narrative"] == library[0]["payload"][0]["description"]


def test_promoting_grounded_git_changes_only_the_linked_cv_result() -> None:
    extraction = extract_requirements_from_entities(
        "Qualifications\nBasic familiarity with version control tools such as Git.",
        {"entities": {}},
    )
    cv = {"sections": [{"id": "skills", "type": "skills", "enabled": True, "data": [
        {"id": "tools", "category": "Tools", "items": ["Python", "Git"]}
    ]}]}
    analysis = evaluate_semantic_coverage(extraction.requirements, cv, as_of=date(2026, 9, 22))
    assert analysis.requirements[0].status is EvidenceStatus.SUPPORTED


def test_library_work_context_can_promote_a_skill_listed_without_work_context() -> None:
    extraction = extract_requirements_from_entities(
        "Qualifications\nBasic familiarity with version control tools such as Git.",
        {"entities": {}},
    )
    linked_cv = {"sections": [{"id": "skills", "type": "skills", "enabled": True, "data": [
        {"id": "tools", "category": "Tools", "items": ["Git"]}
    ]}]}
    library = [{"id": "brain-station", "kind": "experience", "payload": [{
        "id": "brain-station-role", "company": "Brain Station 23", "position": "Associate Software Engineer",
        "description": "Used Git for version control while shipping software features.",
    }]}]

    sources = iter_candidate_sources(library)
    opportunities, retrieved = map_tailoring_opportunities(
        extraction,
        None,
        linked_cv,
        sources,
    )

    git = next(item for item in opportunities if "poorly_surfaced_skills" in item and item["poorly_surfaced_skills"])
    assert git["poorly_surfaced_skills"] == ["git"]
    assert git["operation"] == "PROMOTE"
    assert retrieved[0]["source_id"] == sources[0].source_id


def test_role_relevant_library_material_is_retrieved_even_when_scan_says_covered() -> None:
    extraction = extract_requirements_from_entities(
        "Qualifications\nBasic familiarity with version control tools such as Git.",
        {"entities": {}},
    )
    cv = {"sections": [{"id": "skills", "type": "skills", "enabled": True, "data": [
        {"id": "tools", "category": "Tools", "items": ["Git"]}
    ]}]}
    library = [{"id": "brain-station", "kind": "experience", "payload": [{
        "id": "brain-station-role", "company": "Brain Station 23", "position": "Associate Software Engineer",
        "description": "Used Git for version control while shipping software features in a collaborative team.",
    }]}]
    sources = iter_candidate_sources(library)
    source_scan = SimpleNamespace(
        semantic=SimpleNamespace(requirements=[SimpleNamespace(
            requirement_id=extraction.requirements[0].id,
            status=EvidenceStatus.SUPPORTED,
        )]),
        lexical=SimpleNamespace(terms=[]),
    )

    opportunities, retrieved = map_tailoring_opportunities(extraction, source_scan, cv, sources)

    git = next(item for item in opportunities if item["requirement_id"] == extraction.requirements[0].id)
    assert git["current_cv_status"] == "supported"
    assert git["target_priority"] == extraction.requirements[0].importance.value
    assert git["source_ids"] == [sources[0].source_id]
    assert retrieved[0]["narrative"] == library[0]["payload"][0]["description"]
    assert "verify before making a claim" not in git["source_note"]
