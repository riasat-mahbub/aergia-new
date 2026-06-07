"""Experience section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both. No hardcoded `var(--xxx)` color or font lives in the markup
because that would block the per-section override from cascading in.
"""

from ._utils import esc, format_date_range


def render_experience(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    subsection_gap = css_vars.get("--subsection-gap", "16px")
    items = []
    for entry in data:
        end = format_date_range(
            entry.get("start_date", ""),
            entry.get("end_date"),
            bool(entry.get("current")),
        )
        loc = f', {esc(entry["location"])}' if entry.get("location") else ""
        items.append(
            f'''<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;margin:0;">{esc(entry.get("position", ""))}</h3>
      <p style="font-size:0.875rem;margin:0;">{esc(entry.get("company", ""))}{loc}</p>
    </div>
    <p style="font-size:0.75rem;margin:0;">{esc(end)}</p>
  </div>
  {f'<p style="margin-top:4px;font-size:0.875rem;margin-bottom:0;">{esc(entry["description"])}</p>' if entry.get("description") else ""}
</div>'''
        )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">' + "".join(items) + "</div>"
