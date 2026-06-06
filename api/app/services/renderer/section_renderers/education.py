"""Education section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both.
"""

from ._utils import esc, format_date_range


def render_education(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    items = []
    for entry in data:
        gpa = (
            f'<p style="font-size:0.75rem;margin:0;">GPA: {esc(entry["gpa"])}</p>'
            if entry.get("gpa")
            else ""
        )
        items.append(
            f'''<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;margin:0;">{esc(entry.get("degree", ""))}</h3>
      <p style="font-size:0.875rem;margin:0;">{esc(entry.get("institution", ""))}</p>
    </div>
    <p style="font-size:0.75rem;margin:0;">{esc(format_date_range(entry.get("start_date", ""), entry.get("end_date"), bool(entry.get("current"))))}</p>
  </div>
  {gpa}
</div>'''
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"
