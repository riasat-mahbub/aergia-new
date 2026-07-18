"""AST builder for the ``experience`` section.

Emits one ``Entry`` per data row with fields: ``position``, ``date``,
``company``, ``location``, ``description``.

The ``date`` field is a single ``TextRun`` formatted via
:func:`format_date_range` so the resolver doesn't have to know about
date formatting. The format choice itself is a layout concern and lives
in :class:`LayoutHints.date_style`.

Row model: ``position`` + ``date`` (right rail) on the header row;
``company`` (left) + ``location`` (right rail) on the secondary row;
``description`` on the body row. The renderer turns the rail into
``margin-left:auto``; no comma joining happens between company and
location — they are independent fields on opposite ends of one row.
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextRun
from ._utils import format_date_range


def build_experience(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("position"):
            fields.append(FieldBlock(key="position", group="header", runs=[TextRun(text=str(row["position"]))]))

        date = format_date_range(
            str(row.get("start_date") or ""),
            row.get("end_date"),
            bool(row.get("current")),
        )
        if date:
            fields.append(FieldBlock(key="date", group="header", align="right", runs=[TextRun(text=date)]))

        if row.get("company") or row.get("location"):
            if row.get("company"):
                fields.append(FieldBlock(key="company", group="secondary", runs=[TextRun(text=str(row["company"]))]))
            if row.get("location"):
                fields.append(FieldBlock(key="location", group="secondary", align="right", runs=[TextRun(text=str(row["location"]))]))

        if row.get("description"):
            fields.append(FieldBlock(key="description", group="body", runs=[TextRun(text=str(row["description"]))]))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="experience",
        title=instance.title or "Experience",
        enabled=instance.enabled,
        entries=entries,
    )
