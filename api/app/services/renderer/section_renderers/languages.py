"""Languages section renderer."""

from ._utils import esc


def _font_style(context: dict, kind: str) -> str:
    css_vars = context.get("css_vars") or {}
    key = "--heading-font" if kind == "heading" else "--body-font"
    font = context.get(f"{kind}_font") or css_vars.get(key)
    if not font:
        return ""
    return f"font-family:{font};"


def render_languages(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:var(--text, #9ca3af);font-style:italic;">No data</p>'
    ctx = context or {}
    heading_font_style = _font_style(ctx, "heading")
    body_font_style = _font_style(ctx, "body")
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'font-size:0.875rem;">'
        f'<span style="color:var(--heading, #111827);{heading_font_style}">{esc(e.get("language", ""))}</span>'
        f'<span style="font-size:0.75rem;color:var(--text, #9ca3af);{body_font_style}">{esc(e.get("proficiency", ""))}</span>'
        f'</div>'
        for e in data
    )
    return f'<div style="display:flex;flex-direction:column;gap:4px;">{items}</div>'
