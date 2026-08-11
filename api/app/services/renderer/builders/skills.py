"""AST builder for the ``skills`` section.

Each row in the data is a :class:`SkillGroup` with a ``category`` and
``items`` list. The builder emits a single ``Entry`` per group with a
``category`` field and one ``tag.<i>`` field per item.
"""

from __future__ import annotations
from app.schema.models import Entry, FieldBlock, LayoutHints, Section, SectionInstance, TextRun, TextStyle


def build_skills(instance: SectionInstance, resolved_layout: LayoutHints | None = None) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_group")
        fields: list[FieldBlock] = []

        if row.get("category"):
            fields.append(FieldBlock(key="category", group="body", runs=[TextRun(text=str(row["category"]), style=TextStyle(bold=True))]))

        items = row.get("items") or []
        for i, item in enumerate(items):
            if not item:
                continue
            fields.append(FieldBlock(key=f"tag.{i}", group="body", runs=[TextRun(text=str(item))]))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="skills",
        title=instance.title or "Skills",
        enabled=instance.enabled,
        entries=entries,
    )
