"""Education section renderer."""

from ._utils import esc


def _font_style(context: dict, kind: str) -> str:
    css_vars = context.get("css_vars") or {}
    key = "--heading-font" if kind == "heading" else "--body-font"
    font = context.get(f"{kind}_font") or css_vars.get(key)
    if not font:
        return ""
    return f"font-family:{font};"


def render_education(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:var(--text, #9ca3af);font-style:italic;">No data</p>'
    ctx = context or {}
    heading_font_style = _font_style(ctx, "heading")
    body_font_style = _font_style(ctx, "body")
    items = []
    for entry in data:
        end = "Present" if entry.get("current") else (esc(entry.get("end_date")) or "")
        gpa = f' | GPA: {esc(entry["gpa"])}' if entry.get("gpa") else ""
        items.append(
            f"""<div>
  <h3 style="font-weight:600;color:var(--heading, #111827);{heading_font_style}">{esc(entry.get("degree", ""))}</h3>
  <p style="font-size:0.875rem;color:var(--text, #6b7280);{body_font_style}">{esc(entry.get("institution", ""))}</p>
  <p style="font-size:0.75rem;color:var(--text, #9ca3af);{body_font_style}">{esc(entry.get("start_date", ""))} &ndash; {end}{gpa}</p>
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"
