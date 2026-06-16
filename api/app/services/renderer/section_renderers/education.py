"""Education section renderer.

The wrapper carries the per-section color and font, so every child element
inherits both.
"""

from ._utils import esc, format_date_range


def render_education(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    subsection_gap = css_vars.get("--subsection-gap", "12px")
    date_style = (context or {}).get("instance_style", {}).get("date_style")
    items = []
    for entry in data:
        gpa = (
            f'<p class="f-gpa" style="margin:0;">GPA: {esc(entry["gpa"])}</p>'
            if entry.get("gpa")
            else ""
        )
        summary = (
            f'<p class="f-summary" style="margin-top:4px;margin-bottom:0;">{esc(entry["summary"])}</p>'
            if entry.get("summary")
            else ""
        )
        date_range = format_date_range(
            entry.get("start_date", ""),
            entry.get("end_date"),
            bool(entry.get("current")),
            date_style,
        )
        items.append(
            f'''<div>
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 class="f-degree" style="margin:0;">{esc(entry.get("degree", ""))}</h3>
      <p class="f-institution" style="margin:0;">{esc(entry.get("institution", ""))}</p>
    </div>
    <p class="f-date" style="margin:0;">{esc(date_range)}</p>
  </div>
  {gpa}
  {summary}
</div>'''
        )
    return f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">' + "".join(items) + "</div>"
