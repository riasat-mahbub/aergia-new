"""AST builder for the ``projects`` section.

Fields per entry: ``project``, ``link`` (the URL), ``date``,
``description``, ``tech`` (one per tech-stack item).
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextStyle, TextRun
from ._utils import format_date_range


def build_projects(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("name"):
            fields.append(FieldBlock(key="project", group="header", runs=[TextRun(text=str(row["name"]))]))

        date = format_date_range(
            str(row.get("start_date") or ""),
            row.get("end_date"),
            False,
        )
        if date:
            fields.append(FieldBlock(key="date", group="header", align="right", runs=[TextRun(text=date)]))

        url = str(row.get("url") or "")
        link_text = str(row.get("link_text") or url)
        if url:
            fields.append(FieldBlock(
                key="link", group="secondary", align="right",
                runs=[TextRun(text=link_text, style=TextStyle(link=url))],
            ))

        if row.get("description"):
            fields.append(FieldBlock(key="description", group="body", runs=[TextRun(text=str(row["description"]))]))

        tech = row.get("tech_stack") or []
        for t in tech:
            if not t:
                continue
            fields.append(FieldBlock(key="tech", group="body", runs=[TextRun(text=str(t))]))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="projects",
        title=instance.title or "Projects",
        enabled=instance.enabled,
        entries=entries,
    )
