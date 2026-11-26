"""Editable single-column Word renderer for a resolved CV model."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Final

from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from app.core.safe_url import normalize_url
from app.document_schema.models import (
    FieldBlock,
    RenderModel,
    RichTextBlock,
    Section,
    TextStyle,
)
from app.services.renderer.docx_layout import (
    row_can_use_right_aligned_tab,
    set_paragraph_alignment,
    set_paragraph_bottom_border,
    set_paragraph_shading,
    set_right_aligned_tab_stop,
)
from app.services.renderer.html_values import (
    FONT_SIZE_VALUES,
    FONT_TOKEN_VALUES,
    LINE_HEIGHT_TOKEN_VALUES,
    SPACING_VALUES,
    safe_color,
)
from app.services.renderer.support import RendererSupport, SupportLevel

_BODY_FONT: Final = "Arial"
_DEFAULT_SECTION_GAP: Final = "24px"
_CSS_LENGTH = re.compile(r"^(?P<value>(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)(?P<unit>px|rem)$")
_WORD_FONT_FAMILIES: Final[dict[str, str]] = {
    "sans-serif": "Inter",
    "Inter": "Inter",
    "Inter, system-ui, sans-serif": "Inter",
    "display": "Inter",
    "system-ui": _BODY_FONT,
    "system-ui, sans-serif": _BODY_FONT,
    "serif": "Georgia",
    "Georgia": "Georgia",
    "Crimson": "Crimson",
    "Georgia, Crimson, serif": "Georgia",
    "mono": "Consolas",
    "ui-monospace, SFMono-Regular, Menlo, monospace": "Consolas",
}


@dataclass(frozen=True)
class _RunFormatting:
    """Word equivalents of resolved defaults for one section text role."""

    font_name: str | None = None
    font_size_pt: float | None = None
    line_spacing: float | None = None
    color: RGBColor | None = None
    bold: bool | None = None


@dataclass(frozen=True)
class _SectionFormatting:
    body: _RunFormatting
    heading: _RunFormatting
    spacing_before_pt: float
    spacing_after_pt: float
    entry_gap_pt: float
    field_gap_pt: float


def _length_to_points(value: object) -> float | None:
    """Convert known resolver CSS lengths to Word points in one place."""
    if value == "0":
        return 0.0
    if not isinstance(value, str):
        return None
    match = _CSS_LENGTH.fullmatch(value)
    if not match:
        return None
    number = float(match.group("value"))
    return number * (0.75 if match.group("unit") == "px" else 12.0)


def _font_size_points(value: str | None) -> float | None:
    if value is None:
        return None
    return _length_to_points(FONT_SIZE_VALUES.get(value))


def _line_spacing(value: object, fallback: float) -> float:
    allowed = {*LINE_HEIGHT_TOKEN_VALUES.values(), "1", "1.0"}
    if not isinstance(value, str) or value not in allowed:
        return fallback
    return float(value)


def _word_font_family(value: object) -> str | None:
    """Map a closed HTML font token or stack to one Word font family."""
    if not isinstance(value, str):
        return None
    token_value = FONT_TOKEN_VALUES.get(value)
    return _WORD_FONT_FAMILIES.get(token_value or value)


def _word_color(value: object) -> RGBColor | None:
    """Resolve a supported literal or palette color for WordprocessingML."""
    color = safe_color(value)
    if not color:
        return None
    hex_value = color.removeprefix("#")
    if len(hex_value) == 3:
        hex_value = "".join(character * 2 for character in hex_value)
    return RGBColor.from_string(hex_value.upper())


class _FormattingAdapter:
    """Translate the resolved render model's closed CSS values for Word."""

    def __init__(self, model: RenderModel) -> None:
        self.model = model
        self.body_font = _word_font_family(model.body_font) or _BODY_FONT
        self.heading_font = _word_font_family(model.heading_font) or self.body_font
        resolved_body_size = _length_to_points(model.css_vars.get("--body-size"))
        self.body_size_pt = resolved_body_size if resolved_body_size is not None else 11.0
        self.body_line_spacing = _line_spacing(
            model.css_vars.get("--body-line-height"),
            1.0,
        )

    def configure_document(self, document: DocumentObject) -> None:
        """Set Word style defaults while retaining legacy values when absent."""
        normal = document.styles["Normal"]
        normal.font.name = self.body_font
        normal.font.size = Pt(self.body_size_pt)
        normal.paragraph_format.space_after = Pt(2)
        normal.paragraph_format.line_spacing = self.body_line_spacing

        title = document.styles["Title"]
        title.font.name = self.body_font
        title.font.size = Pt(22)
        title.font.bold = True
        title.paragraph_format.space_before = Pt(0)
        title.paragraph_format.space_after = Pt(2)
        title.paragraph_format.line_spacing = self.body_line_spacing

        heading = document.styles["Heading 1"]
        heading.font.name = self.heading_font
        heading.font.size = Pt(14)
        heading.font.bold = True
        heading.paragraph_format.space_before = Pt(10)
        heading.paragraph_format.space_after = Pt(3)
        heading.paragraph_format.line_spacing = self.body_line_spacing
        heading.paragraph_format.keep_with_next = True

    @staticmethod
    def _spacing_points(value: str | None, fallback_pt: float) -> float:
        if value is None:
            return fallback_pt
        css_length = SPACING_VALUES.get(value)
        points = _length_to_points(css_length)
        return points if points is not None else fallback_pt

    def _css_spacing_points(self, name: str, fallback: str) -> float:
        value = self.model.css_vars.get(name, fallback)
        points = _length_to_points(value)
        return points if points is not None else (_length_to_points(fallback) or 0.0)

    def _role_formatting(self, section: Section, *, heading: bool) -> _RunFormatting:
        typography = section.typography
        role = typography.heading if heading and typography else None
        if not heading:
            role = typography.body if typography else None

        if heading:
            font_name = _word_font_family(role.font_family) if role and role.font_family else None
            font_name = font_name or self.heading_font
            section_color = section.subsection.section_color if section.subsection else None
        else:
            layout_font = section.layout.font_family if section.layout else None
            font_name = _word_font_family(role.font_family) if role and role.font_family else None
            font_name = font_name or _word_font_family(layout_font) or self.body_font
            section_color = section.subsection.section_color if section.subsection else None

        color = _word_color(role.color) if role and role.color else None
        color = color or _word_color(section_color)
        return _RunFormatting(
            font_name=font_name,
            font_size_pt=_font_size_points(role.font_size) if role else None,
            line_spacing=(
                _line_spacing(
                    LINE_HEIGHT_TOKEN_VALUES.get(role.line_height),
                    self.body_line_spacing,
                )
                if role and role.line_height
                else None
            ),
            color=color,
            bold=role.bold if role else None,
        )

    def for_section(self, section: Section) -> _SectionFormatting:
        subsection = section.subsection
        section_before = (
            self._spacing_points(subsection.spacing_before, 0.0)
            if subsection and subsection.spacing_before is not None
            else 0.0
        )
        section_after = (
            self._spacing_points(subsection.spacing_after, 0.0)
            if subsection and subsection.spacing_after is not None
            else self._css_spacing_points("--spacing-section", _DEFAULT_SECTION_GAP)
        )
        entry_default = self._css_spacing_points(
            "--spacing-entry",
            self.model.css_vars.get("--spacing-subsection", "0px"),
        )
        field_default = self._css_spacing_points(
            "--spacing-field",
            self.model.css_vars.get("--spacing-subsection", "0px"),
        )
        entry_gap = (
            self._spacing_points(subsection.entry_gap, entry_default)
            if subsection and subsection.entry_gap is not None
            else entry_default
        )
        field_gap = (
            self._spacing_points(subsection.field_gap, field_default)
            if subsection and subsection.field_gap is not None
            else field_default
        )
        return _SectionFormatting(
            body=self._role_formatting(section, heading=False),
            heading=self._role_formatting(section, heading=True),
            spacing_before_pt=section_before,
            spacing_after_pt=section_after,
            entry_gap_pt=entry_gap,
            field_gap_pt=field_gap,
        )


def _apply_paragraph_formatting(paragraph: Paragraph, formatting: _RunFormatting) -> None:
    if formatting.line_spacing is not None:
        paragraph.paragraph_format.line_spacing = formatting.line_spacing


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


def _set_run_properties(
    run: Run,
    style: TextStyle | None,
    default_bold: bool = False,
    formatting: _RunFormatting | None = None,
) -> None:
    """Apply section defaults, then authored inline and semantic emphasis."""

    if formatting is not None:
        if formatting.font_name:
            run.font.name = formatting.font_name
        if formatting.font_size_pt is not None:
            run.font.size = Pt(formatting.font_size_pt)
        if formatting.color is not None:
            run.font.color.rgb = formatting.color
        if formatting.bold is not None:
            run.bold = formatting.bold
    if style is not None:
        if style.font_size is not None:
            size = _font_size_points(style.font_size)
            if size is not None:
                run.font.size = Pt(size)
        if style.color is not None:
            color = _word_color(style.color)
            if color is not None:
                run.font.color.rgb = color

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


def _append_hyperlink_run(
    paragraph: Paragraph,
    text: str,
    href: str,
    style: TextStyle | None,
    default_bold: bool,
    formatting: _RunFormatting | None,
) -> None:
    """Append a linked run using python-docx's relationship and XML APIs."""

    relationship_id = paragraph.part.relate_to(href, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)

    run_element = OxmlElement("w:r")
    run = Run(run_element, paragraph)
    run.style = "Hyperlink"
    run.text = text
    _set_run_properties(run, style, default_bold, formatting)
    hyperlink.append(run_element)
    paragraph._p.append(hyperlink)


def _append_run(
    paragraph: Paragraph,
    text: str,
    style: TextStyle | None = None,
    *,
    default_bold: bool = False,
    formatting: _RunFormatting | None = None,
) -> None:
    """Append a run or a safe hyperlink, retaining a rejected link's label."""

    clean_text = _sanitize_xml_text(text)
    if not clean_text:
        return
    safe_href = normalize_url(style.link) if style and style.link else ""
    if safe_href:
        _append_hyperlink_run(paragraph, clean_text, safe_href, style, default_bold, formatting)
        return
    run = paragraph.add_run()
    run.text = clean_text
    _set_run_properties(run, style, default_bold, formatting)


def _add_numbering_definition(document: DocumentObject, *, numbered: bool) -> int:
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
    number_properties = paragraph_properties.get_or_add_numPr()
    number_properties.get_or_add_ilvl().val = 0
    number_properties.get_or_add_numId().val = num_id


def _field_default_bold(field: FieldBlock) -> bool:
    return field.group == "header" and field.key != "date" and field.key != "link"


def _field_has_text(field: FieldBlock) -> bool:
    if field.blocks:
        return any(item.text != "" for block in field.blocks for item in block.items)
    return any(run.text != "" for run in field.runs)


class _DocumentWriter:
    def __init__(self, document: DocumentObject, formatting: _FormattingAdapter) -> None:
        self.document = document
        self.formatting = formatting
        page = document.sections[0]
        self._usable_width_pt = page.page_width.pt - page.left_margin.pt - page.right_margin.pt
        self._section: Section | None = None
        self._section_background_color: RGBColor | None = None
        self._heading_divider_color: RGBColor | None = None
        self._section_formatting: _SectionFormatting | None = None
        self._body_formatting = _RunFormatting(font_name=formatting.body_font)
        self._heading_formatting = _RunFormatting(font_name=formatting.heading_font)
        self._section_paragraphs: list[Paragraph] = []
        self._previous_section_last: Paragraph | None = None
        self._previous_section_after_pt = 0.0
        self._entry_active = False
        self._entry_has_row = False
        self._entry_row_last: Paragraph | None = None
        self._entry_metadata_paragraphs: list[Paragraph] = []
        self._entry_body_started = False
        self._rendering_rich_field = False
        self._has_content = False
        self._first_paragraph_pending = False
        self._page_break_pending = False

    def _new_paragraph(self, style: str = "Normal") -> Paragraph:
        paragraph = self.document.add_paragraph(style=style)
        defaults = self._heading_formatting if style == "Heading 1" else self._body_formatting
        _apply_paragraph_formatting(paragraph, defaults)
        if self._section is not None:
            subsection = self._section.subsection
            set_paragraph_alignment(
                paragraph,
                subsection.text_align if subsection is not None else None,
            )
            set_paragraph_shading(paragraph, self._section_background_color)
            if style == "Heading 1":
                set_paragraph_bottom_border(paragraph, self._heading_divider_color)
        if self._first_paragraph_pending:
            if self._page_break_pending:
                paragraph.paragraph_format.page_break_before = True
            self._first_paragraph_pending = False
            self._page_break_pending = False
        self._section_paragraphs.append(paragraph)
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
                _append_run(paragraph, item.text, item.style, formatting=self._body_formatting)
            return

        paragraph = self._new_paragraph()
        for item in items:
            _append_run(paragraph, item.text, item.style, formatting=self._body_formatting)

    def _finish_field_row(self, start: int, fields: list[FieldBlock]) -> None:
        """Apply one field gap per logical row and track leading metadata."""

        paragraphs = self._section_paragraphs[start:]
        if not paragraphs or not self._entry_active:
            return

        if self._entry_has_row and self._entry_row_last is not None:
            self._entry_row_last.paragraph_format.space_after = Pt(0)
            paragraphs[0].paragraph_format.space_before = Pt(
                self._section_formatting.field_gap_pt if self._section_formatting else 0
            )
        for previous, following in itertools.pairwise(paragraphs):
            previous.paragraph_format.space_after = Pt(0)
            following.paragraph_format.space_before = Pt(0)

        self._entry_row_last = paragraphs[-1]
        self._entry_has_row = True
        is_metadata = bool(fields) and all(field.group in {"header", "secondary"} for field in fields)
        if self._entry_body_started:
            return
        if is_metadata:
            self._entry_metadata_paragraphs.extend(paragraphs)
            return

        # Keep only leading title/metadata paragraphs with the first body
        # paragraph. Later body paragraphs are left free to flow across pages.
        for metadata_paragraph in self._entry_metadata_paragraphs:
            metadata_paragraph.paragraph_format.keep_with_next = True
        self._entry_metadata_paragraphs.clear()
        self._entry_body_started = True

    def _append_rich_field_paragraphs(self, field: FieldBlock) -> list[Paragraph]:
        start = len(self._section_paragraphs)
        self._rendering_rich_field = True
        try:
            for block in field.blocks or []:
                self._render_rich_block(block)
        finally:
            self._rendering_rich_field = False
        paragraphs = self._section_paragraphs[start:]
        if field.align == "right":
            for paragraph in paragraphs:
                set_paragraph_alignment(paragraph, "right")
        return paragraphs

    def _render_rich_field(self, field: FieldBlock) -> None:
        start = len(self._section_paragraphs)
        self._append_rich_field_paragraphs(field)
        self._finish_field_row(start, [field])

    def _render_field(self, paragraph: Paragraph, field: FieldBlock) -> None:
        bold = _field_default_bold(field)
        if field.blocks:
            return
        for run in field.runs:
            _append_run(
                paragraph,
                run.text,
                run.style,
                default_bold=bold,
                formatting=self._body_formatting,
            )

    def _append_grouped_fields(self, paragraph: Paragraph, fields: list[FieldBlock]) -> None:
        if not fields:
            return
        first = fields[0]
        separator = (
            "  ·  "
            if first.group == "contact"
            else "  |  "
            if first.group in {"header", "secondary"}
            else "  ·  "
        )
        for group_index, grouped_field in enumerate(fields):
            if group_index:
                _append_run(paragraph, separator, formatting=self._body_formatting)
            self._render_field(paragraph, grouped_field)

    def _render_stacked_fields(self, fields: list[FieldBlock]) -> None:
        """Emit fields in source order when a right rail cannot fit a tab."""

        index = 0
        while index < len(fields):
            field = fields[index]
            if field.blocks:
                self._append_rich_field_paragraphs(field)
                index += 1
                continue
            if field.align == "right":
                paragraph = self._new_paragraph()
                set_paragraph_alignment(paragraph, "right")
                self._render_field(paragraph, field)
                index += 1
                continue

            end = index + 1
            while end < len(fields) and fields[end].align != "right":
                end += 1
            paragraph = self._new_paragraph()
            self._append_grouped_fields(paragraph, fields[index:end])
            index = end

    def _render_field_row(self, fields: list[FieldBlock]) -> None:
        start = len(self._section_paragraphs)
        right_fields = [field for field in fields if field.align == "right"]
        if right_fields and row_can_use_right_aligned_tab(
            fields,
            self._usable_width_pt,
            base_font_size_pt=self._body_formatting.font_size_pt or self.formatting.body_size_pt,
            font_family=self._body_formatting.font_name or self.formatting.body_font,
            font_size_resolver=_font_size_points,
        ):
            paragraph = self._new_paragraph()
            self._append_grouped_fields(paragraph, fields[:-1])
            _append_run(paragraph, "\t", formatting=self._body_formatting)
            self._render_field(paragraph, fields[-1])
            set_right_aligned_tab_stop(paragraph, self._usable_width_pt)
        elif right_fields or any(field.blocks for field in fields):
            self._render_stacked_fields(fields)
        else:
            paragraph = self._new_paragraph()
            self._append_grouped_fields(paragraph, fields)

        self._finish_field_row(start, fields)

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

            group_key: tuple[str, str | int] = (
                ("group", field.group) if field.group is not None else ("field", index)
            )
            end = index + 1
            while end < len(fields):
                candidate = fields[end]
                candidate_key: tuple[str, str | int] = (
                    ("group", candidate.group) if candidate.group is not None else ("field", end)
                )
                if (section.type == "profile" and candidate.key == "name") or candidate_key != group_key:
                    break
                end += 1
            grouped_fields = fields[index:end]
            if any(field.align == "right" for field in grouped_fields):
                self._render_field_row(grouped_fields)
                index = end
            elif field.blocks:
                self._render_rich_field(field)
                index += 1
            else:
                simple_end = index + 1
                while simple_end < end and not fields[simple_end].blocks:
                    simple_end += 1
                self._render_field_row(fields[index:simple_end])
                index = simple_end

    def render_section(self, section: Section) -> None:
        if not section.enabled:
            return

        self._section = section
        subsection = section.subsection
        self._section_background_color = (
            _word_color(subsection.background_color)
            if subsection and subsection.background_color
            else None
        )
        has_divider = bool(section.policy and section.policy.heading_divider)
        divider_color = (
            subsection.accent_color
            if subsection and subsection.accent_color
            else self.formatting.model.css_vars.get("--accent")
            or (subsection.section_color if subsection else None)
            or "#1F2937"
        )
        self._heading_divider_color = _word_color(divider_color) if has_divider else None
        self._section_formatting = self.formatting.for_section(section)
        self._body_formatting = self._section_formatting.body
        self._heading_formatting = self._section_formatting.heading
        self._section_paragraphs = []
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
            _append_run(heading, section.title, formatting=self._heading_formatting)
            keep_heading = section.layout is None or section.layout.heading_keeps_with_first
            heading.paragraph_format.keep_with_next = has_section_content and keep_heading

        if section.fields:
            self._render_fields(section, section.fields)
        previous_entry_last: Paragraph | None = None
        for entry in section.entries:
            start = len(self._section_paragraphs)
            self._entry_active = True
            self._entry_has_row = False
            self._entry_row_last = None
            self._entry_metadata_paragraphs = []
            self._entry_body_started = False
            self._render_fields(section, entry.fields)
            for metadata_paragraph in self._entry_metadata_paragraphs[:-1]:
                metadata_paragraph.paragraph_format.keep_with_next = True
            self._entry_metadata_paragraphs.clear()
            self._entry_active = False
            entry_paragraphs = self._section_paragraphs[start:]
            if not entry_paragraphs:
                continue
            if previous_entry_last is not None:
                previous_entry_last.paragraph_format.space_after = Pt(0)
                entry_paragraphs[0].paragraph_format.space_before = Pt(
                    self._section_formatting.entry_gap_pt
                    if self._section_formatting
                    else 0
                )
            previous_entry_last = entry_paragraphs[-1]

        # An empty section has no paragraph to carry its page-break request.
        # Do not leak that request onto the next section's first paragraph.
        if self._first_paragraph_pending:
            self._first_paragraph_pending = False
            self._page_break_pending = False
            return

        section_formatting = self._section_formatting
        if section_formatting is None:
            return
        first_paragraph = self._section_paragraphs[0]
        if self._previous_section_last is not None:
            self._previous_section_last.paragraph_format.space_after = Pt(
                self._previous_section_after_pt + section_formatting.spacing_before_pt
            )
            first_paragraph.paragraph_format.space_before = Pt(0)
        elif section.subsection and section.subsection.spacing_before is not None:
            first_paragraph.paragraph_format.space_before = Pt(section_formatting.spacing_before_pt)

        last_paragraph = self._section_paragraphs[-1]
        last_paragraph.paragraph_format.space_after = Pt(section_formatting.spacing_after_pt)
        self._previous_section_last = last_paragraph
        self._previous_section_after_pt = section_formatting.spacing_after_pt


def _configure_document(document: DocumentObject, formatting: _FormattingAdapter) -> None:
    section = document.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(18)
    section.bottom_margin = Mm(18)
    section.left_margin = Mm(18)
    section.right_margin = Mm(18)

    formatting.configure_document(document)

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
        feature_section_underline=SupportLevel.FULL,
        feature_anchor_styling=SupportLevel.NONE,
    )

    def render(self, model: RenderModel) -> bytes:
        document = Document()
        formatting = _FormattingAdapter(model)
        _configure_document(document, formatting)

        # python-docx's default template can contain an empty starter paragraph.
        # Remove it so the first rendered content starts at the top margin.
        if len(document.paragraphs) == 1 and not document.paragraphs[0].text:
            starter = document.paragraphs[0]._p
            starter.getparent().remove(starter)

        writer = _DocumentWriter(document, formatting)
        # Resolved sections retain source insertion order. Zones only describe
        # placement and must not duplicate or reorder content in this export.
        for section in model.sections.values():
            writer.render_section(section)

        output = BytesIO()
        document.save(output)
        return output.getvalue()


__all__ = ["DOCXDocumentRenderer"]
