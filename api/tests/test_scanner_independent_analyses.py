from pathlib import Path
from typing import Any

from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.lexical import analyze_lexical_visibility
from app.scanner.pdf_recovery import (
    MAX_PDF_INPUT_BYTES,
    _run_bounded_pdf_worker,
    analyze_pdf_recovery,
)
from app.scanner.quality import analyze_presentation_quality
from app.scanner.scoring import score_lexical_analysis
from app.scanner.results import (
    BulletEvidenceClass,
    EvidenceStatus,
    LexicalVisibility,
    PDFRecoveryStatus,
)
from app.scanner.service import ScannerService, fingerprint_scan_inputs
from app.services.parser._extract_pdfplumber import extract_with_pdfplumber


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "scanner" / "alayacare"
SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample.pdf"


def _field(key: str, text: str) -> dict[str, Any]:
    return {"key": key, "runs": [{"text": text}]}


def _cv_fixture() -> dict[str, Any]:
    return {
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "enabled": True,
                "fields": [
                    _field("name", "[REDACTED NAME]"),
                    _field("email", "[REDACTED EMAIL]"),
                    _field("phone", "[REDACTED PHONE]"),
                    _field("title", "Full-stack developer"),
                    _field("summary", "Built coding-agent and RAG workflows, and deployed Dockerized applications through CI/CD."),
                ],
                "entries": [],
            },
            {
                "id": "experience",
                "type": "experience",
                "enabled": True,
                "fields": [],
                "entries": [
                    {"id": "job-1", "fields": [_field("position", "Software Engineer"), _field("description", "Built Python APIs and wrote unit and integration tests. Deployed Dockerized applications through Git and CI/CD pipelines.")]},
                    {"id": "job-2", "fields": [_field("position", "Developer"), _field("description", "Reduced query time by 40% using PostgreSQL indexes.")]},
                    {"id": "job-3", "fields": [_field("position", "Intern"), _field("description", "Created a testing plan for a new service.")]},
                    {"id": "job-4", "fields": [_field("position", "Assistant"), _field("description", "Responsible for support tickets.")]},
                ],
            },
        ]
    }


def test_lexical_inventory_does_not_promote_semantic_aliases() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    cv = _cv_fixture()

    result = analyze_lexical_visibility(job, cv)
    terms = {term.term.casefold(): term for term in result.terms}

    assert terms["python"].visibility is LexicalVisibility.EXACT
    assert terms["genai"].visibility is LexicalVisibility.ABSENT
    assert terms["automated testing"].visibility is LexicalVisibility.ABSENT
    assert terms["containerization"].visibility is LexicalVisibility.ABSENT
    assert terms["monitoring"].visibility is LexicalVisibility.ABSENT
    assert terms["ci/cd"].visibility is LexicalVisibility.EXACT
    assert "coding agent" not in terms["genai"].variants
    assert "unit tests" not in terms["automated testing"].variants
    assert "docker" not in terms["containerization"].variants
    assert terms["ai tools"].source_locations
    hiring_start = job.index("AlayaCare uses AI tools during our hiring process")
    assert all(location.source_start < hiring_start for location in terms["ai tools"].source_locations)


def test_lexical_variants_are_surface_forms_not_semantic_equivalents() -> None:
    result = analyze_lexical_visibility(
        "Qualifications\nGenAI, containerization, automated testing, and Front-End.\n",
        {
            "sections": [
                {
                    "id": "profile",
                    "type": "profile",
                    "fields": [_field("summary", "Generative AI, Docker, unit and integration tests, frontend development.")],
                    "entries": [],
                }
            ]
        },
    )
    terms = {term.term.casefold(): term for term in result.terms}

    assert terms["genai"].visibility is LexicalVisibility.VARIANT
    assert terms["genai"].evidence[0].matched_text == "Generative AI"
    assert terms["front-end development"].visibility is LexicalVisibility.VARIANT
    assert terms["containerization"].visibility is LexicalVisibility.ABSENT
    assert terms["automated testing"].visibility is LexicalVisibility.ABSENT


def test_illustrative_examples_remain_visible_but_do_not_lower_term_visibility() -> None:
    job = "What You’ll Do\nParticipate in team rituals such as standups, demos, and retrospectives.\n"
    extraction = extract_requirements_from_entities(job, {"entities": {}})

    result = analyze_lexical_visibility(job, {"sections": []}, requirements=extraction.requirements)
    terms = {term.term.casefold(): term for term in result.terms}
    summary = score_lexical_analysis(result)

    assert terms["team rituals"].visibility is LexicalVisibility.ABSENT
    assert terms["team rituals"].illustrative_example is False
    for example in ("standups", "demos", "retrospectives"):
        assert terms[example].visibility is LexicalVisibility.ABSENT
        assert terms[example].illustrative_example is True
    assert summary.absent_count == 1
    assert summary.scorable_fraction == 1.0
    assert summary.visibility_score == 0.0


def test_exhaustive_lists_and_explicit_any_alternatives_remain_scored_terms() -> None:
    exhaustive_job = "Qualifications\nMust know Python, JavaScript, and SQL.\n"
    exhaustive = extract_requirements_from_entities(exhaustive_job, {"entities": {}})
    exhaustive_lexical = analyze_lexical_visibility(
        exhaustive_job,
        {"sections": []},
        requirements=exhaustive.requirements,
    )
    exhaustive_terms = {term.term.casefold(): term for term in exhaustive_lexical.terms}
    for term in ("python", "javascript", "sql"):
        assert exhaustive_terms[term].illustrative_example is False
        assert exhaustive_terms[term].visibility is LexicalVisibility.ABSENT
    assert score_lexical_analysis(exhaustive_lexical).absent_count == 3

    any_job = "Qualifications\nFamiliarity with at least one of Python, Java, or C#.\n"
    any_extraction = extract_requirements_from_entities(any_job, {"entities": {}})
    any_lexical = analyze_lexical_visibility(any_job, {"sections": []}, requirements=any_extraction.requirements)
    any_terms = {term.term.casefold(): term for term in any_lexical.terms}
    for term in ("python", "java", "c#"):
        assert any_terms[term].illustrative_example is False
    assert score_lexical_analysis(any_lexical).absent_count == 3


def test_required_occurrence_of_an_example_term_keeps_it_in_the_score() -> None:
    job = "Qualifications\nAWS experience is required. Cloud platforms such as AWS and Azure are useful.\n"
    example_sentence = "Cloud platforms such as AWS and Azure are useful."
    example_start = job.index(example_sentence)
    extraction = extract_requirements_from_entities(
        job,
        {
            "entities": {
                "candidate_requirement": [
                    {
                        "text": example_sentence,
                        "start": example_start,
                        "end": example_start + len(example_sentence),
                        "confidence": 0.95,
                    }
                ]
            }
        },
    )

    result = analyze_lexical_visibility(job, {"sections": []}, requirements=extraction.requirements)
    aws = next(term for term in result.terms if term.term.casefold() == "aws")

    assert len(aws.source_locations) == 2
    assert sorted(location.illustrative_example for location in aws.source_locations) == [False, True]
    assert aws.illustrative_example is False
    assert score_lexical_analysis(result).absent_count == sum(
        not term.illustrative_example for term in result.terms
    )


def test_presentation_classifies_bullets_without_requiring_metrics() -> None:
    result = analyze_presentation_quality(_cv_fixture())

    assert [item.classification for item in result.bullet_assessments] == [
        BulletEvidenceClass.ACTION_WITH_TECHNICAL_SPECIFICITY,
        BulletEvidenceClass.ACTION_WITH_QUANTIFIED_OUTCOME,
        BulletEvidenceClass.ACTION_ONLY,
        BulletEvidenceClass.RESPONSIBILITY_ONLY,
    ]
    assert not any(finding.code == "missing_contact" for finding in result.findings)
    assert sum(item.classification is BulletEvidenceClass.ACTION_WITH_QUANTIFIED_OUTCOME for item in result.bullet_assessments) == 1


def test_presentation_analyzes_persisted_section_instance_data() -> None:
    cv = {
        "sections": [
            {"id": "profile", "type": "profile", "title": "Profile", "data": {"name": "Ada", "email": "ada@example.com"}},
            {
                "id": "experience",
                "type": "experience",
                "title": "Experience",
                "data": [{"id": "job", "position": "Developer", "description": "Built Python APIs."}],
            },
        ]
    }

    result = analyze_presentation_quality(cv)

    assert not any(finding.code == "missing_name" for finding in result.findings)
    assert not any(finding.code == "missing_contact" for finding in result.findings)
    assert result.bullet_assessments[0].classification is BulletEvidenceClass.ACTION_WITH_TECHNICAL_SPECIFICITY


def test_alayacare_project_bullets_detect_actions_and_technical_specificity() -> None:
    bullets = [
        "Developed requirement-analysis and coding-agent workflows that compose, render, and critique editable CV drafts while keeping the user in control of final approval.",
        "Kept the React editor and Python document renderer on one validated model so live previews and exported PDFs remain consistent.",
        "Combined semantic embeddings, metadata signals, and text search in a RAG pipeline for context-aware recommendations.",
    ]
    cv = {
        "sections": [
            {
                "id": "profile",
                "type": "profile",
                "fields": [_field("name", "Ada Example"), _field("email", "ada@example.com")],
                "entries": [],
            },
            {
                "id": "projects",
                "type": "projects",
                "fields": [],
                "entries": [
                    {"id": f"project-{index}", "fields": [_field("description", bullet)]}
                    for index, bullet in enumerate(bullets)
                ],
            },
        ]
    }

    result = analyze_presentation_quality(cv)

    assert [item.classification for item in result.bullet_assessments] == [
        BulletEvidenceClass.ACTION_WITH_TECHNICAL_SPECIFICITY,
        BulletEvidenceClass.ACTION_WITH_TECHNICAL_SPECIFICITY,
        BulletEvidenceClass.ACTION_WITH_TECHNICAL_SPECIFICITY,
    ]


def test_pdf_recovery_is_explicitly_unavailable_without_a_pdf_and_size_bounded() -> None:
    cv = _cv_fixture()

    missing = analyze_pdf_recovery(None, cv)
    oversized = analyze_pdf_recovery(b"x" * (MAX_PDF_INPUT_BYTES + 1), cv)

    assert missing.status is PDFRecoveryStatus.UNAVAILABLE
    assert oversized.status is PDFRecoveryStatus.WARNING
    assert oversized.checks[0].code == "input_size_limit"


def test_pdf_worker_recovers_text_from_existing_sample_pdf() -> None:
    extracted = _run_bounded_pdf_worker(SAMPLE_PDF.read_bytes())

    assert "error" not in extracted
    assert extracted["page_count"] == 1
    assert "Jane Doe" in extracted["plain_text"]
    assert extracted["page_limit_exceeded"] is False
    assert extracted["text_truncated"] is False


def test_pdf_parser_applies_text_limit_while_building_extracted_document() -> None:
    extracted = extract_with_pdfplumber(SAMPLE_PDF.read_bytes(), max_text_chars=12)

    assert len(extracted.plain_text) <= 12
    assert extracted.text_truncated is True
    assert extracted.page_count == 1


class _FixtureExtractor:
    def extract(self, job_description: str):
        return extract_requirements_from_entities(job_description, {"entities": {}})


def test_scanner_service_keeps_four_independent_branches_and_versions_them() -> None:
    job = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    result = ScannerService(extractor=_FixtureExtractor()).scan(job, _cv_fixture())

    assert result.schema_version == "scanner-v1"
    assert result.requirement_extraction.requirements
    assert result.semantic.status.value == "evaluated"
    assert result.lexical.status.value == "evaluated"
    assert result.presentation_quality.status.value == "evaluated"
    assert result.pdf_recovery.status is PDFRecoveryStatus.UNAVAILABLE
    assert result.versions.extractor_version == "gliner2.5-structured-v7"
    assert result.versions.matcher_version == "requirement-match-v4"
    assert result.versions.lexical_version == "ats-lexical-v5"
    assert result.versions.quality_version == "resume-presentation-v2"
    assert result.versions.semantic_score_version == "job-fit-v2"
    assert result.versions.lexical_score_version == "term-visibility-v2"
    assert result.versions.pdf_score_version == "pdf-recovery-score-v1"
    assert result.semantic.summary is not None
    assert result.lexical.summary is not None
    assert result.pdf_recovery.summary is not None
    assert result.pdf_recovery.summary.recovery_score is None
    terms = {term.term.casefold(): term for term in result.lexical.terms}
    assert terms["genai"].visibility is LexicalVisibility.ABSENT
    assert terms["genai"].semantic_support is EvidenceStatus.PARTIAL
    assert terms["automated testing"].visibility is LexicalVisibility.ABSENT
    assert terms["automated testing"].semantic_support is EvidenceStatus.SUPPORTED
    assert terms["containerization"].visibility is LexicalVisibility.ABSENT
    assert terms["containerization"].semantic_support is EvidenceStatus.SUPPORTED
    assert terms["monitoring"].visibility is LexicalVisibility.ABSENT
    assert terms["monitoring"].semantic_support is EvidenceStatus.NOT_EVIDENCED
    assert len(result.input_fingerprints.cv_content_sha256) == 64


def test_scanner_can_evaluate_against_frozen_extraction_without_reextracting() -> None:
    job = "Qualifications\nPython experience."
    extraction = extract_requirements_from_entities(job, {"entities": {}})

    class _ExplodingExtractor:
        def extract(self, _job: str):
            raise AssertionError("frozen evaluation must not invoke the extractor")

    result = ScannerService(extractor=_ExplodingExtractor()).scan_with_extraction(
        job,
        _cv_fixture(),
        extraction,
    )

    assert result.requirement_extraction == extraction


def test_scanner_cv_fingerprint_ignores_identity_and_lifecycle_metadata() -> None:
    document = {
        "sections": _cv_fixture()["sections"],
        "template_id": "minimal",
        "customizations": {"accent_color": "#123456"},
    }
    orm_like = {
        **document,
        "id": "cv-1",
        "title": "Draft",
        "description": "ignored",
        "revision": 7,
        "is_active": True,
    }

    assert fingerprint_scan_inputs("Build APIs", document).cv_content_sha256 == fingerprint_scan_inputs(
        "Build APIs", orm_like
    ).cv_content_sha256
