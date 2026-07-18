"""AST builder for the ``certifications`` section.

Fields per entry: ``name``, ``meta`` (issuer + date), ``link``.
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextStyle, TextRun
from ._utils import format_single_date


def build_certifications(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("name"):
            fields.append(FieldBlock(key="name", group="header", runs=[TextRun(text=str(row["name"]))]))

        issuer = str(row.get("issuer") or "").strip()
        raw_date = str(row.get("date") or "")
        meta_parts = [p for p in (issuer, format_single_date(raw_date) if raw_date else "") if p]
        if meta_parts:
            fields.append(FieldBlock(key="meta", group="secondary", runs=[TextRun(text=" · ".join(meta_parts))]))

        url = str(row.get("credential_url") or "")
        if url:
            link_text = str(row.get("link_text") or "Certificate")
            fields.append(FieldBlock(
                key="link", group="body", align="right",
                runs=[TextRun(text=link_text, style=TextStyle(link=url))],
            ))

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="certifications",
        title=instance.title or "Certifications",
        enabled=instance.enabled,
        entries=entries,
    )
