"""Canonical helpers for Aergia's persisted rich-text values.

The CV wire model predates stable IDs on rich-text blocks and list items.
Tailoring patches need those IDs to survive reordering, so this module owns
the small compatibility normalizer used by both ordinary CV writes and the
tailoring evidence boundary.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any


# Only these user-facing fields use the RichTextBlock[] representation. Keep
# this allowlist in one place so a future section cannot accidentally become a
# patchable rich-text target merely because it happens to contain a list.
RICH_TEXT_FIELDS_BY_SECTION: dict[str, frozenset[str]] = {
    "profile": frozenset({"summary"}),
    "experience": frozenset({"description"}),
    "education": frozenset({"summary"}),
    "projects": frozenset({"description"}),
    "research": frozenset({"description"}),
}


def rich_text_fields_for_section(section_type: str) -> frozenset[str]:
    """Return the canonical rich-text fields for one section type."""

    return RICH_TEXT_FIELDS_BY_SECTION.get(section_type, frozenset())


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _rows_for_section(section: dict[str, Any]) -> list[dict[str, Any]]:
    data = section.get("data")
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 128


def _normalize_blocks(value: list[Any]) -> bool:
    """Fill missing/duplicate block and item IDs in-place.

    Returning whether anything changed lets callers avoid incrementing a CV
    revision for already-canonical documents. Invalid non-dict values are left
    untouched and are rejected later by the normal SectionInstance validator.
    """

    changed = False
    block_ids: set[str] = set()
    for block in value:
        if not isinstance(block, dict):
            continue

        block_id = block.get("id")
        if not _valid_id(block_id) or block_id in block_ids:
            block["id"] = _new_id("rtb")
            block_id = block["id"]
            changed = True
        block_ids.add(block_id)

        items = block.get("items")
        if not isinstance(items, list):
            continue
        item_ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if not _valid_id(item_id) or item_id in item_ids:
                item["id"] = _new_id("rti")
                item_id = item["id"]
                changed = True
            item_ids.add(item_id)
    return changed


def normalize_rich_text_ids(raw_sections: Any) -> tuple[Any, bool]:
    """Return a copied section payload with stable rich-text IDs filled in."""

    normalized = copy.deepcopy(raw_sections)
    if isinstance(normalized, dict) and isinstance(normalized.get("sections"), list):
        sections = normalized["sections"]
    elif isinstance(normalized, list):
        sections = normalized
    else:
        return normalized, False

    changed = False
    for section in sections:
        if not isinstance(section, dict):
            continue
        fields = rich_text_fields_for_section(str(section.get("type", "")))
        if not fields:
            continue
        for row in _rows_for_section(section):
            for field_name in fields:
                value = row.get(field_name)
                if isinstance(value, list) and _normalize_blocks(value):
                    changed = True
    return normalized, changed


__all__ = [
    "RICH_TEXT_FIELDS_BY_SECTION",
    "normalize_rich_text_ids",
    "rich_text_fields_for_section",
]
