"""Education section renderer."""

from ._utils import esc


def render_education(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for entry in data:
        end = "Present" if entry.get("current") else (esc(entry.get("end_date")) or "")
        gpa = f' | GPA: {esc(entry["gpa"])}' if entry.get("gpa") else ""
        items.append(
            f"""<div>
  <h3 style="font-weight:600;">{esc(entry.get("degree", ""))}</h3>
  <p style="font-size:0.875rem;color:#6b7280;">{esc(entry.get("institution", ""))}</p>
  <p style="font-size:0.75rem;color:#9ca3af;">{esc(entry.get("start_date", ""))} &ndash; {end}{gpa}</p>
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:12px;">' + "".join(items) + "</div>"
