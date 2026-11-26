"""Focused contracts for native Word layout details."""

from __future__ import annotations

from io import BytesIO

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

from app.document_schema.models import (
    Entry,
    FieldBlock,
    RenderModel,
    RichTextBlock,
    Section,
    SectionPolicy,
    SubsectionStyle,
    TextRun,
    TextStyle,
)
from app.services.renderer.docx import DOCXDocumentRenderer
from app.services.renderer.support import SupportLevel


def _model(section: Section) -> RenderModel:
    return RenderModel(
        zones=[],
        css_vars={},
        body_font="Inter, system-ui, sans-serif",
        heading_font="Inter, system-ui, sans-serif",
        link_styles="",
        print_styles="",
        sections={section.id: section},
    )


def _open_docx(section: Section):
    return Document(BytesIO(DOCXDocumentRenderer().render(_model(section))))


def _paragraph(document, text: str):
    return next(paragraph for paragraph in document.paragraphs if paragraph.text == text)


def _xml_children(element) -> list[str]:
    return [child.tag.rsplit("}", 1)[-1] for child in element]


def _assert_paragraph_properties_are_ordered(paragraph) -> None:
    schema_order = (
        "pStyle",
        "keepNext",
        "keepLines",
        "pageBreakBefore",
        "framePr",
        "widowControl",
        "numPr",
        "suppressLineNumbers",
        "pBdr",
        "shd",
        "tabs",
        "suppressAutoHyphens",
        "kinsoku",
        "wordWrap",
        "overflowPunct",
        "topLinePunct",
        "autoSpaceDE",
        "autoSpaceDN",
        "bidi",
        "adjustRightInd",
        "snapToGrid",
        "spacing",
        "ind",
        "contextualSpacing",
        "mirrorIndents",
        "suppressOverlap",
        "jc",
        "textDirection",
        "textAlignment",
        "textboxTightWrap",
        "outlineLvl",
        "divId",
        "cnfStyle",
        "rPr",
        "sectPr",
        "pPrChange",
    )
    properties = paragraph._p.find(qn("w:pPr"))
    assert properties is not None
    indices = [schema_order.index(name) for name in _xml_children(properties)]
    assert indices == sorted(indices)


def test_docx_maps_section_alignment_shading_and_heading_divider_in_schema_order():
    section = Section(
        id="experience",
        type="experience",
        title="Experience",
        subsection=SubsectionStyle(
            text_align="center",
            background_color="#F1F5F9",
            section_color="#123456",
            accent_color="#C04040",
        ),
        policy=SectionPolicy(show_title=True, heading_divider=True),
        fields=[FieldBlock(key="summary", group="body", runs=[TextRun(text="A centered summary")])],
    )

    document = _open_docx(section)
    heading = _paragraph(document, "Experience")
    body = _paragraph(document, "A centered summary")

    assert heading.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert body.alignment == WD_ALIGN_PARAGRAPH.CENTER
    for paragraph in (heading, body):
        shading = paragraph._p.find(f"{qn('w:pPr')}/{qn('w:shd')}")
        assert shading is not None
        assert shading.get(qn("w:fill")) == "F1F5F9"

    paragraph_properties = heading._p.find(qn("w:pPr"))
    assert paragraph_properties is not None
    _assert_paragraph_properties_are_ordered(heading)
    property_names = _xml_children(paragraph_properties)
    assert property_names.index("pBdr") < property_names.index("shd")
    assert property_names.index("shd") < property_names.index("jc")
    if "spacing" in property_names:
        assert property_names.index("shd") < property_names.index("spacing") < property_names.index("jc")

    borders = paragraph_properties.find(qn("w:pBdr"))
    assert borders is not None
    bottom = borders.find(qn("w:bottom"))
    assert bottom is not None
    assert bottom.get(qn("w:val")) == "single"
    assert bottom.get(qn("w:color")) == "C04040"

    assert DOCXDocumentRenderer.support.feature_section_underline is SupportLevel.FULL


def test_docx_shading_and_numbering_keep_paragraph_properties_in_schema_order():
    section = Section(
        id="process",
        type="extras",
        title="",
        subsection=SubsectionStyle(background_color="#F1F5F9"),
        policy=SectionPolicy(show_title=False),
        fields=[
            FieldBlock(
                key="steps",
                group="body",
                runs=[TextRun(text="First step"), TextRun(text="Second step")],
                blocks=[
                    RichTextBlock(
                        type="numbered_list",
                        items=[{"text": "First step"}, {"text": "Second step"}],
                    ),
                ],
                rich_text=True,
            ),
        ],
    )

    document = _open_docx(section)
    paragraphs = [paragraph for paragraph in document.paragraphs if paragraph.text in {"First step", "Second step"}]

    assert [paragraph.text for paragraph in paragraphs] == ["First step", "Second step"]
    for paragraph in paragraphs:
        _assert_paragraph_properties_are_ordered(paragraph)
        properties = paragraph._p.find(qn("w:pPr"))
        assert properties is not None
        assert properties.find(qn("w:numPr")) is not None
        shading = properties.find(qn("w:shd"))
        assert shading is not None
        assert shading.get(qn("w:fill")) == "F1F5F9"

        number_properties = properties.find(qn("w:numPr"))
        assert _xml_children(number_properties) == ["ilvl", "numId"]


def test_docx_uses_right_tab_for_short_metadata_and_keeps_link_relationship():
    target = "https://projects.example.test/toolkit"
    section = Section(
        id="projects",
        type="projects",
        title="Projects",
        policy=SectionPolicy(show_title=False),
        entries=[
            Entry(
                id="toolkit",
                fields=[
                    FieldBlock(key="project", group="header", runs=[TextRun(text="Open Toolkit")]),
                    FieldBlock(
                        key="link",
                        group="header",
                        align="right",
                        runs=[TextRun(text="Demo", style=TextStyle(link=target))],
                    ),
                ],
            ),
        ],
    )

    document = _open_docx(section)
    row = _paragraph(document, "Open Toolkit\tDemo")
    tab_stops = list(row.paragraph_format.tab_stops)

    assert len(tab_stops) == 1
    assert tab_stops[0].alignment == WD_TAB_ALIGNMENT.RIGHT
    assert tab_stops[0].position.pt == pytest.approx(493.23, abs=0.1)
    assert len(row._p.xpath(".//w:hyperlink")) == 1
    assert any(
        relationship.reltype == RT.HYPERLINK and relationship.target_ref == target
        for relationship in document.part.rels.values()
    )


def test_docx_stacks_competing_long_metadata_in_source_order_and_right_aligns_fallback():
    target = "https://projects.example.test/a-very-long-resource"
    long_title = "Principal Engineer " + "for Global Systems " * 8
    section = Section(
        id="experience",
        type="experience",
        title="Experience",
        subsection=SubsectionStyle(text_align="center"),
        policy=SectionPolicy(show_title=False),
        entries=[
            Entry(
                id="long-entry",
                fields=[
                    FieldBlock(key="position", group="header", runs=[TextRun(text=long_title)]),
                    FieldBlock(
                        key="date",
                        group="header",
                        align="right",
                        runs=[TextRun(text="January 2021 – January 2025", style=TextStyle(link=target))],
                    ),
                    FieldBlock(
                        key="description",
                        group="body",
                        runs=[TextRun(text="Led the migration.")],
                        blocks=[RichTextBlock(type="paragraph", items=[{"text": "Led the migration."}])],
                        rich_text=True,
                    ),
                ],
            ),
        ],
    )

    document = _open_docx(section)
    rendered = document.paragraphs
    title_index = next(i for i, paragraph in enumerate(rendered) if paragraph.text == long_title)
    date_index = next(i for i, paragraph in enumerate(rendered) if paragraph.text == "January 2021 – January 2025")
    description_index = next(i for i, paragraph in enumerate(rendered) if paragraph.text == "Led the migration.")
    date = rendered[date_index]

    assert title_index < date_index < description_index
    assert date.alignment == WD_ALIGN_PARAGRAPH.RIGHT
    assert not list(date.paragraph_format.tab_stops)
    assert len(date._p.xpath(".//w:hyperlink")) == 1
    assert sum(paragraph.text.count("January 2021 – January 2025") for paragraph in rendered) == 1
    assert any(
        relationship.reltype == RT.HYPERLINK and relationship.target_ref == target
        for relationship in document.part.rels.values()
    )


def test_docx_stacks_rich_metadata_without_losing_text_or_links():
    target = "https://credentials.example.test/verified"
    section = Section(
        id="certifications",
        type="certifications",
        title="Certifications",
        subsection=SubsectionStyle(text_align="center"),
        policy=SectionPolicy(show_title=False),
        entries=[
            Entry(
                id="credential",
                fields=[
                    FieldBlock(key="certification", group="header", runs=[TextRun(text="Cloud Architect")]),
                    FieldBlock(
                        key="issuer",
                        group="header",
                        runs=[TextRun(text="Professional certificate")],
                        blocks=[
                            RichTextBlock(type="paragraph", items=[{"text": "Professional certificate"}]),
                        ],
                        rich_text=True,
                    ),
                    FieldBlock(
                        key="link",
                        group="header",
                        align="right",
                        runs=[TextRun(text="Verify", style=TextStyle(link=target))],
                        blocks=[
                            RichTextBlock(
                                type="paragraph",
                                items=[{"text": "Verify", "style": {"link": target}}],
                            ),
                        ],
                        rich_text=True,
                    ),
                ],
            ),
        ],
    )

    document = _open_docx(section)
    metadata = _paragraph(document, "Verify")

    assert [paragraph.text for paragraph in document.paragraphs] == [
        "Cloud Architect",
        "Professional certificate",
        "Verify",
    ]
    assert metadata.alignment == WD_ALIGN_PARAGRAPH.RIGHT
    assert not list(metadata.paragraph_format.tab_stops)
    assert len(metadata._p.xpath(".//w:hyperlink")) == 1
    assert any(
        relationship.reltype == RT.HYPERLINK and relationship.target_ref == target
        for relationship in document.part.rels.values()
    )


def test_docx_keeps_entry_metadata_with_only_the_first_body_paragraph():
    section = Section(
        id="experience",
        type="experience",
        title="Experience",
        policy=SectionPolicy(show_title=False),
        entries=[
            Entry(
                id="entry-one",
                fields=[
                    FieldBlock(key="position", group="header", runs=[TextRun(text="Staff Engineer")]),
                    FieldBlock(key="date", group="header", align="right", runs=[TextRun(text="2020–2025")]),
                    FieldBlock(key="company", group="secondary", runs=[TextRun(text="Acme Systems")]),
                    FieldBlock(
                        key="description",
                        group="body",
                        runs=[TextRun(text="First paragraph"), TextRun(text="Second paragraph")],
                        blocks=[
                            RichTextBlock(type="paragraph", items=[{"text": "First paragraph"}]),
                            RichTextBlock(type="paragraph", items=[{"text": "Second paragraph"}]),
                        ],
                        rich_text=True,
                    ),
                ],
            ),
        ],
    )

    document = _open_docx(section)
    header = _paragraph(document, "Staff Engineer\t2020–2025")
    secondary = _paragraph(document, "Acme Systems")
    first_body = _paragraph(document, "First paragraph")
    second_body = _paragraph(document, "Second paragraph")

    assert header.paragraph_format.keep_with_next is True
    assert secondary.paragraph_format.keep_with_next is True
    assert first_body.paragraph_format.keep_with_next is not True
    assert second_body.paragraph_format.keep_with_next is not True
