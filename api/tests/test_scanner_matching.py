from datetime import date
from pathlib import Path
from typing import Any

from app.scanner.matching import evaluate_semantic_coverage, flatten_cv_text
from app.scanner.requirements import (
    Concept,
    Expectation,
    ExpectationKind,
    ExamplesExpression,
    MinimumYearsConstraint,
    Requirement,
    RequirementFamily,
    RequirementImportance,
    RequirementLeaf,
    RequirementSource,
)
from app.scanner.results import EvidenceMethod, EvidenceStatus
from app.scanner.extraction import extract_requirements_from_entities


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "scanner" / "alayacare"


def _field(key: str, text: str) -> dict[str, Any]:
    return {"key": key, "runs": [{"text": text}]}


def _cv_fixture() -> dict[str, Any]:
    return {
        "sections": [
            {
                "id": "profile-1",
                "type": "profile",
                "enabled": True,
                "fields": [
                    _field("title", "Full-stack developer"),
                    _field("summary", "Full-stack developer with professional experience shipping Angular, Laravel, and Ionic features and current projects built with React, TypeScript, FastAPI, Python, and SQL. Wrote unit and integration tests, deployed Dockerized applications through CI/CD, and built coding-agent and RAG workflows."),
                    _field("location", "Halifax, Nova Scotia, Canada; open to relocation"),
                ],
                "entries": [],
            },
            {
                "id": "skills-1",
                "type": "skills",
                "enabled": True,
                "fields": [],
                "entries": [
                    {
                        "id": "skills-languages",
                        "fields": [_field("languages", "Python, TypeScript, JavaScript, PHP, SQL, C#")],
                    },
                    {
                        "id": "skills-tools",
                        "fields": [_field("tools", "Unit Testing, Integration Testing, Git, Docker, GitHub Actions, CI/CD, Linux")],
                    },
                ],
            },
            {
                "id": "experience-1",
                "type": "experience",
                "enabled": True,
                "fields": [],
                "entries": [
                    {
                        "id": "job-1",
                        "fields": [
                            _field("position", "Associate Software Engineer"),
                            _field("start_date", "2022-07"),
                            _field("end_date", "2023-08"),
                            _field("description", "Shipped full-stack web and mobile features with Angular, Laravel, and Ionic. Wrote unit and integration tests across legacy and new codebases. Provisioned Linux environments and deployed Dockerized applications through Git and CI/CD pipelines."),
                        ],
                    },
                    {
                        "id": "job-2",
                        "fields": [
                            _field("position", "Research Assistant"),
                            _field("start_date", "2023-09"),
                            _field("end_date", "2025-10"),
                            _field("description", "Built repository-mining and static-analysis pipelines across open-source repositories. Extended legacy C#/.NET simulation software by diagnosing code-quality issues and implementing product features."),
                        ],
                    },
                ],
            },
            {
                "id": "projects-1",
                "type": "projects",
                "enabled": True,
                "fields": [],
                "entries": [
                    {
                        "id": "project-aergia",
                        "fields": [
                            _field("title", "Aergia CV Builder"),
                            _field("description", "Built a self-hosted CV and application platform with React, FastAPI, SQLAlchemy, SQLite, Playwright, and Docker. Developed requirement-analysis and coding-agent workflows that compose, render, and critique editable CV drafts."),
                        ],
                    },
                    {
                        "id": "project-mbuddy",
                        "fields": [
                            _field("title", "MBuddy"),
                            _field("description", "Built a Python ingestion CLI and created a FastAPI recommendation system backed by PostgreSQL and pgvector. Combined semantic embeddings, metadata signals, and text search in a RAG pipeline."),
                        ],
                    },
                ],
            },
            {
                "id": "education-1",
                "type": "education",
                "enabled": True,
                "fields": [],
                "entries": [
                    {"id": "msc", "fields": [_field("degree", "Master of Computer Science")]},
                    {"id": "bcs", "fields": [_field("degree", "Bachelor of Computer Science and Engineering")]},
                ],
            },
            {
                "id": "disabled-1",
                "type": "experience",
                "enabled": False,
                "fields": [],
                "entries": [{"id": "hidden", "fields": [_field("description", "Monitoring and communication")]}],
            },
        ]
    }


def _requirement(
    requirement_id: str,
    concept_name: str,
    expectation_kind: ExpectationKind,
    *,
    qualifier: str | None = None,
    constraints: list[Any] | None = None,
) -> Requirement:
    source_text = f"{expectation_kind.value} {concept_name}"
    leaf_id = f"{requirement_id}-leaf"
    leaf = RequirementLeaf(
        kind="leaf",
        id=leaf_id,
        concept=Concept(name=concept_name, confidence=0.95),
        expectation=Expectation(kind=expectation_kind, qualifier=qualifier, confidence=0.90),
        constraints=constraints or [],
        confidence=0.95,
    )
    return Requirement(
        id=requirement_id,
        source=RequirementSource(
            original_text=source_text,
            source_start=0,
            source_end=len(source_text),
            extraction_confidence=0.95,
            extractor_version="matcher-test-v1",
        ),
        importance=RequirementImportance.REQUIRED,
        family=RequirementFamily.TECHNICAL_SKILL,
        weight=1.0,
        expression=leaf,
    )


def _walk_leaves(node: Any) -> list[RequirementLeaf]:
    if isinstance(node, RequirementLeaf):
        return [node]
    if isinstance(node, ExamplesExpression):
        return [
            *_walk_leaves(node.subject),
            *[leaf for item in node.examples for leaf in _walk_leaves(item)],
        ]
    return [leaf for child in node.children for leaf in _walk_leaves(child)]


def test_flatten_cv_text_keeps_provenance_and_skips_disabled_sections() -> None:
    fields = flatten_cv_text(_cv_fixture())

    assert any(field.field_path.endswith("fields[description]") and field.entry_id == "project-aergia" for field in fields)
    assert not any(field.entry_id == "hidden" for field in fields)
    assert all(field.text for field in fields)


def test_flatten_cv_text_reads_the_persisted_section_instance_data_shape() -> None:
    cv = {
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "title": "Profile",
                "enabled": True,
                "data": {"name": "Ada Lovelace", "email": "ada@example.com", "summary": "Python developer."},
            },
            {
                "id": "skills",
                "type": "skills",
                "title": "Skills",
                "enabled": True,
                "data": [{"id": "language-skills", "category": "Languages", "items": ["Python", "TypeScript"]}],
            },
            {
                "id": "experience",
                "type": "experience",
                "title": "Experience",
                "enabled": True,
                "data": [{"id": "job", "position": "Python Engineer", "description": "Built Python services.", "start_date": "2023-01"}],
            },
        ]
    }

    fields = flatten_cv_text(cv)

    assert any(field.field_key == "name" and field.text == "Ada Lovelace" for field in fields)
    assert any(field.field_key == "items" and field.text == "Python" for field in fields)
    assert any(field.field_key == "description" and field.entry_id == "job" for field in fields)

    requirement = _requirement("python-familiarity-wire", "Python", ExpectationKind.FAMILIARITY)
    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))
    assert result.requirements[0].status is EvidenceStatus.SUPPORTED


def test_familiarity_is_supported_by_a_cv_skill_field() -> None:
    requirement = _requirement("python-familiarity", "Python", ExpectationKind.FAMILIARITY)

    result = evaluate_semantic_coverage([requirement], _cv_fixture(), as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED
    evidence = result.evidence[0]
    assert evidence.concept_status is EvidenceStatus.SUPPORTED
    assert evidence.expectation_status is EvidenceStatus.SUPPORTED
    assert any(location.section_type == "skills" for item in result.evidence for location in item.locations)


def test_unrelated_skill_and_experience_entries_are_not_joined_as_full_proof() -> None:
    requirement = _requirement("python-prior-experience", "Python", ExpectationKind.PRIOR_EXPERIENCE)
    cv = {
        "sections": [
            {"id": "skills", "type": "skills", "fields": [], "entries": [{"id": "language", "fields": [_field("name", "Python")] }]},
            {"id": "experience", "type": "experience", "fields": [], "entries": [{"id": "job", "fields": [_field("description", "Built Java APIs.")] }]},
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.PARTIAL
    assert result.requirements[0].status is not EvidenceStatus.SUPPORTED


def test_software_engineer_title_cannot_establish_industry_curiosity() -> None:
    requirement = _requirement("industry-curiosity", "software development", ExpectationKind.CURIOSITY)
    cv = {
        "sections": [
            {"id": "experience", "type": "experience", "fields": [], "entries": [{"id": "job", "fields": [_field("position", "Associate Software Engineer")] }]}
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.PARTIAL
    assert result.requirements[0].status is not EvidenceStatus.SUPPORTED
    evidence = result.evidence[0]
    assert evidence.concept_status is EvidenceStatus.SUPPORTED
    assert evidence.expectation_status is EvidenceStatus.NOT_EVIDENCED


def test_developmental_interest_is_supported_by_practical_tool_use() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    requirement = next(
        item
        for item in extraction.requirements
        if item.source.original_text.startswith("Interest in learning development tools")
    )

    assert all(
        leaf.expectation.kind is ExpectationKind.DEVELOPMENTAL_INTEREST
        for leaf in _walk_leaves(requirement.expression)
    )
    result = evaluate_semantic_coverage([requirement], _cv_fixture(), as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED
    assert isinstance(requirement.expression, ExamplesExpression)
    example_leaves = [
        leaf
        for example in requirement.expression.examples
        for leaf in _walk_leaves(example)
    ]
    for leaf in example_leaves:
        leaf_evidence = [item for item in result.evidence if item.id.startswith(f"ev-{leaf.id}-")]
        assert any(item.expectation_status is EvidenceStatus.SUPPORTED for item in leaf_evidence)


def test_interest_in_ai_does_not_satisfy_proactive_day_to_day_application() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    requirement = next(
        item
        for item in extraction.requirements
        if item.source.original_text.startswith("Demonstrated interest in AI tools")
    )

    result = evaluate_semantic_coverage([requirement], _cv_fixture(), as_of=date(2026, 9, 20))
    by_leaf = {leaf.id: leaf for leaf in _walk_leaves(requirement.expression)}
    evidence_by_leaf = {
        leaf_id: [item for item in result.evidence if item.id.startswith(f"ev-{leaf_id}-")]
        for leaf_id in by_leaf
    }

    assert result.requirements[0].status is EvidenceStatus.PARTIAL
    assert len(by_leaf) == 2
    interest_leaf_id = next(
        leaf_id for leaf_id, leaf in by_leaf.items() if leaf.expectation.kind is ExpectationKind.INTEREST
    )
    application_leaf_id = next(
        leaf_id
        for leaf_id, leaf in by_leaf.items()
        if leaf.expectation.kind is ExpectationKind.DEMONSTRATED_APPLICATION
    )
    assert any(
        item.expectation_status is EvidenceStatus.PARTIAL
        for item in evidence_by_leaf[interest_leaf_id]
    )
    assert not any(
        item.expectation_status is EvidenceStatus.SUPPORTED
        for item in evidence_by_leaf[application_leaf_id]
    )


def test_skill_listing_alone_does_not_establish_developmental_interest() -> None:
    requirement = _requirement(
        "docker-learning-interest",
        "Docker",
        ExpectationKind.DEVELOPMENTAL_INTEREST,
    )
    cv = {
        "sections": [
            {"id": "skills", "type": "skills", "fields": [_field("tools", "Docker")], "entries": []}
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.PARTIAL
    assert result.evidence[0].concept_status is EvidenceStatus.SUPPORTED
    assert result.evidence[0].expectation_status is EvidenceStatus.NOT_EVIDENCED


def test_full_stack_practical_experience_supports_developmental_interest() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    requirement = next(
        item
        for item in extraction.requirements
        if item.source.original_text.startswith("Interest in developing yourself")
    )

    result = evaluate_semantic_coverage([requirement], _cv_fixture(), as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED


def test_curiosity_requires_trend_related_evidence() -> None:
    requirement = _requirement("industry-curiosity", "industry trends", ExpectationKind.CURIOSITY)
    cv = {
        "sections": [
            {
                "id": "projects",
                "type": "projects",
                "fields": [],
                "entries": [
                    {
                        "id": "project",
                        "fields": [_field("description", "Followed current industry trends in software through a weekly engineering publication.")],
                    }
                ],
            }
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED


def test_general_action_patterns_support_feature_implementation() -> None:
    requirement = _requirement(
        "feature-implementation",
        "software feature implementation",
        ExpectationKind.ABILITY_TO_PERFORM,
    )
    cv = {
        "sections": [
            {
                "id": "experience",
                "type": "experience",
                "fields": [],
                "entries": [
                    {
                        "id": "job",
                        "fields": [
                            _field("description", "Developed customer-facing features for a scheduling platform.")
                        ],
                    }
                ],
            }
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED
    assert any(item.method is EvidenceMethod.SEMANTIC_RULE for item in result.evidence)


def test_job_title_alone_does_not_establish_familiarity_or_prior_experience() -> None:
    requirement = _requirement("python-experience", "Python", ExpectationKind.PRIOR_EXPERIENCE)
    cv = {
        "sections": [
            {
                "id": "experience",
                "type": "experience",
                "fields": [],
                "entries": [
                    {"id": "python-title", "fields": [_field("position", "Python Developer")]},
                    {"id": "java-work", "fields": [_field("description", "Built Java APIs.")]},
                ],
            }
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.PARTIAL


def test_coding_agent_project_does_not_prove_ai_assisted_coding_predicate() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    compound = next(item for item in extraction.requirements if item.source.original_text.startswith("Learn and apply modern development practices"))
    ai_component = compound.expression.children[0].children[0]
    result = evaluate_semantic_coverage(
        [compound.model_copy(update={"expression": ai_component})],
        _cv_fixture(),
        as_of=date(2026, 9, 20),
    )

    assert result.requirements[0].status is EvidenceStatus.PARTIAL
    assert result.evidence[0].concept_status is EvidenceStatus.SUPPORTED
    assert result.evidence[0].expectation_status is EvidenceStatus.NOT_EVIDENCED


def test_explicit_ai_coding_tool_use_can_support_ai_assisted_development() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    compound = next(item for item in extraction.requirements if item.source.original_text.startswith("Learn and apply modern development practices"))
    ai_component = compound.expression.children[0].children[0]
    cv = {
        "sections": [
            {
                "id": "experience",
                "type": "experience",
                "fields": [],
                "entries": [
                    {"id": "job", "fields": [_field("description", "Used GitHub Copilot to generate code and tests for a FastAPI service.")]}
                ],
            }
        ]
    }

    result = evaluate_semantic_coverage(
        [compound.model_copy(update={"expression": ai_component})],
        cv,
        as_of=date(2026, 9, 20),
    )

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED


def test_alayacare_compound_has_three_supported_components_and_monitoring_missing() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    compound = next(item for item in extraction.requirements if item.source.original_text.startswith("Learn and apply modern development practices"))

    result = evaluate_semantic_coverage([compound], _cv_fixture(), as_of=date(2026, 9, 20))
    evaluation = result.requirements[0]

    assert evaluation.status is EvidenceStatus.PARTIAL
    assert (evaluation.expression.mandatory_supported, evaluation.expression.mandatory_total) == (2, 4)
    assert evaluation.expression.children[0].status is EvidenceStatus.PARTIAL
    assert evaluation.expression.children[-1].status is EvidenceStatus.NOT_EVIDENCED


def test_genai_concept_overlap_does_not_prove_using_it_to_test_code() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    requirement = next(item for item in extraction.requirements if item.source.original_text.startswith("Use GenAI tools"))

    result = evaluate_semantic_coverage([requirement], _cv_fixture(), as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.PARTIAL
    assert result.evidence[0].concept_status is EvidenceStatus.SUPPORTED
    assert result.evidence[0].expectation_status is EvidenceStatus.NOT_EVIDENCED


def test_unit_and_integration_tests_support_automated_testing_semantically() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    extraction = extract_requirements_from_entities(job, {"entities": {}})
    requirement = next(item for item in extraction.requirements if item.source.original_text.startswith("Write and maintain automated tests"))

    result = evaluate_semantic_coverage([requirement], _cv_fixture(), as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.SUPPORTED
    assert any("unit and integration tests" in location.excerpt for evidence in result.evidence for location in evidence.locations)


def test_structured_years_contradiction_is_conflicting_not_missing() -> None:
    constraint = MinimumYearsConstraint(
        id="python-years",
        kind="minimum_years",
        years=3,
        source_text="three years of Python experience",
        confidence=0.95,
    )
    requirement = _requirement(
        "python-three-years",
        "Python",
        ExpectationKind.PRIOR_EXPERIENCE,
        constraints=[constraint],
    )
    cv = {
        "sections": [
            {
                "id": "experience",
                "type": "experience",
                "fields": [],
                "entries": [
                    {
                        "id": "python-job",
                        "fields": [
                            _field("start_date", "2020-01"),
                            _field("end_date", "2022-01"),
                            _field("description", "Developed Python services."),
                        ],
                    }
                ],
            }
        ]
    }

    result = evaluate_semantic_coverage([requirement], cv, as_of=date(2026, 9, 20))

    assert result.requirements[0].status is EvidenceStatus.CONFLICTING
    assert result.evidence[0].constraints[0].status is EvidenceStatus.CONFLICTING
