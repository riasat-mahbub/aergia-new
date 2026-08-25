"""AST builder for the ``research`` section.

Fields per entry: ``paper``, ``venue`` (publication venue), ``link``
(paper URL), ``date`` (publication), ``description``.
"""

from __future__ import annotations
from app.schema.models import Entry, FieldBlock, LayoutHints, Section, SectionInstance, TextStyle, TextRun
from ._utils import format_single_date, normalize_url_scheme, rich_text_to_field_block


def build_research(instance: SectionInstance, resolved_layout: LayoutHints | None = None) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("title"):
            fields.append(FieldBlock(key="paper", group="header", runs=[TextRun(text=str(row["title"]))]))
        raw_date = str(row.get("publication_date") or "")
        if raw_date:
            date_style = resolved_layout.date_style if resolved_layout else None
            formatted = format_single_date(raw_date, date_style)
            fields.append(FieldBlock(key="date", group="header", align="right", runs=[TextRun(text=formatted)]))
        venue = str(row.get("publication_value") or "").strip()
        if venue:
            fields.append(FieldBlock(key="venue", group="secondary", runs=[TextRun(text=venue)]))

        # Chromium silently drops <a href> annotations without a scheme;
        # normalize so legacy/loose data still exports clickable links.
        url = normalize_url_scheme(row.get("paper_url"))
        if url:
            link_text = str(row.get("paper_link_text") or "Paper")
            fields.append(FieldBlock(
                key="link", group="secondary", align="right",
                runs=[TextRun(text=link_text, style=TextStyle(link=url))],
            ))

        desc_block = rich_text_to_field_block("description", row.get("description"))
        if desc_block:
            fields.append(desc_block)

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="research",
        title=instance.title or "Research",
        enabled=instance.enabled,
        entries=entries,
    )
