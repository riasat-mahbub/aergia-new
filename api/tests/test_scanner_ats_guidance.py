from app.scanner.extraction import extract_requirements_from_entities
from app.scanner.service import ScannerService
from app.scanner.ats_guidance import ATS_RULES, ATS_SOURCES, SUPPORTED_ATS_PLATFORMS


class _FixtureExtractor:
    extractor_version = "fixture-extractor-v1"

    def extract(self, job_description: str):
        return extract_requirements_from_entities(job_description, {"entities": {}})


def _cv(*sections):
    return {"sections": list(sections)}


def _section(section_id, section_type, title, data):
    return {"id": section_id, "type": section_type, "title": title, "enabled": True, "data": data}


def _scan(job, cv):
    return ScannerService(extractor=_FixtureExtractor()).scan(job, cv)


def test_every_scan_generates_all_supported_ats_platforms():
    result = _scan(
        "Qualifications\nExperience with Python.",
        _cv(_section("profile", "profile", "Profile", {"name": "Ada"})),
    )

    assert result.ats_guidance is not None
    assert set(result.ats_guidance.platforms) == {
        "workday", "greenhouse", "lever", "icims", "successfactors",
        "oracle_recruiting", "taleo", "ashby", "smartrecruiters", "bamboohr",
        "rippling", "workable", "jazzhr", "breezy",
    }
    assert result.versions.ats_guidance_version == "ats-guidance-v1"


def test_ats_registry_is_unique_and_source_references_resolve():
    assert len(SUPPORTED_ATS_PLATFORMS) == len(set(SUPPORTED_ATS_PLATFORMS)) == 14
    assert len(ATS_RULES) == len(set(ATS_RULES))
    assert len(ATS_SOURCES) == len(set(ATS_SOURCES))
    for rule in ATS_RULES.values():
        assert set(rule.applies_to).issubset(SUPPORTED_ATS_PLATFORMS)
        assert set(rule.source_ids).issubset(ATS_SOURCES)


def test_heading_convention_uses_semantic_section_type():
    result = _scan(
        "Qualifications\nPython",
        _cv(
            _section("work", "experience", "What I've Done", [{"id": "w1", "position": "Engineer", "company": "Acme"}]),
            _section("education", "education", "Education & Experience", [{"id": "e1", "degree": "MSc", "institution": "Dal"}]),
        ),
    )
    headings = {item.section_id: item for item in result.ats_guidance.heading_conventions}

    assert headings["work"].canonical_section == "experience"
    assert headings["work"].status == "nonstandard"
    assert headings["education"].status == "ambiguous"


def test_rendered_date_compatibility_does_not_flag_safe_renderer_formats():
    result = _scan(
        "Qualifications\nPython",
        _cv(
            _section(
                "work", "experience", "Experience",
                [
                    {"id": "w1", "position": "Engineer", "company": "Acme", "start_date": "2024-01", "current": True},
                    {"id": "w2", "position": "Developer", "company": "Beta", "start_date": "2022-07", "end_date": "2023-08"},
                ],
            ),
            _section(
                "research", "research", "Research",
                [{"id": "r1", "title": "Study", "publication_date": "Spring 2024"}],
            ),
        ),
    )
    dates = {(item.entry_id, item.rendered_text): item.status for item in result.ats_guidance.date_compatibility}

    assert dates[("w1", "January 2024 – Present")] == "conventional"
    assert dates[("w2", "July 2022 – August 2023")] == "conventional"
    assert dates[("r1", "Spring 2024")] == "potentially_ambiguous"


def test_acronym_coverage_requires_explicit_or_curated_pair():
    result = _scan(
        "Qualifications\nProject Management Professional (PMP) required. ABC experience preferred.",
        _cv(_section("profile", "profile", "Profile", {"name": "Ada", "summary": "PMP practitioner"})),
    )
    coverage = {item.acronym: item for item in result.ats_guidance.acronym_coverage}

    assert coverage["PMP"].status == "acronym_only"
    assert "ABC" not in coverage


def test_entry_completeness_reports_missing_structured_fields():
    result = _scan(
        "Qualifications\nPython",
        _cv(
            _section("work", "experience", "Experience", [{"id": "w1", "position": "Engineer"}]),
            _section("edu", "education", "Education", [{"id": "e1", "degree": "MSc"}]),
        ),
    )
    findings = {(item.section_type, item.entry_id): item for item in result.ats_guidance.entry_completeness}

    assert findings[("experience", "w1")].status == "incomplete"
    assert set(findings[("experience", "w1")].missing_fields) == {"employer", "dates"}
    assert findings[("education", "e1")].missing_fields == ["institution"]


def test_entry_completeness_accepts_renderer_field_aliases():
    result = _scan(
        "Qualifications\nPython",
        _cv(
            _section("project", "projects", "Projects", [{"id": "p1", "name": "Aergia"}]),
            _section("edu", "education", "Education", [{"id": "e1", "degree": "MSc", "institution": "Dal"}]),
        ),
    )
    findings = {(item.section_type, item.entry_id): item for item in result.ats_guidance.entry_completeness}

    assert findings[("projects", "p1")].status == "complete"
    assert findings[("education", "e1")].status == "complete"


def test_structural_entry_findings_keep_named_common_rule_ids():
    result = _scan(
        "Qualifications\nPython",
        _cv(
            _section("work", "experience", "Experience", [{"id": "w1", "position": "Engineer"}]),
            _section("edu", "education", "Education", [{"id": "e1", "degree": "MSc"}]),
        ),
    )
    rule_ids = {item.rule_id for item in result.ats_guidance.common_findings}

    assert {"experience_has_employer", "experience_has_dates", "education_has_institution"} <= rule_ids


def test_unsupported_keyword_guidance_does_not_recommend_invention():
    result = _scan(
        "Qualifications\nMonitoring experience required.",
        _cv(_section("profile", "profile", "Profile", {"name": "Ada"})),
    )
    findings = [item for item in result.ats_guidance.common_findings if item.rule_id == "employer_wording_with_evidence"]

    assert findings
    assert all(item.action and "accurate" in item.action for item in findings)
    assert all(item.severity == "info" for item in findings)


def test_illustrative_lexical_examples_are_not_ats_gap_findings():
    result = _scan(
        "Responsibilities\nParticipate in team rituals such as standups, demos, and retrospectives.",
        _cv(_section("profile", "profile", "Profile", {"name": "Ada"})),
    )
    titles = {item.title for item in result.ats_guidance.common_findings}

    assert "Standups" not in titles
    assert "Demos" not in titles
    assert "Retrospectives" not in titles


def test_common_finding_rule_ids_are_registered():
    result = _scan(
        "Qualifications\nProject Management Professional (PMP).",
        _cv(_section("profile", "profile", "Profile", {"name": "Ada"})),
    )

    assert all(item.rule_id in ATS_RULES for item in result.ats_guidance.common_findings)


def test_platform_guidance_contains_only_platform_specific_deltas():
    result = _scan(
        "Qualifications\nPython",
        _cv(_section("profile", "profile", "Profile", {"name": "Ada"})),
    )

    assert result.ats_guidance.common_findings
    assert all(not platform.findings and not platform.tips for platform in result.ats_guidance.platforms.values())
