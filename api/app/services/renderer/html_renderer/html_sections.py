"""Render section headings, local styles, and section contents."""

from __future__ import annotations

from app.document_schema.models import LayoutHints, Section, SectionPolicy, SubsectionStyle, TypographyRole
from .html_entries import (
    _add_entry_metadata,
    _merge_entry_break_before,
    _render_entry,
    _render_skills_inline_entry,
)
from .html_markup import (
    attr,
    format_inline_style as _format_inline_style,
    h,
    style_attr as _style_attr,
)
from app.services.renderer.html_values import (
    FONT_SIZE_VALUES as _FONT_SIZE_TO_CSS,
    safe_color as _safe_color,
    safe_font_family as _safe_font_family,
    safe_spacing as _safe_spacing,
)


def _render_heading(section: Section, policy: SectionPolicy | None) -> str:
    show = policy.show_title if policy else True
    if not show:
        return ""
    color = section.subsection.section_color if section.subsection and section.subsection.section_color else None
    heading = section.typography.heading if section.typography else None
    has_divider = bool(policy and policy.heading_divider)
    # Without a divider we keep 2px below the text; with a divider the
    # ``border-bottom`` + ``padding-bottom`` already provide breathing
    # room, so any margin on top of that pushes the body too far from
    # the title row (a visible ~7px gap on project / research entries).
    base_margin = "0 0 0" if has_divider else "0 0 2px"
    style_parts = [f"margin:{base_margin}", "font-size:1rem", "font-weight:700"]
    if heading:
        style_parts.extend(_typography_role_decls(heading))
    safe_color = _safe_color(heading.color if heading and heading.color else color)
    if safe_color:
        style_parts.append(f"color:{safe_color}")
    if has_divider:
        # Legacy ``underline_section_titles`` flag: border-bottom under
        # the heading, padded so the rule does not crowd the text.
        divider_color = (
            "var(--section-accent,var(--accent,#1f2937))"
            if section.subsection and section.subsection.accent_color
            else "var(--accent,#1f2937)"
        )
        style_parts.append(f"border-bottom:1px solid {divider_color}")
        style_parts.append("padding-bottom:4px")
    return f"<h2{_style_attr(';'.join(style_parts))}>{h(section.title)}</h2>"


def _subsection_style_decl(section: Section) -> str:
    """Inline-style declarations contributed by the section's subsection axis."""

    sub = section.subsection or SubsectionStyle()
    decls: list[str] = []
    if sub.text_align:
        decls.append(f"text-align:{sub.text_align}")
    if sub.spacing_before:
        spacing_before = _safe_spacing(sub.spacing_before)
        if spacing_before:
            decls.append(f"padding-top:{spacing_before}")
    if sub.spacing_after:
        spacing_after = _safe_spacing(sub.spacing_after)
        if spacing_after:
            decls.append(f"margin-bottom:{spacing_after}")
    if sub.background_color:
        background_color = _safe_color(sub.background_color)
        if background_color:
            decls.append(f"background-color:{background_color}")
    if sub.section_color:
        section_color = _safe_color(sub.section_color)
        if section_color:
            decls.append(f"color:{section_color}")
    if sub.accent_color:
        accent_color = _safe_color(sub.accent_color)
        if accent_color:
            decls.append(f"--section-accent:{accent_color}")
            decls.append(f"--accent:{accent_color}")
    return _format_inline_style(decls)


def _typography_role_decls(role: TypographyRole) -> list[str]:
    decls: list[str] = []
    line_heights = {"tight": "1.2", "normal": "1.4", "relaxed": "1.7"}
    if role.font_family:
        family = _safe_font_family(role.font_family)
        if family:
            decls.append(f"font-family:{family}")
    if role.font_size and role.font_size in _FONT_SIZE_TO_CSS:
        decls.append(f"font-size:{_FONT_SIZE_TO_CSS[role.font_size]}")
    if role.line_height:
        decls.append(f"line-height:{line_heights[role.line_height]}")
    if role.color:
        color = _safe_color(role.color)
        if color:
            decls.append(f"color:{color}")
    if role.bold is not None:
        decls.append(f"font-weight:{700 if role.bold else 400}")
    return decls


def _typography_style_decl(section: Section) -> str:
    body = section.typography.body if section.typography else None
    if body is None:
        return ""
    decls = _typography_role_decls(body)
    if body.font_size and body.font_size in _FONT_SIZE_TO_CSS:
        # Field classes have intentional defaults in the document stylesheet.
        # This variable lets a section-level body size replace those defaults
        # without changing the default output for untouched sections.
        decls.append(f"--section-body-size:{_FONT_SIZE_TO_CSS[body.font_size]}")
    if body.color:
        color = _safe_color(body.color)
        if color:
            decls.append(f"--section-body-color:{color}")
    return _format_inline_style(decls)


def _layout_style_decl(section: Section) -> str:
    """Inline-style declarations contributed by the section's layout axis."""

    layout = section.layout or LayoutHints()
    decls: list[str] = []
    if layout.font_family:
        font_family = _safe_font_family(layout.font_family)
        if font_family:
            decls.append(f"font-family:{font_family}")
    if layout.break_before:
        decls.append("break-before:page")
    if layout.orphans:
        decls.append(f"orphans:{layout.orphans}")
    if layout.widows:
        decls.append(f"widows:{layout.widows}")
    return _format_inline_style(decls)


def _heading_keeps_with_first_decl(section: Section) -> str:
    """When ``heading_keeps_with_first`` is set, the first entry needs
    ``break-before: avoid`` to stay glued to the heading."""

    layout = section.layout or LayoutHints()
    if not layout.heading_keeps_with_first:
        return ""
    return "break-before:avoid"


def _keep_entry_together_decl(section: Section) -> str:
    """When ``keep_together`` is set, every entry carries ``break-inside: avoid``
    so the unit of page-flow is the entry — an overflowing entry moves to
    the next page on its own instead of dragging the whole section with it.
    Chromium's ``break-inside: avoid`` is best-effort: a single entry taller
    than a page still splits, which is the intended fallback for very tall
    entries.
    """

    layout = section.layout or LayoutHints()
    if not layout.keep_together:
        return ""
    return "break-inside:avoid"


def _render_section(section: Section) -> str:
    policy = section.policy or SectionPolicy()
    layout = section.layout or LayoutHints()
    sub_decl = _subsection_style_decl(section)
    layout_decl = _layout_style_decl(section)
    keep_first = _heading_keeps_with_first_decl(section)
    keep_entry = _keep_entry_together_decl(section)
    typography_decl = _typography_style_decl(section)
    wrapper_decl_parts = [d for d in (layout_decl, sub_decl, typography_decl) if d]
    # A local "Below" value owns the section's bottom margin. Only add the
    # template section rhythm when the section did not choose one; emitting
    # both declarations lets the later default silently override the user's
    # selection.
    if not section.subsection or not _safe_spacing(section.subsection.spacing_after):
        wrapper_decl_parts.append("margin-bottom:var(--spacing-section, 24px)")
    wrapper_style = _format_inline_style(wrapper_decl_parts)
    body_size_attr = (
        ' data-preview-body-size="true"'
        if section.typography and section.typography.body and section.typography.body.font_size
        else ""
    )
    heading_html = _render_heading(section, policy)

    entries_html_parts: list[str] = []
    # Skills are always rendered as a comma-separated list per category
    # (e.g. ``Programming Languages: TypeScript, JavaScript, Python``).
    # The block variant — each tag as its own flex item — looked tight
    # after the entry-gap fix (gap: 0 collapsed everything flush), and
    # a comma list avoids the gap problem entirely while reading as a
    # single semantic group. The ``skill_variant`` policy is preserved
    # for API compatibility but no longer affects the layout.
    if section.type == "skills":
        for entry in section.entries:
            entry_html = _render_skills_inline_entry(entry)
            entry_html = _add_entry_metadata(entry_html, entry.id, bool(keep_entry))
            if keep_entry:
                entry_html = _merge_entry_break_before(entry_html, keep_entry)
            entries_html_parts.append(entry_html)
    else:
        for i, entry in enumerate(section.entries):
            chip_keys = section.layout.chip_keys if section.layout else None
            entry_html = _render_entry(
                entry,
                section.subsection,
                chip_keys,
                entry_layout=policy.entry_layout,
            )
            entry_html = _add_entry_metadata(entry_html, entry.id, bool(keep_entry))
            if i == 0 and keep_first:
                entry_html = _merge_entry_break_before(entry_html, keep_first)
            if keep_entry:
                entry_html = _merge_entry_break_before(entry_html, keep_entry)
            entries_html_parts.append(entry_html)
    entries_html = "".join(entries_html_parts)
    entry_gap = (
        _safe_spacing(
            (section.subsection.entry_gap if section.subsection and section.subsection.entry_gap else None)
            or "var(--spacing-subsection, 0px)"
        )
        or "0px"
    )
    entries_html = (
        f'<div class="section-entries" style="display:flex;flex-direction:column;gap:{entry_gap}">{entries_html}</div>'
    )

    return (
        f'<section id="{attr(section.id)}"'
        f' data-preview-section="true"'
        f' data-preview-section-id="{attr(section.id)}"'
        f"{body_size_attr}"
        f' data-preview-break-before="{str(bool(layout.break_before)).lower()}"'
        f' data-preview-heading-keeps-with-first="{str(bool(layout.heading_keeps_with_first)).lower()}"'
        f"{_style_attr(wrapper_style)}>"
        f"{heading_html}{entries_html}"
        f"</section>"
    )


__all__ = ["_render_section"]
