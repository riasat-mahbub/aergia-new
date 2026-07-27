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
