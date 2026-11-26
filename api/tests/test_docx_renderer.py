"""Focused contracts for the editable Word renderer."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

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
