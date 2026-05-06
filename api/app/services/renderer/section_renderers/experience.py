"""Experience section renderer."""

from ._utils import esc


def render_experience(data: list[dict] | None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;color:#9ca3af;font-style:italic;">No data</p>'
    items = []
    for entry in data:
        end = "Present" if entry.get("current") else (esc(entry.get("end_date")) or "")
        loc = f', {esc(entry["location"])}' if entry.get("location") else ""
        items.append(
            f"""<div style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <h3 style="font-weight:600;">{esc(entry.get("position", ""))}</h3>
      <p style="font-size:0.875rem;color:#6b7280;">{esc(entry.get("company", ""))}{loc}</p>
    </div>
    <p style="font-size:0.75rem;color:#9ca3af;">{esc(entry.get("start_date", ""))} &ndash; {end}</p>
  </div>
  {f'<p style="margin-top:4px;font-size:0.875rem;color:#374151;">{esc(entry["description"])}</p>' if entry.get("description") else ""}
</div>"""
        )
    return '<div style="display:flex;flex-direction:column;gap:16px;">' + "".join(items) + "</div>"
