"""AST builder for the ``certifications`` section.

Fields per entry: ``certification``, ``date``, ``issuer``, ``link``
(credential URL, optional ``link_text``).
"""

from __future__ import annotations

from app.schema.models import Entry, FieldBlock, Section, SectionInstance, TextStyle, TextRun
from ._utils import format_single_date, normalize_url_scheme


def build_certifications(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        if row.get("name"):
            fields.append(FieldBlock(key="certification", group="header", runs=[TextRun(text=str(row["name"]))]))

        # `date` joins the header row alongside `certification`, matching the
        # research pattern (paper+date in row 0, venue+link in row 1).
        raw_date = str(row.get("date") or "")
        if raw_date:
            formatted = format_single_date(raw_date)
            fields.append(FieldBlock(key="date", group="header", align="right", runs=[TextRun(text=formatted)]))

        issuer = str(row.get("issuer") or "").strip()
        if issuer:
            fields.append(FieldBlock(key="issuer", group="secondary", runs=[TextRun(text=issuer)]))

        # Chromium silently drops <a href> annotations without a scheme;
        # normalize so legacy/loose data still exports clickable links.
        url = normalize_url_scheme(row.get("credential_url"))
        if url:
            link_text = str(row.get("link_text") or "Certificate")
            fields.append(FieldBlock(
                key="link", group="secondary", align="right",
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
