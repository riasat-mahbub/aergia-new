"""Parser pipeline end-to-end tests.

Each test builds an :class:`ExtractedDocument` from synthetic ``TextBlock``
data, runs it through ``parse_cv``-style orchestration (extract → classify →
map), and asserts the resulting ``SectionInstance`` shape.

These tests do NOT touch real PDFs. Real-PDF fixtures are added under
``tests/fixtures/sample.pdf`` by the smoke-gate step (Step 19).
"""

from __future__ import annotations

import json

import pytest

from app.services.parser import (
    EmptyInputError,
    ExtractionFailedError,
    ParseResult,
    UnsupportedFormatError,
    parse_cv,
)
from app.services.parser.schemas import ExtractedDocument, ParseMeta, TextBlock
from app.services.parser.classify import classify
from app.services.parser.mapper import map_to_sections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tb(text: str, *, bold: bool = False, size: float = 10.0, page: int = 0, y: float = 0.0) -> TextBlock:
    return TextBlock(
        text=text,
        x=0.0,
        y=y,
        width=400.0,
        height=size,
        font_size=size,
        is_bold=bold,
        page=page,
    )


def _build(parsed: list[TextBlock]) -> ExtractedDocument:
    return ExtractedDocument(
        blocks=parsed,
        plain_text="\n".join(b.text for b in parsed),
        columns=[[]],
        source_format="pdf",
    )


def _run_pipeline(blocks: list[TextBlock]) -> ParseResult:
    """Run classify + map + orchestrator glue without touching extract."""
    extracted = _build(blocks)
    labeled, confs = classify(extracted)
    sections, conf = map_to_sections(labeled, confs)
    return ParseResult(
        sections=sections,
        confidence=conf,
        meta=_meta([s for s in sections if s.type == "extras"]),
    )


def _meta(extra_sections: list) -> ParseMeta:

    warnings = []
    if extra_sections:
        warnings.append("parsed_with_unmapped_content")
    return ParseMeta(source="regex", warnings=warnings)


# ---------------------------------------------------------------------------
# parse_cv entry-point tests
# ---------------------------------------------------------------------------


async def test_parse_cv_rejects_empty_bytes():
    with pytest.raises(EmptyInputError):
        await parse_cv(b"", "application/pdf")


async def test_parse_cv_rejects_unsupported_mime():
    with pytest.raises(UnsupportedFormatError):
        await parse_cv(b"data", "text/plain")


async def test_parse_cv_rejects_corrupt_pdf():
    with pytest.raises(ExtractionFailedError):
        await parse_cv(b"NOT A PDF", "application/pdf")


async def test_parse_cv_json_fastpath_validates_section_instance_list():
    payload = json.dumps(
        [
            {
                "id": "p1",
                "type": "profile",
                "title": "P",
                "enabled": True,
                "data": {
                    "name": "Jane",
                    "title": "",
                    "email": "j@example.com",
                    "phone": "",
                    "location": "",
                    "site_text": "",
                    "site_url": "",
                    "summary": "",
                    "photo_url": "",
                    "social_links": [],
                },
            }
        ]
    ).encode("utf-8")
    result = await parse_cv(payload, "application/json")


async def test_parse_cv_json_fastpath_rejects_non_array():
    bad = json.dumps({"not": "a list"}).encode("utf-8")
    with pytest.raises(Exception):
        await parse_cv(bad, "application/json")


async def test_parse_cv_json_fastpath_rejects_element_with_missing_field():
    bad = json.dumps([{"id": "x"}]).encode("utf-8")
    with pytest.raises(Exception):
        await parse_cv(bad, "application/json")


# ---------------------------------------------------------------------------
# Pipeline-level tests (classify + map)
# ---------------------------------------------------------------------------


def test_pipeline_emits_profile_when_contact_lines_present():
    blocks = [
        _tb("Jane Doe", bold=True, size=18, y=0),
        _tb("jane@example.com", y=1),
        _tb("+1 555 123 4567", y=2),
    ]
    result = _run_pipeline(blocks)
    profile = next((s for s in result.sections if s.type == "profile"), None)
    assert profile is not None
    assert profile.data["name"] == "Jane Doe"
    assert profile.data["email"] == "jane@example.com"
    assert profile.data["phone"] == "+1 555 123 4567"


def test_pipeline_emits_experience_with_title_and_company_split():
    blocks = [
        _tb("EXPERIENCE", bold=True, size=12, y=0),
        _tb("Senior Engineer", y=1),
        _tb("Acme Corp", y=2),
        _tb("Jan 2020 - Dec 2022", y=3),
        _tb("- Built things", y=4),
    ]
    result = _run_pipeline(blocks)
    experience = next((s for s in result.sections if s.type == "experience"), None)
    assert experience is not None
    entries = experience.data
    assert len(entries) == 1
    entry = entries[0]
    assert entry["position"] == "Senior Engineer"
    assert entry["company"] == "Acme Corp"
    assert entry["start_date"] == "2020-01"
    assert entry["end_date"] == "2022-12"
    assert entry["current"] is False
    assert entry["description"] == "Built things"


def test_pipeline_emits_skills_with_split_tokens():
    blocks = [
        _tb("SKILLS", bold=True, size=12, y=0),
        _tb("Python, Go, Rust", y=1),
    ]
    result = _run_pipeline(blocks)
    skills = next((s for s in result.sections if s.type == "skills"), None)
    assert skills is not None
    items = skills.data[0]["items"]
    assert items == ["Python", "Go", "Rust"]


def test_pipeline_emits_extras_for_unmatched_heading():
    blocks = [
        _tb("PROFESSIONAL AFFILIATIONS", bold=True, size=12, y=0),
        _tb("Some prose that doesn't fit anywhere", y=1),
    ]
    result = _run_pipeline(blocks)
    extras = next((s for s in result.sections if s.type == "extras"), None)
    assert extras is not None
    assert extras.data[0]["title"] == "PROFESSIONAL AFFILIATIONS"
    assert "parsed_with_unmapped_content" in [
        w for w in [result.meta.warnings[i] for i in range(len(result.meta.warnings))]
    ]


def test_pipeline_emits_only_non_empty_sections():
    blocks = [
        _tb("EXPERIENCE", bold=True, size=12, y=0),
        _tb("Senior Engineer", y=1),
        _tb("Acme Corp", y=2),
    ]
    result = _run_pipeline(blocks)
    types = [s.type for s in result.sections]
    # No empty stubs for skills/projects/etc.
    assert "skills" not in types
    assert "projects" not in types
    assert "education" not in types


def test_pipeline_drops_extras_when_only_header_line_present():
    """A single bold heading line produces a section with no body — the
    extras builder drops empty entries."""
    blocks = [
        _tb("EXPERIENCE", bold=True, size=12, y=0),
        _tb("Senior Engineer", y=1),
    ]
    result = _run_pipeline(blocks)
    # No extras section: profile has content, experience has content,
    # no extras blocks → no extras instance.
    assert all(s.type != "extras" for s in result.sections)


# ---------------------------------------------------------------------------
# Section-header matching regressions (Task 1: font-based bold inference)
# ---------------------------------------------------------------------------


def test_section_title_single_word_requires_exact_match():
    """Job titles that prefix-match a section name must NOT open a section.

    "Research Assistant" is a role inside an Experience section, not a
    "Research" header. Single-word aliases match exactly; only multi-word
    aliases prefix-match. Without this, the benchmark CV's first
    experience entry (a Research Assistant role) swallowed the whole
    section into a bogus "research" span.
    """
    from app.services.parser.classify import _match_section_title

    assert _match_section_title("Research")[0] == "research"
    assert _match_section_title("Research Assistant")[0] is None
    assert _match_section_title("Skills")[0] == "skills"
    assert _match_section_title("Master of Computer Science")[0] is None


def test_pipeline_keeps_research_assistant_in_experience():
    """The benchmark-shaped layout: Experience header, then a bold
    "Research Assistant" role line — the role stays in experience, no
    research section is invented."""
    blocks = [
        _tb("Jane Doe", bold=True, size=18, y=0),
        _tb("jane@example.com", y=1),
        _tb("Experience", bold=True, size=14, y=2),
        _tb("Research Assistant", bold=True, size=12, y=3),
        _tb("Dalhousie University", y=4),
        _tb("Jan 2020 - Dec 2022", y=5),
    ]
    result = _run_pipeline(blocks)
    types = [s.type for s in result.sections]
    assert "experience" in types
    assert "research" not in types
    exp = next(s for s in result.sections if s.type == "experience")
    assert exp.data[0]["position"] == "Research Assistant"


# ---------------------------------------------------------------------------
# Downstream extractor regressions (Tasks 2-5)
# ---------------------------------------------------------------------------


def test_profile_extracts_bare_domain_as_site_url():
    """Contact lines omit the scheme: 'rmahbub.com' becomes
    https://rmahbub.com. The email host must NOT leak into site_url."""
    blocks = [
        _tb("Jane Doe", bold=True, size=18, y=0),
        _tb("jane@example.com · +1 555 123 4567 · Jane · jane-doe · janedoe.com", y=1),
    ]
    result = _run_pipeline(blocks)
    profile = next(s for s in result.sections if s.type == "profile")
    assert profile.data["email"] == "jane@example.com"
    assert profile.data["phone"] == "+1 555 123 4567"
    assert profile.data["site_url"] == "https://janedoe.com"


def test_profile_does_not_leak_email_host_into_site_url():
    """'example.com' inside jane@example.com is preceded by '@', not
    whitespace/middot, so it must not become the site URL."""
    blocks = [
        _tb("Jane Doe", bold=True, size=18, y=0),
        _tb("jane@example.com", y=1),
    ]
    result = _run_pipeline(blocks)
    profile = next(s for s in result.sections if s.type == "profile")
    assert profile.data["site_url"] == ""


def test_experience_splits_entries_without_blank_lines():
    """Two experience entries joined without blank lines still split on
    the title/company/date pattern."""
    blocks = [
        _tb("EXPERIENCE", bold=True, size=12, y=0),
        _tb("Research Assistant", bold=True, size=11, y=1),
        _tb("Dalhousie University", y=2),
        _tb("September 2023 – October 2025", y=3),
        _tb("Worked with civil engineers on simulation systems.", y=4),
        _tb("Associate Software Engineer", bold=True, size=11, y=5),
        _tb("Brain Station 23", y=6),
        _tb("July 2022 – August 2023", y=7),
        _tb("Delivered features across client projects.", y=8),
    ]
    result = _run_pipeline(blocks)
    exp = next(s for s in result.sections if s.type == "experience")
    entries = exp.data
    assert len(entries) == 2
    assert entries[0]["position"] == "Research Assistant"
    assert entries[0]["company"] == "Dalhousie University"
    assert entries[0]["start_date"] == "2023-09"
    assert entries[0]["end_date"] == "2025-10"
    assert entries[0]["description"] == "Worked with civil engineers on simulation systems."
    assert entries[1]["position"] == "Associate Software Engineer"
    assert entries[1]["company"] == "Brain Station 23"
    assert entries[1]["start_date"] == "2022-07"
    assert entries[1]["description"] == "Delivered features across client projects."


def test_experience_recovers_paragraph_descriptions():
    """Running-paragraph descriptions (no bullets) survive the split."""
    blocks = [
        _tb("EXPERIENCE", bold=True, size=12, y=0),
        _tb("Research Assistant", bold=True, size=11, y=1),
        _tb("Dalhousie University", y=2),
        _tb("September 2023 – October 2025", y=3),
        _tb("Worked with civil engineers and planners.", y=4),
        _tb("Used SonarQube to identify code smells.", y=5),
    ]
    result = _run_pipeline(blocks)
    exp = next(s for s in result.sections if s.type == "experience")
    assert exp.data[0]["description"] == (
        "Worked with civil engineers and planners.\nUsed SonarQube to identify code smells."
    )


def test_education_splits_two_degrees_without_blank_lines():
    """Two degree/institution/date triples joined without blank lines
    each become their own education entry."""
    blocks = [
        _tb("EDUCATION", bold=True, size=12, y=0),
        _tb("Master of Computer Science", bold=True, size=11, y=1),
        _tb("Dalhousie University", y=2),
        _tb("September 2023 – October 2025", y=3),
        _tb("Bachelor of Computer Science and Engineering", bold=True, size=11, y=4),
        _tb("BRAC University", y=5),
        _tb("January 2018 – January 2022", y=6),
    ]
    result = _run_pipeline(blocks)
    edu = next(s for s in result.sections if s.type == "education")
    entries = edu.data
    assert len(entries) == 2
    assert entries[0]["degree"] == "Master of Computer Science"
    assert entries[0]["institution"] == "Dalhousie University"
    assert entries[0]["start_date"] == "2023-09"
    assert entries[1]["degree"] == "Bachelor of Computer Science and Engineering"
    assert entries[1]["institution"] == "BRAC University"
    assert entries[1]["start_date"] == "2018-01"


def test_skills_groups_by_category_prefix():
    """'Category: a, b' lines produce per-category groups; unlabelled
    items without a category still land in a group."""
    blocks = [
        _tb("SKILLS", bold=True, size=12, y=0),
        _tb("Programming Languages: TypeScript, JavaScript, Python", y=1),
        _tb("Frontend: React Js, Angular", y=2),
    ]
    result = _run_pipeline(blocks)
    skills = next(s for s in result.sections if s.type == "skills")
    groups = skills.data
    assert len(groups) == 2
    assert groups[0]["category"] == "Programming Languages"
    assert groups[0]["items"] == ["TypeScript", "JavaScript", "Python"]
    assert groups[1]["category"] == "Frontend"
    assert groups[1]["items"] == ["React Js", "Angular"]


def test_skills_filters_letterspaced_junk():
    """Chromium letter-spaced date labels ('A u g u s t  2 0 2 6')
    never become skill tokens."""
    blocks = [
        _tb("SKILLS", bold=True, size=12, y=0),
        _tb("Python, Go, Rust", y=1),
        _tb("A u g u s t  2 0 2 6", y=2),
    ]
    result = _run_pipeline(blocks)
    skills = next(s for s in result.sections if s.type == "skills")
    items = skills.data[0]["items"]
    assert items == ["Python", "Go", "Rust"]
    assert all("A u g u s t" not in i for i in items)


def test_projects_splits_entries_on_bold_titles():
    """Project titles are bold; each title opens its own entry even when
    the link line ('GitHub ↗') is interleaved."""
    blocks = [
        _tb("PROJECTS", bold=True, size=12, y=0),
        _tb("MBuddy", bold=True, size=11, y=1),
        _tb("A recommendation engine.", y=2),
        _tb("GitHub ↗", y=3),
        _tb("Project Tracker Extension", bold=True, size=11, y=4),
        _tb("A knowledge graph tool.", y=5),
    ]
    result = _run_pipeline(blocks)
    proj = next(s for s in result.sections if s.type == "projects")
    entries = proj.data
    assert len(entries) == 2
    assert entries[0]["title"] == "MBuddy"
    assert entries[1]["title"] == "Project Tracker Extension"
