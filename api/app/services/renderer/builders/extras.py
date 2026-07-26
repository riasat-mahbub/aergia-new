"""AST builder for the ``extras`` section.

A user-defined block of CV content. ``data`` is a list of entries shaped like::

    [
        {
            "id": "<uuid>",
            "title": "<section title>",
            "fields": [
                {"label": "<key>", "value": "<text>"},
                ...
            ],
        },
        ...
    ]

Each entry emits one :class:`Entry` whose first ``FieldBlock`` is the entry
``title`` (``group="header"``), followed by one ``FieldBlock`` per
``{label, value}`` pair (``key=f"field:{label}"``, ``group="body"``). The
existing :func:`app.services.renderer.html._render_field_row` treats these
groups the same as Experience/Skills, so no renderer branch is required.

Field values that look like URLs (explicit schemes, ``www.`` prefix, or
bare ``domain.tld``) are passed through :func:`normalize_url_scheme` so the
exported PDF keeps clickable anchors — same precedent as Profile site URLs.

Entries with neither a title nor any fields are dropped, matching the
empty-entry behaviour in :func:`build_skills`.
"""

from __future__ import annotations

from app.schema.models import (
    Entry,
    FieldBlock,
    Section,
    SectionInstance,
    TextRun,
    TextStyle,
)

from ._utils import normalize_url_scheme


_URL_SAFE = "-._~:/?#[]@!$&'()*+,;=%"


def _looks_like_url(value: str) -> bool:
    """Heuristic URL detection for extras field values.

    Accepts explicit schemes (``http://``, ``https://``, ``mailto:``, …) and
    the ``www.`` prefix, plus bare ``domain.tld`` shapes (no whitespace, at
    least one dot, only URL-safe punctuation) so users can paste either form.
    """
    lowered = value.lower().lstrip()
    if lowered.startswith(("http://", "https://", "www.")):
        return True
    if " " in lowered or "\n" in lowered or "." not in lowered:
        return False
    return all(ch.isalnum() or ch in _URL_SAFE for ch in lowered)


def build_extras(instance: SectionInstance) -> Section:
    rows = instance.data if isinstance(instance.data, list) else []

    entries: list[Entry] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        entry_id = str(row.get("id") or f"{instance.id}_entry")
        fields: list[FieldBlock] = []

        title = str(row.get("title") or "").strip()
        if title:
            fields.append(
                FieldBlock(
                    key="title",
                    group="header",
                    runs=[TextRun(text=title)],
                )
            )

        raw_fields = row.get("fields") or []
        for raw_field in raw_fields:
            if not isinstance(raw_field, dict):
                continue
            label = str(raw_field.get("label") or "").strip()
            value = raw_field.get("value")
            if not label or value is None:
                continue
            value_text = str(value).strip()
            if not value_text:
                continue

            style: TextStyle | None = None
            if _looks_like_url(value_text):
                style = TextStyle(link=normalize_url_scheme(value_text))

            fields.append(
                FieldBlock(
                    key=f"field:{label}",
                    group="body",
                    runs=[TextRun(text=value_text, style=style)],
                )
            )

        if fields:
            entries.append(Entry(id=entry_id, fields=fields))

    return Section(
        id=instance.id,
        type="extras",
        title=instance.title or "Extras",
        enabled=instance.enabled,
        entries=entries,
    )
