"""Languages section renderer."""

from ._utils import esc


def render_languages(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;align-items:center;font-size:0.875rem;"><span>{esc(e.get("language", ""))}</span><span style="font-size:0.75rem;color:#9ca3af;">{esc(e.get("proficiency", ""))}</span></div>'
        for e in data
    )
    return f'<div style="display:flex;flex-direction:column;gap:4px;">{items}</div>'
