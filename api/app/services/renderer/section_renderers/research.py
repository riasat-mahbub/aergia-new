"""Research section renderer.

Each entry renders as a left-bordered publication citation card — visually
distinct from the unbordered Projects list. The paper title sits on the left;
when a URL is present, an explicit label (defaulting to "Paper") plus a small
external-link glyph appears on the right. Optional publication date and
prose description follow below.

Inline styles are kept minimal so the per-section wrapper's color/font cascade
remains authoritative.
"""

from ._utils import esc, esc_attr, normalize_url_scheme


def render_research(data: list[dict] | None, context: dict | None = None) -> str:
    if not data:
        return '<p style="font-size:0.875rem;font-style:italic;opacity:0.7;">No data</p>'
    css_vars = (context or {}).get("css_vars") or {}
    subsection_gap = css_vars.get("--subsection-gap", "16px")
    items = []
    for entry in data:
        title = esc(entry.get("title", ""))
        paper_url = entry.get("paper_url") or ""
        # paper_link_text is content for the f-url anchor; default to "Paper"
        # only when a URL exists so a stray label without a target never
        # renders as an affordance.
        link_text = esc(entry.get("paper_link_text") or "Paper")
        description = esc(entry.get("description", ""))
        publication_date = esc(entry.get("publication_date", ""))

        # Normalize bare domains so Chromium emits a /Link annotation in PDF.
        url_href = esc_attr(normalize_url_scheme(paper_url))
        anchor = (
            f'<a class="f-url" href="{url_href}" '
            f'style="flex-shrink:0;">{link_text}'
            f'<span aria-hidden="true"> ↗</span></a>'
            if paper_url
            else ""
        )
        date_paragraph = (
            f'<p class="f-date" style="margin:2px 0 0;font-size:0.75rem;opacity:0.75;">'
            f'Published {publication_date}</p>'
            if publication_date
            else ""
        )
        description_paragraph = (
            f'<p class="f-description" style="margin:6px 0 0;">{description}</p>'
            if description
            else ""
        )
        items.append(
            f'''<article class="f-research-entry" style="border-left:2px solid var(--accent, #2563eb);padding-left:12px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
    <h3 class="f-title" style="margin:0;">{title}</h3>
    {anchor}
  </div>
  {date_paragraph}
  {description_paragraph}
</article>'''
        )
    return (
        f'<div style="display:flex;flex-direction:column;gap:{subsection_gap};">'
        + "".join(items)
        + "</div>"
    )
