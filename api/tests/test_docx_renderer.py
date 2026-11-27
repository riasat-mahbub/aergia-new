"""Focused contracts for the editable Word renderer."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.shared import RGBColor
from docx.text.run import Run

from app.document_schema.models import (
    Entry,
    FieldBlock,
    RenderModel,
    Section,
    SectionPolicy,
    TextRun,
    TextStyle,
)
from app.services.renderer.docx import DOCXDocumentRenderer
from app.services.renderer.pipeline import prepare_render_source, render_source_docx

_PROJECT_URL = f"https://projects.example.test/portfolio?{'q' * 180}=full#published"
_PROFILE_URL = "https://portfolio.example.test/work?source=cv&mode=full#selected"
_FORMATTING_LINK = "https://formatting.example.test/details"


def _minimal_manifest():
    """The seed Minimal values relevant to Word spacing and typography."""

    return {
        "manifest_version": 2,
        "name": "Minimal",
        "zones": [{"id": "main", "styles": {"width": "full", "padding": "spacious"}}],
        "placement": {"profile": "main", "experience": "main", "education": "main"},
        "layout_defaults": {
            "spacing": "minimal",
            "entry_gap": "snug",
            "field_gap": "tight",
        },
        "global_styles": {
            "accent_color": "#111827",
            "body_font": "sans-serif",
            "body_font_size": "small",
            "body_line_height": "normal",
            "heading_font": "sans-serif",
        },
    }


def _formatting_sections(experience_style=None):
    """Stable no-date content for rendered DOCX formatting comparisons."""

    experience = {
        "id": "s-experience",
        "type": "experience",
        "title": "Experience",
        "data": [
            {
                "id": "entry-1",
                "position": "Engineer One",
                "company": "Acme",
                "description": "Entry one body.",
            },
            {
                "id": "entry-2",
                "position": "Engineer Two",
                "company": "Northwind",
                "description": "Entry two body.",
            },
        ],
    }
    if experience_style is not None:
        experience["style"] = experience_style
    return [
        {
            "id": "s-profile",
            "type": "profile",
            "title": "Profile",
            "data": {"name": "Format Candidate"},
        },
        experience,
        {
            "id": "s-education",
            "type": "education",
            "title": "Education",
            "data": [{"id": "school-1", "degree": "BSc", "institution": "Dalhousie"}],
        },
    ]


def _render_formatting_docx(*, manifest=None, customizations=None, experience_style=None):
    source = prepare_render_source(
        _formatting_sections(experience_style),
        manifest if manifest is not None else _minimal_manifest(),
        customizations,
    )
    return _open_docx(render_source_docx(source))


def _style_chain(style):
    while style is not None:
        yield style
        style = style.base_style


def _effective_style_font(style, property_name):
    for current in _style_chain(style):
        value = getattr(current.font, property_name)
        if value is not None:
            return value
    return None


def _effective_style_paragraph_format(style, property_name):
    for current in _style_chain(style):
        value = getattr(current.paragraph_format, property_name)
        if value is not None:
            return value
    return None


def _effective_paragraph_format(paragraph, property_name):
    value = getattr(paragraph.paragraph_format, property_name)
    if value is not None:
        return value
    return _effective_style_paragraph_format(paragraph.style, property_name)


def _effective_run_font(run, property_name):
    value = getattr(run.font, property_name)
    if value is not None:
        return value
    for current in _style_chain(run.style):
        value = getattr(current.font, property_name)
        if value is not None:
            return value
    return _effective_style_font(run._parent.style, property_name)


def _effective_run_flag(run, property_name):
    value = getattr(run, property_name)
    if value is not None:
        return value
    for current in _style_chain(run.style):
        value = getattr(current.font, property_name)
        if value is not None:
            return value
    return _effective_style_font(run._parent.style, property_name)


def _points(value) -> float:
    return value.pt if value is not None else 0.0


def _paragraph_boundary_gap_points(previous, following) -> float:
    """Word uses the greater adjacent before/after spacing at a boundary."""

    return max(
        _points(_effective_paragraph_format(previous, "space_after")),
        _points(_effective_paragraph_format(following, "space_before")),
    )


def _paragraph_with_text(document, text):
    return next(paragraph for paragraph in document.paragraphs if paragraph.text == text)


def _runs_including_hyperlinks(paragraph):
    return [Run(element, paragraph) for element in paragraph._p.xpath(".//w:r")]


def _run_with_text(paragraph, text):
    return next(run for run in _runs_including_hyperlinks(paragraph) if run.text == text)


def _effective_run_color(run):
    for font in [run.font, *(style.font for style in _style_chain(run.style))]:
        if font.color.rgb is not None:
            return font.color.rgb
    for style in _style_chain(run._parent.style):
        if style.font.color.rgb is not None:
            return style.font.color.rgb
    return None


def _fixture_source():
    sections = [
        {
            "id": "s-profile",
            "type": "profile",
            "title": "Profile heading hidden by default",
            "data": {
                "name": "Zoë Ångström",
                "title": "Lead Engineer",
                "email": "zoe@example.test",
                "phone": "",
                "location": "Halifax, NS",
                "site_text": "Portfolio",
                "site_url": _PROFILE_URL,
                "show_urls": True,
                "social_links": [
                    {"label": "GitHub", "url": "https://github.com/zoe#projects", "icon": "github"},
                ],
                "summary": [
                    {
                        "type": "paragraph",
                        "items": [
                            {"text": "Builds ", "style": {"bold": True}},
                            {
                                "text": "reliable\tplatforms\nwith",
                                "style": {"italic": True, "underline": True, "strike": True},
                            },
                            {"text": " care \x00"},
                        ],
                    },
                    {"type": "bullet_list", "items": [{"text": "Owns system design"}, {"text": "Mentors teams"}]},
                    {"type": "numbered_list", "items": [{"text": "First action"}, {"text": "Second action"}]},
                    {"type": "paragraph", "items": [{"text": "Intervening paragraph"}]},
                    {"type": "numbered_list", "items": [{"text": "Restarted action one"}, {"text": "Restarted action two"}]},
                ],
            },
        },
        {
            "id": "s-experience",
            "type": "experience",
            "title": "Experience heading hidden locally",
            "style": {"policy": {"show_title": False}, "layout": {"break_before": True}},
            "data": [
                {
                    "id": "job-1",
                    "position": "Staff Engineer",
                    "company": "Acme Systems",
                    "location": "Halifax",
                    "start_date": "2021-01",
                    "end_date": "2023-01",
                    "description": "Led a platform migration.",
                },
                {
                    "id": "job-2",
                    "position": "Principal Engineer",
                    "company": "Northwind Labs",
                    "start_date": "2021-01",
                    "end_date": None,
                    "current": True,
                    "description": "Improved service reliability.",
                },
            ],
        },
        {
            "id": "s-education",
            "type": "education",
            "title": "Education History",
            "style": {"layout": {"break_before": True}},
            "data": [
                {
                    "id": "school-1",
                    "degree": "BSc Computer Science",
                    "institution": "Dalhousie University",
                    "start_date": "2017-09",
                    "end_date": "2021-01",
                    "gpa": "3.9",
                    "summary": "Graduated with distinction.",
                },
            ],
        },
        {
            "id": "s-skills",
            "type": "skills",
            "title": "Skills heading hidden by template",
            "data": [{"id": "skill-group", "category": "Languages", "items": ["Python", "TypeScript"]}],
        },
        {
            "id": "s-projects",
            "type": "projects",
            "title": "Selected Projects",
            "data": [
                {
                    "id": "project-1",
                    "name": "Open Source Toolkit",
                    "url": _PROJECT_URL,
                    "link_text": "Demo",
                    "start_date": "2021-01",
                    "end_date": "2022-01",
                    "description": "A toolkit for reliable systems.",
                    "tech_stack": ["FastAPI", "PostgreSQL"],
                },
            ],
        },
        {
            "id": "s-research",
            "type": "research",
            "title": "Research",
            "data": [
                {
                    "id": "paper-1",
                    "title": "Resilient Runtime",
                    "publication_date": "2021-01",
                    "publication_value": "Systems Journal",
                    "paper_url": "https://papers.example.test/runtime?format=html#abstract",
                    "paper_link_text": "Read paper",
                    "description": "A study of fault recovery.",
                },
            ],
        },
        {
            "id": "s-certifications",
            "type": "certifications",
            "title": "Certifications",
            "data": [
                {
                    "id": "cert-1",
                    "name": "Cloud Architect",
                    "date": "2021-01",
                    "issuer": "Cloud Guild",
                    "credential_url": "https://credentials.example.test/zoe?level=pro#verify",
                    "link_text": "Verify credential",
                    "description": "Professional certification.",
                },
            ],
        },
        {
            "id": "s-languages",
            "type": "languages",
            "title": "Languages",
            "data": [{"id": "language-1", "language": "French", "proficiency": "Fluent"}],
        },
        {
            "id": "s-extras",
            "type": "extras",
            "title": "Community",
            "data": [
                {
                    "id": "extra-1",
                    "title": "Community Work",
                    "fields": [{"label": "Mentoring", "value": "Mentored early-career engineers"}],
                },
            ],
        },
        {
            "id": "s-disabled",
            "type": "experience",
            "title": "Disabled section must not render",
            "enabled": False,
            "data": [{"id": "disabled-entry", "position": "Disabled role", "company": "Hidden Co"}],
        },
    ]
    manifest = {
        "manifest_version": 2,
        "name": "Two zone template",
        "zones": [
            {"id": "sidebar", "styles": {"width": "narrow"}},
            {"id": "main", "styles": {"width": "full"}},
        ],
        "placement": {"profile": "sidebar", "skills": "sidebar"},
        "policy_overrides": {"by_type": {"skills": {"show_title": False}}},
    }
    customizations = {
        "body_font": "serif",
        "layout": {
            "zones": [{"id": "sidebar"}, {"id": "main"}],
            "placement": {
                "s-profile": "sidebar",
                "s-experience": "main",
                "s-education": "sidebar",
                "s-skills": "main",
                "s-projects": "sidebar",
                "s-research": "main",
                "s-certifications": "sidebar",
                "s-languages": "main",
                "s-extras": "sidebar",
            },
        },
    }
    return prepare_render_source(sections, manifest, customizations)


def _open_docx(data: bytes):
    return Document(BytesIO(data))


def _number_id(paragraph) -> str | None:
    values = paragraph._p.xpath("./w:pPr/w:numPr/w:numId")
    return values[0].get(qn("w:val")) if values else None


def test_docx_minimal_defaults_set_named_style_typography_and_spacing():
    document = _render_formatting_docx()
    normal = document.styles["Normal"]
    title = document.styles["Title"]
    heading = document.styles["Heading 1"]

    assert document.paragraphs[0].text == "Format Candidate"
    assert document.paragraphs[0].style.name == "Title"
    assert _paragraph_with_text(document, "Experience").style.name == "Heading 1"
    assert normal.font.size.pt == pytest.approx(10.5)
    assert _effective_style_paragraph_format(normal, "line_spacing") == pytest.approx(1.4)
    assert normal.font.name == "Inter"
    assert title.font.name == normal.font.name
    assert heading.font.name == normal.font.name

    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(document, "Engineer One"),
        _paragraph_with_text(document, "Acme"),
    ) == pytest.approx(3)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(document, "Acme"),
        _paragraph_with_text(document, "Entry one body."),
    ) == pytest.approx(3)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(document, "Entry one body."),
        _paragraph_with_text(document, "Engineer Two"),
    ) == pytest.approx(6)


def test_docx_spacing_applies_global_and_local_gaps_in_points_including_zero():
    minimal = _render_formatting_docx()
    global_override = _render_formatting_docx(customizations={"spacing": "comfortable"})
    local_override = _render_formatting_docx(
        customizations={"spacing": "compact"},
        experience_style={"subsection": {
            "spacing_before": "comfortable",
            "spacing_after": "spacious",
            "entry_gap": "none",
            "field_gap": "tight",
        }},
    )

    for document in (minimal, global_override, local_override):
        flat_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        assert flat_text.index("Engineer One") < flat_text.index("Acme") < flat_text.index("Entry one body.")
        assert flat_text.index("Entry one body.") < flat_text.index("Engineer Two")
        assert flat_text.index("Engineer Two") < flat_text.index("Northwind") < flat_text.index("Entry two body.")

    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(minimal, "Engineer One"),
        _paragraph_with_text(minimal, "Acme"),
    ) == pytest.approx(3)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(minimal, "Acme"),
        _paragraph_with_text(minimal, "Entry one body."),
    ) == pytest.approx(3)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(minimal, "Entry one body."),
        _paragraph_with_text(minimal, "Engineer Two"),
    ) == pytest.approx(6)

    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(global_override, "Engineer One"),
        _paragraph_with_text(global_override, "Acme"),
    ) == pytest.approx(12)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(global_override, "Acme"),
        _paragraph_with_text(global_override, "Entry one body."),
    ) == pytest.approx(12)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(global_override, "Entry one body."),
        _paragraph_with_text(global_override, "Engineer Two"),
    ) == pytest.approx(12)

    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(local_override, "Engineer One"),
        _paragraph_with_text(local_override, "Acme"),
    ) == pytest.approx(3)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(local_override, "Acme"),
        _paragraph_with_text(local_override, "Entry one body."),
    ) == pytest.approx(3)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(local_override, "Entry one body."),
        _paragraph_with_text(local_override, "Engineer Two"),
    ) == pytest.approx(0)
    # The prior section contributes 15 pt after; this section adds 18 pt before.
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(local_override, "Format Candidate"),
        _paragraph_with_text(local_override, "Experience"),
    ) == pytest.approx(33)
    assert _paragraph_boundary_gap_points(
        _paragraph_with_text(local_override, "Entry two body."),
        _paragraph_with_text(local_override, "Education"),
    ) == pytest.approx(30)


def test_docx_typography_resolves_document_section_and_plain_or_linked_run_overrides():
    global_manifest = _minimal_manifest()
    global_manifest["global_styles"]["body_font_size"] = "normal"
    global_manifest["global_styles"]["body_line_height"] = "relaxed"

    sections = _formatting_sections(experience_style={
        "typography": {
            "heading": {
                "font_family": "sans-serif",
                "font_size": "xl",
                "line_height": "normal",
                "color": "palette.accent",
                "bold": False,
            },
            "body": {
                "font_family": "sans-serif",
                "font_size": "large",
                "line_height": "tight",
                "color": "palette.text-muted",
                "bold": True,
            },
        },
    })
    sections[1]["data"][0]["description"] = [
        {
            "type": "paragraph",
            "items": [
                {"text": "Inherited body."},
                {
                    "text": " Plain override",
                    "style": {"font_size": "xs", "color": "palette.accent", "bold": False},
                },
                {
                    "text": " Linked override",
                    "style": {
                        "link": _FORMATTING_LINK,
                        "font_size": "xs",
                        "color": "palette.text-muted",
                        "bold": False,
                        "underline": False,
                    },
                },
            ],
        },
    ]
    source = prepare_render_source(
        sections,
        global_manifest,
        {"body_font": "serif", "heading_font": "serif"},
    )
    document = _open_docx(render_source_docx(source))

    normal = document.styles["Normal"]
    title = document.styles["Title"]
    heading_style = document.styles["Heading 1"]
    minimal = _render_formatting_docx()
    minimal_normal = minimal.styles["Normal"]

    assert normal.font.name == "Georgia"
    assert normal.font.size.pt == pytest.approx(12)
    assert _effective_style_paragraph_format(normal, "line_spacing") == pytest.approx(1.7)
    assert normal.font.name != minimal_normal.font.name
    assert normal.font.size.pt != minimal_normal.font.size.pt
    assert _effective_style_paragraph_format(normal, "line_spacing") != pytest.approx(
        _effective_style_paragraph_format(minimal_normal, "line_spacing")
    )
    assert title.font.name == "Georgia"
    assert heading_style.font.name == "Georgia"

    heading = _paragraph_with_text(document, "Experience")
    heading_run = _run_with_text(heading, "Experience")
    assert heading.style.name == "Heading 1"
    assert _effective_run_font(heading_run, "name") == "Inter"
    assert _effective_run_font(heading_run, "name") != heading_style.font.name
    assert _effective_run_font(heading_run, "size").pt == pytest.approx(15)
    assert _effective_paragraph_format(heading, "line_spacing") == pytest.approx(1.4)
    assert _effective_run_flag(heading_run, "bold") is False
    assert _effective_run_color(heading_run) == RGBColor(0x25, 0x63, 0xEB)

    body = _paragraph_with_text(document, "Inherited body. Plain override Linked override")
    inherited_run = _run_with_text(body, "Inherited body.")
    plain_run = _run_with_text(body, " Plain override")
    linked_run = _run_with_text(body, " Linked override")
    assert _effective_run_font(inherited_run, "name") == "Inter"
    assert _effective_run_font(inherited_run, "name") != normal.font.name
    assert _effective_run_font(inherited_run, "size").pt == pytest.approx(13.5)
    assert _effective_paragraph_format(body, "line_spacing") == pytest.approx(1.2)
    assert _effective_run_flag(inherited_run, "bold") is True
    assert _effective_run_color(inherited_run) == RGBColor(0x6B, 0x72, 0x80)

    for run, color in (
        (plain_run, RGBColor(0x25, 0x63, 0xEB)),
        (linked_run, RGBColor(0x6B, 0x72, 0x80)),
    ):
        assert _effective_run_font(run, "size").pt == pytest.approx(9)
        assert _effective_run_color(run) == color
        assert _effective_run_flag(run, "bold") is False
    assert _effective_run_flag(linked_run, "underline") is False
    assert any(
        relationship.reltype == RT.HYPERLINK and relationship.target_ref == _FORMATTING_LINK
        for relationship in document.part.rels.values()
    )


def test_docx_is_editable_ordered_and_uses_resolved_section_policy_and_content():
    data = render_source_docx(_fixture_source())
    document = _open_docx(data)
    paragraphs = document.paragraphs
    texts = [paragraph.text for paragraph in paragraphs]

    assert texts[0] == "Zoë Ångström"
    assert paragraphs[0].style.name == "Title"
    assert "Profile heading hidden by default" not in texts
    assert "Experience heading hidden locally" not in texts
    assert "Skills heading hidden by template" not in texts
    assert "Disabled section must not render" not in texts
    assert "Disabled role" not in "\n".join(texts)

    contact = next(text for text in texts if "zoe@example.test" in text)
    assert "Halifax, NS" in contact
    assert "Portfolio — portfolio.example.test/work?source=cv&mode=full#selected" in contact
    assert "GitHub" in contact
    assert "None" not in "\n".join(texts)

    content_order = [
        "Zoë Ångström",
        "Staff Engineer",
        "Education History",
        "Python",
        "Open Source Toolkit",
        "Resilient Runtime",
        "Cloud Architect",
        "French",
        "Community Work",
    ]
    positions = [next(i for i, text in enumerate(texts) if marker in text) for marker in content_order]
    assert positions == sorted(positions)

    experience = next(paragraph for paragraph in paragraphs if "Staff Engineer" in paragraph.text)
    assert experience.paragraph_format.page_break_before is True
    assert "January 2021" in experience.text
    assert sum(paragraph.text.count("January 2021") for paragraph in paragraphs) >= 4

    education_heading = next(paragraph for paragraph in paragraphs if paragraph.text == "Education History")
    assert education_heading.style.name == "Heading 1"
    assert education_heading.paragraph_format.keep_with_next is True
    assert education_heading.paragraph_format.page_break_before is True

    job_markers = [
        "Staff Engineer",
        "Acme Systems",
        "Led a platform migration.",
        "Principal Engineer",
        "Northwind Labs",
        "Improved service reliability.",
    ]
    job_positions = [next(i for i, text in enumerate(texts) if marker in text) for marker in job_markers]
    assert job_positions == sorted(job_positions)

    profile_text = next(paragraph for paragraph in paragraphs if paragraph.text.startswith("Builds "))
    assert profile_text.text == "Builds reliable\tplatforms\nwith care �"
    assert profile_text.runs[0].bold is True
    assert profile_text.runs[1].italic is True
    assert profile_text.runs[1].underline is True
    assert profile_text.runs[1].font.strike is True

    list_paragraphs = {
        paragraph.text: paragraph
        for paragraph in paragraphs
        if paragraph.text in {
            "Owns system design",
            "Mentors teams",
            "First action",
            "Second action",
            "Restarted action one",
            "Restarted action two",
        }
    }
    assert len(list_paragraphs) == 6
    first_numbered_ids = {_number_id(list_paragraphs[text]) for text in ("First action", "Second action")}
    restarted_numbered_ids = {
        _number_id(list_paragraphs[text]) for text in ("Restarted action one", "Restarted action two")
    }
    assert len(first_numbered_ids) == 1
    assert len(restarted_numbered_ids) == 1
    assert first_numbered_ids.isdisjoint(restarted_numbered_ids)
    assert all(_number_id(list_paragraphs[text]) for text in list_paragraphs)

    project_link = next(
        relationship
        for relationship in document.part.rels.values()
        if relationship.reltype == RT.HYPERLINK and relationship.target_ref == _PROJECT_URL
    )
    assert project_link.is_external is True
    assert "Demo" in "\n".join(texts)

    page = document.sections[0]
    assert page.page_width.mm == pytest.approx(210, abs=0.02)
    assert page.page_height.mm == pytest.approx(297, abs=0.02)
    assert page.top_margin.mm == pytest.approx(18, abs=0.02)
    assert page.bottom_margin.mm == pytest.approx(18, abs=0.02)
    assert page.left_margin.mm == pytest.approx(18, abs=0.02)
    assert page.right_margin.mm == pytest.approx(18, abs=0.02)
    assert document.styles["Normal"].font.size.pt == pytest.approx(11)
    assert document.core_properties.author == ""

    with ZipFile(BytesIO(data)) as package:
        xml = package.read("word/document.xml")
    assert b"\x00" not in xml
    assert "�".encode() in xml


def test_docx_numbering_and_boolean_run_properties_are_valid_wordprocessingml():
    data = render_source_docx(_fixture_source())
    document = _open_docx(data)
    numbering = document.part.numbering_part.element
    child_names = [element.tag.rsplit("}", 1)[-1] for element in numbering]
    first_num_index = child_names.index("num")
    assert all(index < first_num_index for index, name in enumerate(child_names) if name == "abstractNum")
    if "numIdMacAtCleanup" in child_names:
        cleanup_index = child_names.index("numIdMacAtCleanup")
        assert all(index < cleanup_index for index, name in enumerate(child_names) if name == "num")

    paragraphs = document.paragraphs
    assert [paragraph.text for paragraph in paragraphs if _number_id(paragraph)] == [
        "Owns system design",
        "Mentors teams",
        "First action",
        "Second action",
        "Restarted action one",
        "Restarted action two",
    ]
    numbered_ids = {
        _number_id(paragraph)
        for paragraph in paragraphs
        if paragraph.text in {"First action", "Second action", "Restarted action one", "Restarted action two"}
    }
    numbered_instances = [
        element
        for element in numbering.findall(qn("w:num"))
        if element.get(qn("w:numId")) in numbered_ids
    ]
    abstract_ids = [instance.find(qn("w:abstractNumId")).get(qn("w:val")) for instance in numbered_instances]
    assert len(abstract_ids) == 2
    assert all(
        abstract.find(f"{qn('w:lvl')}/{qn('w:start')}").get(qn("w:val")) == "1"
        for abstract_id in abstract_ids
        for abstract in numbering.findall(qn("w:abstractNum"))
        if abstract.get(qn("w:abstractNumId")) == abstract_id
    )


def test_docx_rejects_unsafe_link_destination_but_keeps_label_and_valid_xml_flags():
    unsafe_style = TextStyle.model_construct(
        _fields_set={"link", "underline", "strike"},
        link="javascript:alert(1)",
        underline=False,
        strike=False,
    )
    section = Section(
        id="unsafe",
        type="extras",
        title="",
        enabled=True,
        policy=SectionPolicy(show_title=False),
        entries=[
            Entry(
                id="unsafe-entry",
                fields=[FieldBlock(key="label", runs=[TextRun(text="Keep this label", style=unsafe_style)])],
            ),
        ],
    )
    model = RenderModel(
        zones=[],
        css_vars={},
        body_font="Arial",
        heading_font="Arial",
        link_styles="",
        print_styles="",
        sections={"unsafe": section},
    )

    document = _open_docx(DOCXDocumentRenderer().render(model))
    paragraph = next(paragraph for paragraph in document.paragraphs if paragraph.text == "Keep this label")
    assert not paragraph._p.xpath(".//w:hyperlink")
    assert not any(
        relationship.reltype == RT.HYPERLINK and relationship.target_ref.startswith("javascript:")
        for relationship in document.part.rels.values()
    )

    run_properties = paragraph.runs[0]._r.rPr
    assert run_properties.find(qn("w:u")).get(qn("w:val")) == "none"
    assert run_properties.find(qn("w:strike")).get(qn("w:val")) == "0"
