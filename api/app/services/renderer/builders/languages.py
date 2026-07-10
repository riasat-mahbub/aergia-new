"""AST builder for the ``languages`` section.

Fields per entry: ``language``, ``proficiency``.
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextRun


def build_languages(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("language"):
            fields.append(FieldBlock(key="language", group="header", runs=[TextRun(text=str(row["language"]))]))
        if row.get("proficiency"):
            fields.append(FieldBlock(key="proficiency", group="header", align="right", runs=[TextRun(text=str(row["proficiency"]))]))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="languages",
        title=instance.title or "Languages",
        enabled=instance.enabled,
        entries=entries,
    )
