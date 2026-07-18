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


# Social icon table: name -> inline SVG markup (16x16, currentColor).
# Generic glyphs are hand-drawn; brand marks (github) copy the lucide path
# (https://lucide.dev/icon/github, ISC license) at implementation time.
_SOCIAL_ICONS: dict[str, str] = {
    "x": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 4l16 16M20 4L4 20"/></svg>',
    "twitter": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 4l16 16M20 4L4 20"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3.5" y="3.5" width="17" height="17" rx="4.5"/><circle cx="12" cy="12" r="3.8"/><circle cx="17.2" cy="6.8" r="1.15" fill="currentColor" stroke="none"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3.5" y="3.5" width="17" height="17" rx="2"/><path d="M8.2 10v6.5M8.2 6.9v.2M11.8 16.5v-4.4a2.6 2.6 0 0 1 5.2 0v4.4"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13.4 21v-6.8h2.3l.45-2.9H13.4V9.4c0-.85.3-1.6 1.7-1.6h1.15V5.1c-.55-.08-1.6-.2-2.55-.2-2.55 0-4.2 1.55-4.2 4.4v2.05H7.2v2.9h2.3V21"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="6.2" width="18" height="11.6" rx="3.2"/><path d="M10.1 9.6l4.6 2.4-4.6 2.4z" fill="currentColor" stroke="none"/></svg>',
    "github": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>',
    "globe": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3.6 9h16.8M3.6 15h16.8M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25H4.5a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5H4.5a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 0 0 2.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 0 1-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 0 0-1.091-.852H4.5A2.25 2.25 0 0 0 2.25 4.5v2.25Z"/></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"/></svg>',
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


def _render_field_block(block: FieldBlock, extra_style: str | None = None) -> str:
    inner = "".join(_render_text_run(r) for r in block.runs)
    icon_svg = _SOCIAL_ICONS.get(block.icon) if block.icon else None
    if icon_svg:
        icon_html = f'<span class="f-icon" aria-hidden="true">{icon_svg}</span>'
        inner = f'{icon_html}<span class="f-icon-label">{inner}</span>'
    style = f' style="{extra_style}"' if extra_style else ""
    return f'<div class="f-{attr(block.key)}"{style}>{inner}</div>'


def _resolve_row_justify(subsection: SubsectionStyle | None) -> str:
    """Map a section's ``text_align`` to the flex ``justify-content`` value
    used for its field rows. ``None``/``"left"`` keep the default
    ``flex-start``; the renderer never emits an explicit left."""

    align = subsection.text_align if subsection else None
    if align == "center":
        return "center"
    if align == "right":
        return "right"
    return "flex-start"


def _render_entry(entry: Entry, section_subsection: SubsectionStyle | None) -> str:
    gap = (section_subsection.spacing_after if section_subsection else None) or "var(--spacing-subsection, 16px)"
    justify = _resolve_row_justify(section_subsection)

    # Group consecutive fields that share a group name into one row.
    rows: list[str] = []
    current_group: str | None = None
    bucket: list[FieldBlock] = []
    for field in entry.fields:
        if bucket and (field.group is None or field.group != current_group):
            rows.append(_render_field_row(bucket, justify))
            bucket = []
        current_group = field.group
        bucket.append(field)
    if bucket:
        rows.append(_render_field_row(bucket, justify))

    fields_html = "".join(rows)
    return f'<div class="entry" style="display:flex;flex-direction:column;gap:{gap};">{fields_html}</div>'


def _render_field_row(fields: list[FieldBlock], justify: str) -> str:
    """Render consecutive same-group fields as one flex row.

    A right-aligned field (``align="right"``) becomes the row's right rail:
    the first such field is pushed to the right edge via ``margin-left:auto``
    and the section's text alignment is ignored for that row. Otherwise the
    row's ``justify-content`` mirrors the section's ``text_align``."""

    rail_field = next((f for f in fields if f.align == "right"), None)
    base_style = "display:flex;flex-wrap:wrap;align-items:baseline;column-gap:1rem;row-gap:0.25rem"
    if rail_field is not None:
        inner = "".join(
            _render_field_block(f, extra_style="margin-left:auto" if f is rail_field else None)
            for f in fields
        )
        return f'<div class="field-row" style="{base_style}">{inner}</div>'
    inner = "".join(_render_field_block(f) for f in fields)
    return f'<div class="field-row" style="{base_style};justify-content:{justify}">{inner}</div>'


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


def _render_document(model: RenderModel, support: RendererSupport) -> str:
    best_effort = "\n".join(_best_effort_comments(model, support))
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
    .f-contact, .f-contact-sep, .f-email, .f-phone, .f-location, .f-site, .f-social-links, .f-date, .f-gpa, .f-link, .f-url, .f-tech, .f-tag, .f-proficiency, .f-meta {{ font-size: 0.75rem; }}
    .f-position, .f-degree {{ font-weight: 600; }}
    .f-link::after {{ content: " →"; }}
    .f-icon {{ display:inline-flex; width:0.9em; height:0.9em; margin-right:0.3em; vertical-align:-0.125em; }}
    .f-icon svg {{ width:100%; height:100%; }}
    .field-row {{ display:flex; flex-wrap:wrap; align-items:baseline; column-gap:1rem; row-gap:0.25rem; }}
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
        return _render_document(model, self.support)

    def render_bytes(self, model: RenderModel) -> bytes:
        return self.render(model).encode("utf-8")


__all__ = ["HTMLDocumentRenderer"]
