"""AST builder for the ``education`` section.

Fields per entry: ``degree``, ``institution``, ``date``, ``gpa``, ``summary``.
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextRun
from ._utils import format_date_range


def build_education(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("degree"):
            fields.append(FieldBlock(key="degree", group="header", runs=[TextRun(text=str(row["degree"]))]))

        date = format_date_range(
            str(row.get("start_date") or ""),
            row.get("end_date"),
            bool(row.get("current")),
        )
        if date:
            fields.append(FieldBlock(key="date", group="header", align="right", runs=[TextRun(text=date)]))

        if row.get("institution"):
            fields.append(FieldBlock(key="institution", group="secondary", runs=[TextRun(text=str(row["institution"]))]))
        if row.get("gpa"):
            fields.append(FieldBlock(key="gpa", group="secondary", align="right", runs=[TextRun(text=str(row["gpa"]))]))
        if row.get("summary"):
            fields.append(FieldBlock(key="summary", group="summary", runs=[TextRun(text=str(row["summary"]))]))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="education",
        title=instance.title or "Education",
        enabled=instance.enabled,
        entries=entries,
    )
