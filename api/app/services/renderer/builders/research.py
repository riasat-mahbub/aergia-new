"""AST builder for the ``research`` section.

Fields per entry: ``title``, ``venue`` (publication venue), ``link``
(paper URL), ``date`` (publication), ``description``.
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextRun
from ._utils import format_single_date


def build_research(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("title"):
            fields.append(FieldBlock(key="title", group="header", runs=[TextRun(text=str(row["title"]))]))

        raw_date = str(row.get("publication_date") or "")
        if raw_date:
            formatted = format_single_date(raw_date)
            fields.append(FieldBlock(key="date", group="header", align="right", runs=[TextRun(text=formatted)]))

        venue = str(row.get("publication_value") or "").strip()
        if venue:
            fields.append(FieldBlock(key="venue", group="secondary", runs=[TextRun(text=venue)]))

        url = str(row.get("paper_url") or "")
        if url:
            link_text = str(row.get("paper_link_text") or "Paper")
            fields.append(FieldBlock(key="link", group="secondary", runs=[TextRun(text=link_text)]))

        if row.get("description"):
            fields.append(FieldBlock(key="description", group="body", runs=[TextRun(text=str(row["description"]))]))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="research",
        title=instance.title or "Research",
        enabled=instance.enabled,
        entries=entries,
    )
