"""Assemble resolved sections into a complete HTML document."""

from __future__ import annotations

from app.document_schema.models import RenderModel, ResolvedZone
from .html_markup import (
    attr,
    format_inline_style as _format_inline_style,
    style_attr as _style_attr,
)
from .html_sections import _render_section
from app.services.renderer.html_values import (
    LINK_STYLES,
    PLAIN_LINK_STYLES,
    PRINT_STYLES,
    safe_color as _safe_color,
    safe_font_family as _safe_font_family,
    safe_spacing as _safe_spacing,
)
from app.services.renderer.support import RendererSupport, SupportLevel


_CSS_VAR_NAMES = frozenset(
    {
        "--spacing-section",
        "--spacing-subsection",
        "--body-font",
        "--heading-font",
        "--accent",
    }
)


def _best_effort_comments(model: RenderModel, support: RendererSupport) -> str:
    if support.keep_with_next is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: keep_with_next -->"
    if support.heading_keeps_with_first is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: heading_keeps_with_first -->"
    if support.break_before is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: break_before -->"
    if support.keep_entry_together is SupportLevel.BEST_EFFORT:
        yield "<!-- best-effort: keep_entry_together -->"


def _render_css_vars(model: RenderModel) -> str:
    if not model.css_vars:
        return ""
    lines: list[str] = []
    for key, value in model.css_vars.items():
        if key not in _CSS_VAR_NAMES:
            continue
        if key in {"--accent"}:
            safe_value = _safe_color(value)
        elif key in {"--body-font", "--heading-font"}:
            safe_value = _safe_font_family(value)
        else:
            safe_value = _safe_spacing(value)
        if safe_value:
            lines.append(f"  {key}: {safe_value};")
    if not lines:
        return ""
    return ":root {\n" + "\n".join(lines) + "\n}"


def _render_zone(zone: ResolvedZone, sections_by_id) -> str:
    safe_zone_decls: list[str] = []
    for key, value in zone.styles.items():
        if key == "width" and value in {"30%", "50%", "100%", "auto"}:
            safe_zone_decls.append(f"width:{value}")
        elif key == "padding" and _safe_spacing(value):
            safe_zone_decls.append(f"padding:{_safe_spacing(value)}")
        elif key == "background-color" and _safe_color(value):
            safe_zone_decls.append(f"background-color:{_safe_color(value)}")
    style_str = _format_inline_style(safe_zone_decls)
    panels: list[str] = []
    for section_id in zone.section_ids:
        section = sections_by_id.get(section_id)
        if section is None:
            continue
        panels.append(_render_section(section))
    return (
        f'<div class="zone" data-preview-zone="true" data-preview-zone-id="{attr(zone.id)}"'
        f"{_style_attr(style_str)}>"
        f"{''.join(panels)}"
        f"</div>"
    )


def _render_document(model: RenderModel, support: RendererSupport) -> str:
    best_effort = "\n".join(_best_effort_comments(model, support))
    css_vars_block = _render_css_vars(model)
    zones_html = "".join(_render_zone(zone, model.sections) for zone in model.zones)
    body_font = _safe_font_family(model.body_font) or "system-ui, sans-serif"
    heading_font = _safe_font_family(model.heading_font) or body_font
    link_styles = model.link_styles if model.link_styles in {LINK_STYLES, PLAIN_LINK_STYLES} else PLAIN_LINK_STYLES
    print_styles = model.print_styles if model.print_styles == PRINT_STYLES else PRINT_STYLES
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
{css_vars_block}
    body {{
      margin: 0;
      padding: 0;
      font-family: {body_font};
      color: var(--text, #374151);
      background: var(--bg, #ffffff);
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: {heading_font};
    }}
    .f-name {{ font-size: 1.5rem; font-weight: 700; }}
    .f-title, .f-company, .f-institution, .f-category, .f-venue, .f-issuer {{ font-size: 0.875rem; }}
    .f-summary, .f-description {{ font-size: 0.75rem; }}
    .f-contact, .f-contact-sep, .f-email, .f-phone, .f-location, .f-site, .f-date, .f-gpa, .f-link, .f-tech, .f-tag, .f-proficiency, .f-meta {{ font-size: 0.75rem; }}
    /* Social row: smaller than the other contact fields so the icon+label
       pairs read as fine metadata next to the email/phone row. */
    .f-social {{ display:inline-block; font-size: 0.83rem; }}
    .f-social:last-child {{ margin-right: 0; }}
    .f-social-link {{ margin-right: 1.5rem; }}
    .f-social-link:last-child {{ margin-right: 0; }}
    .f-position, .f-degree, .f-project, .f-certification, .f-paper, .f-category {{ font-weight: 600; }}
    /* Rich text blocks: paragraphs and lists inside description/summary fields */
    .f-description p, .f-summary p {{ margin: 0.25rem 0; }}
    .f-description p:first-child, .f-summary p:first-child {{ margin-top: 0; }}
    .f-description p:last-child, .f-summary p:last-child {{ margin-bottom: 0; }}
    .f-description ul, .f-description ol, .f-summary ul, .f-summary ol {{ margin: 0.25rem 0; padding-left: 1.5rem; }}
    .f-description ul, .f-summary ul {{ list-style-type: disc; }}
    .f-description ol, .f-summary ol {{ list-style-type: decimal; }}
    .f-description li, .f-summary li {{ margin: 0.125rem 0; }}

    .f-icon {{ display:inline-flex; width:0.75em; height:0.75em; margin-right:0.25em; vertical-align:-0.1em; }}
    .f-icon svg {{ width:100%; height:100%; }}
    /* Pipe separator between adjacent contact fields in the profile row
       (email | phone | location | site). Skipped on the first child so
       the row doesn't start with a dangling pipe. The profile builder
       emits f-email/f-phone/f-location/f-site (not f-contact), so the
       selectors target those classes specifically. */
    .f-email + .f-phone::before,
    .f-phone + .f-location::before,
    .f-location + .f-site::before,
    .f-email + .f-location::before,
    .f-email + .f-site::before,
    .f-phone + .f-site::before {{
      content: " | ";
      color: var(--text, #6b7280);
      margin: 0 0.35em;
    }}
    .field-row {{ display:flex; flex-wrap:wrap; align-items:baseline; column-gap:0; row-gap:0; }}
    .f-chip-group {{ display:flex; flex-wrap:wrap; align-items:center; gap:0.25rem; width:100%; min-width:0; max-width:100%; }}
    .f-chip-link {{ display:inline-flex; text-decoration:none; color:inherit; max-width:100%; min-width:0; }}
    .f-chip {{ display:inline-flex; align-items:center; box-sizing:border-box; max-width:100%; min-width:0; background:#eff6ff; padding:2px 8px; border-radius:9999px; color:var(--section-body-color,#1d4ed8); font-size:0.75rem; line-height:1.2; overflow-wrap:anywhere; }}
    /* A section body size is opt-in. Keep the field grammar above unchanged
       for untouched sections, then let the section-local control replace
       every field default when it is set. */
    section[data-preview-body-size] .f-name,
    section[data-preview-body-size] .f-title,
    section[data-preview-body-size] .f-company,
    section[data-preview-body-size] .f-institution,
    section[data-preview-body-size] .f-category,
    section[data-preview-body-size] .f-venue,
    section[data-preview-body-size] .f-issuer,
    section[data-preview-body-size] .f-summary,
    section[data-preview-body-size] .f-description,
    section[data-preview-body-size] .f-contact,
    section[data-preview-body-size] .f-contact-sep,
    section[data-preview-body-size] .f-email,
    section[data-preview-body-size] .f-phone,
    section[data-preview-body-size] .f-location,
    section[data-preview-body-size] .f-site,
    section[data-preview-body-size] .f-date,
    section[data-preview-body-size] .f-gpa,
    section[data-preview-body-size] .f-link,
    section[data-preview-body-size] .f-tech,
    section[data-preview-body-size] .f-tag,
    section[data-preview-body-size] .f-proficiency,
    section[data-preview-body-size] .f-meta,
    section[data-preview-body-size] .f-social,
    section[data-preview-body-size] .f-chip {{ font-size:var(--section-body-size); }}
{link_styles}    {print_styles}
  </style>
{best_effort}
</head>
<body>
  <div style="display:flex;flex-direction:row;align-items:flex-start;gap:var(--spacing-section, 16px);">
{zones_html}
  </div>
</body>
</html>"""


__all__ = ["_render_document"]
