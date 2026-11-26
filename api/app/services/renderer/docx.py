"""Editable single-column Word renderer for a resolved CV model."""

from __future__ import annotations

from io import BytesIO
from typing import Final

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from docx.text.run import Run

from app.core.safe_url import normalize_url
from app.document_schema.models import (
    FieldBlock,
    RenderModel,
    RichTextBlock,
    Section,
    TextStyle,
)
from app.services.renderer.support import RendererSupport, SupportLevel

_BODY_FONT: Final = "Arial"


def _sanitize_xml_text(value: str) -> str:
    """Replace XML 1.0-invalid code points while preserving tabs and breaks."""

    def valid(codepoint: int) -> bool:
        return (
            codepoint in (0x09, 0x0A, 0x0D)
            or 0x20 <= codepoint <= 0xD7FF
            or 0xE000 <= codepoint <= 0xFFFD
            or 0x10000 <= codepoint <= 0x10FFFF
        )

    return "".join(char if valid(ord(char)) else "\uFFFD" for char in value)


def _run_bool(style: TextStyle | None, property_name: str, default: bool = False) -> bool:
    """Apply a true style flag, or an explicitly authored false override."""

    if style is None:
        return default
    if property_name in style.model_fields_set:
        return bool(getattr(style, property_name))
    return default or bool(getattr(style, property_name))


def _set_run_properties(run, style: TextStyle | None, default_bold: bool = False) -> None:
    """Set the inline emphasis supported by the fixed Word layout."""

    for property_name, setter in (
        ("bold", lambda value: setattr(run, "bold", value)),
        ("italic", lambda value: setattr(run, "italic", value)),
        ("underline", lambda value: setattr(run, "underline", value)),
        ("strike", lambda value: setattr(run.font, "strike", value)),
    ):
        if style is None:
            if property_name == "bold" and default_bold:
                setter(True)
            continue
        if (
            property_name in style.model_fields_set
            or getattr(style, property_name)
            or (property_name == "bold" and default_bold)
        ):
            setter(_run_bool(style, property_name, default_bold if property_name == "bold" else False))


def _append_hyperlink_run(paragraph, text: str, href: str, style: TextStyle | None, default_bold: bool) -> None:
    """Append a linked run using python-docx's relationship and XML APIs."""

    relationship_id = paragraph.part.relate_to(href, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)

    run_element = OxmlElement("w:r")
    run = Run(run_element, paragraph)
    run.style = "Hyperlink"
    run.text = text
    _set_run_properties(run, style, default_bold)
    hyperlink.append(run_element)
    paragraph._p.append(hyperlink)


def _append_run(paragraph, text: str, style: TextStyle | None = None, *, default_bold: bool = False) -> None:
    """Append a run or a safe hyperlink, retaining a rejected link's label."""

    clean_text = _sanitize_xml_text(text)
    if not clean_text:
        return
    safe_href = normalize_url(style.link) if style and style.link else ""
    if safe_href:
        _append_hyperlink_run(paragraph, clean_text, safe_href, style, default_bold)
        return
    run = paragraph.add_run()
    run.text = clean_text
    _set_run_properties(run, style, default_bold)


def _add_numbering_definition(document, *, numbered: bool) -> int:
    """Add a fresh single-level bullet or numbered-list instance."""

    numbering = document.part.numbering_part.element
    abstract_ids = [int(element.get(qn("w:abstractNumId"))) for element in numbering.findall(qn("w:abstractNum"))]
    abstract_id = max(abstract_ids, default=-1) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi_level_type = OxmlElement("w:multiLevelType")
    multi_level_type.set(qn("w:val"), "singleLevel")
    abstract.append(multi_level_type)

    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    level.append(start)
    number_format = OxmlElement("w:numFmt")
    number_format.set(qn("w:val"), "decimal" if numbered else "bullet")
    level.append(number_format)
    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), "%1." if numbered else "•")
    level.append(level_text)
    justification = OxmlElement("w:lvlJc")
    justification.set(qn("w:val"), "left")
    level.append(justification)

    paragraph_properties = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "720")
    tabs.append(tab)
    paragraph_properties.append(tabs)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "720")
    indent.set(qn("w:hanging"), "360")
    paragraph_properties.append(indent)
    level.append(paragraph_properties)
    abstract.append(level)
    first_num = numbering.find(qn("w:num"))
    cleanup = numbering.find(qn("w:numIdMacAtCleanup"))
    if first_num is not None:
        numbering.insert(numbering.index(first_num), abstract)
    elif cleanup is not None:
        numbering.insert(numbering.index(cleanup), abstract)
    else:
        numbering.append(abstract)

    num_ids = [int(element.get(qn("w:numId"))) for element in numbering.findall(qn("w:num"))]
    num_id = max(num_ids, default=0) + 1
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_num_id = OxmlElement("w:abstractNumId")
    abstract_num_id.set(qn("w:val"), str(abstract_id))
    num.append(abstract_num_id)
    cleanup = numbering.find(qn("w:numIdMacAtCleanup"))
    if cleanup is not None:
        numbering.insert(numbering.index(cleanup), num)
    else:
        numbering.append(num)
    return num_id


def _set_list_number(paragraph, num_id: int) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    number_properties = OxmlElement("w:numPr")
    level = OxmlElement("w:ilvl")
    level.set(qn("w:val"), "0")
    number_id = OxmlElement("w:numId")
    number_id.set(qn("w:val"), str(num_id))
    number_properties.append(level)
    number_properties.append(number_id)
    paragraph_properties.append(number_properties)


def _field_default_bold(field: FieldBlock) -> bool:
    return field.group == "header" and field.key != "date" and field.key != "link"


def _field_has_text(field: FieldBlock) -> bool:
    if field.blocks:
        return any(item.text != "" for block in field.blocks for item in block.items)
    return any(run.text != "" for run in field.runs)


class _DocumentWriter:
    def __init__(self, document):
        self.document = document
        self._has_content = False
        self._first_paragraph_pending = False
        self._page_break_pending = False

    def _new_paragraph(self, style: str = "Normal"):
        paragraph = self.document.add_paragraph(style=style)
        if self._first_paragraph_pending:
            if self._page_break_pending:
                paragraph.paragraph_format.page_break_before = True
            self._first_paragraph_pending = False
            self._page_break_pending = False
        self._has_content = True
        return paragraph

    def _render_rich_block(self, block: RichTextBlock) -> None:
        items = [item for item in block.items if item.text != ""]
        if not items:
            return
        if block.type in {"bullet_list", "numbered_list"}:
            num_id = _add_numbering_definition(self.document, numbered=block.type == "numbered_list")
            for item in items:
                paragraph = self._new_paragraph()
                _set_list_number(paragraph, num_id)
                _append_run(paragraph, item.text, item.style)
            return

        paragraph = self._new_paragraph()
        for item in items:
            _append_run(paragraph, item.text, item.style)

    def _render_field(self, paragraph, field: FieldBlock) -> None:
        bold = _field_default_bold(field)
        if field.blocks:
            return
        for run in field.runs:
            _append_run(paragraph, run.text, run.style, default_bold=bold)

    def _render_fields(self, section: Section, fields: list[FieldBlock]) -> None:
        fields = [field for field in fields if _field_has_text(field)]
        index = 0
        while index < len(fields):
            field = fields[index]
            if section.type == "profile" and field.key == "name":
                name_text = "".join(run.text for run in field.runs)
                if name_text:
                    paragraph = self._new_paragraph("Title")
                    self._render_field(paragraph, field)
                index += 1
                continue

            if field.blocks:
                for block in field.blocks:
                    self._render_rich_block(block)
                index += 1
                continue

            group_key: tuple[str, str | int] = (
                ("group", field.group) if field.group is not None else ("field", index)
            )
            end = index + 1
            while end < len(fields):
                candidate = fields[end]
                candidate_key: tuple[str, str | int] = (
                    ("group", candidate.group) if candidate.group is not None else ("field", end)
                )
                if candidate.blocks or (section.type == "profile" and candidate.key == "name") or candidate_key != group_key:
                    break
                end += 1

            paragraph = self._new_paragraph()
            separator = "  ·  " if field.group == "contact" else "  |  " if field.group in {"header", "secondary"} else "  ·  "
            for group_index, grouped_field in enumerate(fields[index:end]):
                if group_index:
                    paragraph.add_run(separator)
                self._render_field(paragraph, grouped_field)
            index = end

    def render_section(self, section: Section) -> None:
        if not section.enabled:
            return

        self._first_paragraph_pending = True
        self._page_break_pending = bool(
            self._has_content and section.layout and section.layout.break_before
        )

        has_section_content = any(_field_has_text(field) for field in section.fields) or any(
            _field_has_text(field) for entry in section.entries for field in entry.fields
        )
        policy = section.policy
        if section.title and (policy is None or policy.show_title):
            heading = self._new_paragraph("Heading 1")
            heading.add_run(_sanitize_xml_text(section.title))
            keep_heading = section.layout is None or section.layout.heading_keeps_with_first
            heading.paragraph_format.keep_with_next = has_section_content and keep_heading

        if section.fields:
            self._render_fields(section, section.fields)
        for entry in section.entries:
            self._render_fields(section, entry.fields)

        # An empty section has no paragraph to carry its page-break request.
        # Do not leak that request onto the next section's first paragraph.
        if self._first_paragraph_pending:
            self._first_paragraph_pending = False
            self._page_break_pending = False


def _configure_document(document) -> None:
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(18)
    section.bottom_margin = Mm(18)
    section.left_margin = Mm(18)
    section.right_margin = Mm(18)

    normal = document.styles["Normal"]
    normal.font.name = _BODY_FONT
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.0

    title = document.styles["Title"]
    title.font.name = _BODY_FONT
    title.font.size = Pt(22)
    title.font.bold = True
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(2)

    heading = document.styles["Heading 1"]
    heading.font.name = _BODY_FONT
    heading.font.size = Pt(14)
    heading.font.bold = True
    heading.paragraph_format.space_before = Pt(10)
    heading.paragraph_format.space_after = Pt(3)
    heading.paragraph_format.keep_with_next = True

    properties = document.core_properties
    properties.author = ""
    properties.last_modified_by = ""
    properties.title = ""
    properties.subject = ""
    properties.keywords = ""
    properties.comments = ""
    properties.category = ""

    try:
        hyperlink = document.styles["Hyperlink"]
    except KeyError:
        hyperlink = document.styles.add_style("Hyperlink", WD_STYLE_TYPE.CHARACTER)
    hyperlink.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
    hyperlink.font.underline = True


class DOCXDocumentRenderer:
    """Render a resolved model as editable single-column Word paragraphs."""

    support = RendererSupport(
        break_before=SupportLevel.FULL,
        keep_with_next=SupportLevel.FULL,
        keep_together=SupportLevel.NONE,
        heading_keeps_with_first=SupportLevel.FULL,
        keep_entry_together=SupportLevel.NONE,
        feature_skills_inline=SupportLevel.FULL,
        feature_section_underline=SupportLevel.NONE,
        feature_anchor_styling=SupportLevel.NONE,
    )

    def render(self, model: RenderModel) -> bytes:
        document = Document()
        _configure_document(document)

        # python-docx's default template can contain an empty starter paragraph.
        # Remove it so the first rendered content starts at the top margin.
        if len(document.paragraphs) == 1 and not document.paragraphs[0].text:
            starter = document.paragraphs[0]._p
            starter.getparent().remove(starter)

        writer = _DocumentWriter(document)
        # Resolved sections retain source insertion order. Zones only describe
        # placement and must not duplicate or reorder content in this export.
        for section in model.sections.values():
            writer.render_section(section)

        output = BytesIO()
        document.save(output)
        return output.getvalue()


__all__ = ["DOCXDocumentRenderer"]
