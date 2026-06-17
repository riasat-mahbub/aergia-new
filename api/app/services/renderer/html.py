"""HTML renderer — emits a complete HTML5 document from a :class:`RenderModel`.

The renderer is almost stupid: it receives a fully resolved
:class:`RenderModel` and emits HTML. No decision logic. No defaults. No
policy resolution. The Resolver owns those.

The renderer's :class:`RendererSupport` declares the HTML renderer's
capabilities:

- ``break_before`` is ``FULL`` because Chromium honours
  ``break-before: page``.
- ``keep_with_next`` / ``keep_together`` / ``heading_keeps_with_first``
  are ``BEST_EFFORT`` because Chromium honours ``break-inside: avoid``
  and ``break-after: avoid`` only when other constraints allow it.

The renderer emits a ``<!-- best-effort: <feature> -->`` HTML comment for
each ``BEST_EFFORT`` feature it uses, so debugging the live preview and
the PDF is straightforward.

CSS knowledge lives in this module (the renderer is the source of CSS
knowledge — the manifest only carries values).
"""

from __future__ import annotations

import html as _stdlib_html

from app.schema.models import (
    Entry,
    FieldBlock,
    LayoutHints,
    RenderModel,
    ResolvedZone,
    Section,
    SectionPolicy,
    SubsectionStyle,
    TextRun,
    TextStyle,
)
from app.services.renderer.support import RendererSupport, SupportLevel
from app.services.renderer.base import DocumentRenderer


_FONT_SIZE_TO_CSS: dict[str, str] = {
    "xs": "0.75rem",
    "small": "0.875rem",
    "normal": "1rem",
    "large": "1.125rem",
    "xl": "1.25rem",
}


def h(text: object) -> str:
    """HTML-escape a value for use between tags."""

    if text is None:
        return ""
    return _stdlib_html.escape(str(text))


def attr(text: object) -> str:
    """HTML-escape a value for use in a double-quoted attribute."""

    if text is None:
        return ""
    return _stdlib_html.escape(str(text), quote=True)


def _best_effort_comments(model: RenderModel, support: RendererSupport) -> str:
    if support.keep_together is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: keep_together -->"
    if support.keep_with_next is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: keep_with_next -->"
    if support.heading_keeps_with_first is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: heading_keeps_with_first -->"
    if support.break_before is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: break_before -->"


def _render_css_vars(model: RenderModel) -> str:
    if not model.css_vars:
        return ""
    lines = [f"  {k}: {v};" for k, v in model.css_vars.items() if v]
    return ":root {\n" + "\n".join(lines) + "\n}"


def _format_inline_style(decls: list[str]) -> str:
    decls = [d for d in decls if d]
    return ";".join(decls)


def _text_run_to_style(run: TextRun) -> str:
    """Build an inline-style declaration for a single ``TextRun``."""

    decls: list[str] = []
    style = run.style or TextStyle()
    if style.bold:
        decls.append("font-weight:700")
    if style.italic:
        decls.append("font-style:italic")
    if style.underline:
        decls.append("text-decoration:underline")
    if style.strike:
        decls.append("text-decoration:line-through")
        # Underline + strike both set text-decoration; later wins.
    if style.color:
        decls.append(f"color:{style.color}")
    if style.font_size and style.font_size in _FONT_SIZE_TO_CSS:
        decls.append(f"font-size:{_FONT_SIZE_TO_CSS[style.font_size]}")
    return _format_inline_style(decls)


def _render_text_run(run: TextRun) -> str:
    """Render a single text run as ``<span>…</span>`` (or ``<a>`` when linked)."""

    text = h(run.text)
    style = _text_run_to_style(run)
    if run.style and run.style.link:
        href = attr(run.style.link)
        if style:
            return f'<a href="{href}" style="{style}">{text}</a>'
        return f'<a href="{href}">{text}</a>'
    if style:
        return f'<span style="{style}">{text}</span>'
    return text


def _render_field_block(block: FieldBlock) -> str:
    inner = "".join(_render_text_run(r) for r in block.runs)
    return f'<div class="f-{attr(block.key)}">{inner}</div>'


def _render_entry(entry: Entry, section_subsection: SubsectionStyle | None) -> str:
    fields_html = "".join(_render_field_block(f) for f in entry.fields)
    gap = (section_subsection.spacing_after if section_subsection else None) or "var(--spacing-subsection, 16px)"
    return f'<div class="entry" style="display:flex;flex-direction:column;gap:{gap};">{fields_html}</div>'


def _render_heading(section: Section, policy: SectionPolicy | None) -> str:
    show = policy.show_title if policy else True
    if not show:
        return ""
    color = section.subsection.section_color if section.subsection and section.subsection.section_color else None
    style_parts = ["margin:0 0 8px", "font-size:1rem", "font-weight:700"]
    if color:
        style_parts.append(f"color:{color}")
    return f'<h2 style="{";".join(style_parts)};">{h(section.title)}</h2>'


def _subsection_style_decl(section: Section) -> str:
    """Inline-style declarations contributed by the section's subsection axis."""

    sub = section.subsection or SubsectionStyle()
    decls: list[str] = []
    if sub.text_align:
        decls.append(f"text-align:{sub.text_align}")
    if sub.spacing_before:
        decls.append(f"padding-top:{sub.spacing_before}")
    if sub.spacing_after:
        decls.append(f"margin-bottom:{sub.spacing_after}")
    if sub.background_color:
        decls.append(f"background-color:{sub.background_color}")
    if sub.section_color:
        decls.append(f"color:{sub.section_color}")
    return _format_inline_style(decls)


def _layout_style_decl(section: Section) -> str:
    """Inline-style declarations contributed by the section's layout axis."""

    layout = section.layout or LayoutHints()
    decls: list[str] = []
    if layout.font_family:
        decls.append(f"font-family:{layout.font_family}")
    if layout.break_before:
        decls.append("break-before:page")
    if layout.keep_together:
        decls.append("break-inside:avoid")
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


def _render_section(section: Section) -> str:
    policy = section.policy or SectionPolicy()
    sub_decl = _subsection_style_decl(section)
    layout_decl = _layout_style_decl(section)
    keep_first = _heading_keeps_with_first_decl(section)
    wrapper_decl_parts = [d for d in (layout_decl, sub_decl) if d]
    wrapper_decl_parts.append("margin-bottom:var(--spacing-section, 24px)")
    wrapper_style = _format_inline_style(wrapper_decl_parts)
    heading_html = _render_heading(section, policy)

    entries_html_parts: list[str] = []
    for i, entry in enumerate(section.entries):
        entry_html = _render_entry(entry, section.subsection)
        if i == 0 and keep_first:
            # Inject break-before:avoid on the first entry.
            entry_html = entry_html.replace(
                '<div class="entry"',
                f'<div class="entry" style="{keep_first};',
                1,
            )
        entries_html_parts.append(entry_html)
    entries_html = "".join(entries_html_parts)

    return (
        f'<section id="{attr(section.id)}" style="{wrapper_style}">'
        f"{heading_html}{entries_html}"
        f"</section>"
    )


def _render_zone(zone: ResolvedZone, sections_by_id) -> str:
    style_str = _format_inline_style([f"{k}:{v}" for k, v in zone.styles.items() if v])
    panels: list[str] = []
    for section_id in zone.section_ids:
        section = sections_by_id.get(section_id)
        if section is None:
            continue
        panels.append(_render_section(section))
    return f'<div class="zone" style="{style_str}">{"".join(panels)}</div>'


def _render_document(model: RenderModel) -> str:
    best_effort = "\n".join(_best_effort_comments(model, HTMLDocumentRenderer.support))
    css_vars_block = _render_css_vars(model)
    zones_html = "".join(_render_zone(zone, model.sections) for zone in model.zones)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
{css_vars_block}
    body {{
      margin: 0;
      padding: 0;
      font-family: {attr(model.body_font)};
      color: var(--text, #374151);
      background: var(--bg, #ffffff);
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: {attr(model.heading_font)};
    }}
    .f-name {{ font-size: 1.5rem; font-weight: 700; }}
    .f-title, .f-summary, .f-company, .f-description, .f-institution, .f-category {{ font-size: 0.875rem; }}
    .f-contact, .f-contact-sep, .f-email, .f-phone, .f-location, .f-site, .f-social-links, .f-date, .f-gpa, .f-url, .f-tech, .f-tag, .f-proficiency, .f-meta {{ font-size: 0.75rem; }}
    .f-position, .f-degree {{ font-weight: 600; }}
    .f-category {{ font-weight: 600; }}
{model.link_styles}    {model.print_styles}
  </style>
{best_effort}
</head>
<body>
  <div style="display:flex;flex-direction:row;align-items:flex-start;gap:var(--spacing-section, 16px);">
{zones_html}
  </div>
</body>
</html>"""


class HTMLDocumentRenderer(DocumentRenderer):
    """Render a :class:`RenderModel` to a complete HTML5 document."""

    support = RendererSupport()

    def render(self, model: RenderModel) -> str:
        return _render_document(model)

    def render_bytes(self, model: RenderModel) -> bytes:
        return self.render(model).encode("utf-8")


__all__ = ["HTMLDocumentRenderer"]
