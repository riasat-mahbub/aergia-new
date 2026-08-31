"""Server-owned field policy for tailoring patches.

Tailoring receives an untrusted JSON patch. This module deliberately keeps the
policy separate from the local agent prompt and from the flexible CV AST so a
new CV field is not implicitly editable merely because a model can address it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class TailoringPolicyError(ValueError):
    """A patch attempts a field or structural mutation outside the policy."""


EDITABLE_RICH_TEXT_FIELDS: dict[str, frozenset[str]] = {
    "profile": frozenset({"summary"}),
    "experience": frozenset({"description"}),
    "education": frozenset({"summary"}),
    "projects": frozenset({"description"}),
    "research": frozenset({"description"}),
}

PROTECTED_FIELDS: dict[str, frozenset[str]] = {
    "profile": frozenset(
        {
            "name",
            "title",
            "email",
            "email_link",
            "phone",
            "location",
            "site_text",
            "site_url",
            "photo_url",
            "social_links",
        }
    ),
    "experience": frozenset(
        {"id", "company", "position", "start_date", "end_date", "current", "location"}
    ),
    "education": frozenset(
        {"id", "institution", "degree", "start_date", "end_date", "current", "gpa"}
    ),
    "skills": frozenset({"id", "category", "items"}),
    "projects": frozenset(
        {"id", "name", "url", "link_text", "start_date", "end_date", "tech_stack"}
    ),
    "languages": frozenset({"id", "language", "proficiency"}),
    "certifications": frozenset({"id", "name", "issuer", "date", "credential_url", "link_text"}),
    "research": frozenset(
        {"id", "title", "paper_url", "paper_link_text", "publication_date", "publication_value"}
    ),
    # Extras are user-defined and have no safe schema-level fact boundary yet.
    "extras": frozenset({"*"}),
}

LIBRARY_KIND_TO_SECTION_TYPE: dict[str, str] = {
    "experience": "experience",
    "education": "education",
    "skill": "skills",
    "project": "projects",
    "language": "languages",
    "certification": "certifications",
    "research": "research",
}

ENTRY_SECTION_TYPES = frozenset(LIBRARY_KIND_TO_SECTION_TYPE.values())


def editable_rich_text_fields(section_type: str) -> frozenset[str]:
    return EDITABLE_RICH_TEXT_FIELDS.get(section_type, frozenset())


def protected_fields(section_type: str) -> frozenset[str]:
    return PROTECTED_FIELDS.get(section_type, frozenset({"*"}))


def section_by_id(sections: list[dict[str, Any]], section_id: str) -> dict[str, Any]:
    matches = [section for section in sections if section.get("id") == section_id]
    if not matches:
        raise TailoringPolicyError("Tailoring target section not found")
    if len(matches) > 1:
        raise TailoringPolicyError("Tailoring target section is ambiguous")
    return matches[0]


def entry_by_id(section: Mapping[str, Any], entry_id: str | None) -> dict[str, Any]:
    section_type = str(section.get("type", ""))
    data = section.get("data")
    if section_type == "profile":
        if entry_id is not None:
            raise TailoringPolicyError("Profile rich text targets do not use entry_id")
        if not isinstance(data, dict):
            raise TailoringPolicyError("Profile section data is invalid")
        return data
    if not isinstance(data, list):
        raise TailoringPolicyError("Tailoring target section is not entry-based")
    matches = [entry for entry in data if isinstance(entry, dict) and entry.get("id") == entry_id]
    if not matches:
        raise TailoringPolicyError("Tailoring target entry not found")
    if len(matches) > 1:
        raise TailoringPolicyError("Tailoring target entry is ambiguous")
    return matches[0]


def validate_rich_text_target(section: Mapping[str, Any], field: str, entry_id: str | None) -> dict[str, Any]:
    section_type = str(section.get("type", ""))
    if field not in editable_rich_text_fields(section_type):
        raise TailoringPolicyError(f"Field {field!r} is not editable prose for section type {section_type!r}")
    return entry_by_id(section, entry_id)


def _section_shell(section: Mapping[str, Any]) -> dict[str, Any]:
    """Return fields no tailoring operation may mutate."""

    return {key: section.get(key) for key in ("id", "type", "title", "enabled", "style")}


def _entry_map(section: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    data = section.get("data")
    if isinstance(data, dict):
        return {"__profile__": data}
    if not isinstance(data, list):
        return {}
    return {
        str(entry["id"]): entry
        for entry in data
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }


def _allowed_changes(changes: Iterable[object]) -> tuple[dict[tuple[str, str], set[str]], set[tuple[str, str]]]:
    allowed_fields: dict[tuple[str, str], set[str]] = {}
    removable: set[tuple[str, str]] = set()
    for change in changes:
        operation = getattr(change, "operation", None)
        section_id = getattr(change, "section_id", None)
        entry_id = getattr(change, "entry_id", None)
        if not isinstance(section_id, str):
            continue
        key = (section_id, entry_id or "__profile__")
        if operation in {
            "replace_description",
            "replace_rich_text",
            "rewrite_rich_text",
            "remove_bullet",
            "reorder_bullets",
        }:
            field = getattr(change, "field", None) or "description"
            allowed_fields.setdefault(key, set()).add(field)
        elif operation == "remove_entry" and isinstance(entry_id, str):
            removable.add(key)
    return allowed_fields, removable


def _rich_text_changes(changes: Iterable[object]) -> dict[tuple[str, str, str], list[object]]:
    result: dict[tuple[str, str, str], list[object]] = {}
    for change in changes:
        operation = getattr(change, "operation", None)
        if operation not in {"rewrite_rich_text", "remove_bullet", "reorder_bullets"}:
            continue
        section_id = getattr(change, "section_id", None)
        field = getattr(change, "field", None)
        if not isinstance(section_id, str) or not isinstance(field, str):
            continue
        key = (section_id, getattr(change, "entry_id", None) or "__profile__", field)
        result.setdefault(key, []).append(change)
    return result


def _rich_text_blocks(value: Any) -> dict[str, Mapping[str, Any]] | None:
    if not isinstance(value, list):
        return None
    blocks: dict[str, Mapping[str, Any]] = {}
    for block in value:
        if not isinstance(block, Mapping) or not isinstance(block.get("id"), str):
            raise TailoringPolicyError("Rich-text blocks must have stable IDs")
        if block["id"] in blocks:
            raise TailoringPolicyError("Rich-text block IDs must be unique")
        blocks[block["id"]] = block
    return blocks


def _rich_text_items(block: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    items = block.get("items")
    if not isinstance(items, list):
        raise TailoringPolicyError("Rich-text block items are invalid")
    result: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            raise TailoringPolicyError("Rich-text items must have stable IDs")
        if item["id"] in result:
            raise TailoringPolicyError("Rich-text item IDs must be unique")
        result[item["id"]] = item
    return result


def _validate_rich_text_delta(
    before: Any,
    after: Any,
    changes: Iterable[object],
) -> None:
    """Allow text changes while keeping rich-text structure and styles fixed."""

    before_blocks = _rich_text_blocks(before)
    after_blocks = _rich_text_blocks(after)
    if before_blocks is None and after_blocks is None:
        return
    if before_blocks is None or after_blocks is None:
        raise TailoringPolicyError("Tailoring patches cannot change a rich-text field's representation")

    changes = list(changes)
    rewrite_allowed = any(getattr(change, "operation", None) == "rewrite_rich_text" for change in changes)
    removed_items = {
        getattr(change, "item_id", None)
        for change in changes
        if getattr(change, "operation", None) == "remove_bullet"
    }
    for block_id, before_block in before_blocks.items():
        after_block = after_blocks.get(block_id)
        if after_block is None:
            before_item_ids = set(_rich_text_items(before_block))
            if not rewrite_allowed and (not before_item_ids or not before_item_ids.issubset(removed_items)):
                raise TailoringPolicyError("Rich-text blocks may only disappear when all bullets are explicitly removed")
            continue
        if before_block.get("type", "paragraph") != after_block.get("type", "paragraph"):
            raise TailoringPolicyError("Tailoring patches cannot change rich-text block types")
        before_items = _rich_text_items(before_block)
        after_items = _rich_text_items(after_block)
        removed = set(before_items) - set(after_items)
        if not rewrite_allowed and not removed.issubset(removed_items):
            raise TailoringPolicyError("Rich-text items may only be removed with remove_bullet")
        if set(after_items) - set(before_items):
            raise TailoringPolicyError("Tailoring patches cannot add rich-text items")
        for item_id in set(before_items) & set(after_items):
            before_item = before_items[item_id]
            after_item = after_items[item_id]
            if before_item.get("style") != after_item.get("style"):
                raise TailoringPolicyError("Tailoring patches cannot change rich-text styles or links")

    if set(after_blocks) - set(before_blocks):
        raise TailoringPolicyError("Tailoring patches cannot add rich-text blocks")


def validate_document_delta(
    before_sections: list[dict[str, Any]], after_sections: list[dict[str, Any]], changes: Iterable[object]
) -> None:
    """Reject mutations outside operation-specific editable paths.

    Operation handlers already perform narrow mutations. This second pass is a
    defense against a future handler accidentally changing a protected field.
    It allows intentional entry removal/addition and prose-field edits while
    requiring every other value to remain byte-for-byte equivalent.
    """

    changes = list(changes)
    if len(before_sections) != len(after_sections):
        raise TailoringPolicyError("Tailoring patches cannot add or remove sections")

    before_by_id = {str(section.get("id")): section for section in before_sections}
    after_by_id = {str(section.get("id")): section for section in after_sections}
    if len(before_by_id) != len(before_sections) or len(after_by_id) != len(after_sections):
        raise TailoringPolicyError("Tailoring patches require unique section IDs")
    if set(before_by_id) != set(after_by_id):
        raise TailoringPolicyError("Tailoring patches cannot change section IDs")

    allowed_fields, removable = _allowed_changes(changes)
    rich_text_changes = _rich_text_changes(changes)
    for section_id, before_section in before_by_id.items():
        after_section = after_by_id[section_id]
        if _section_shell(before_section) != _section_shell(after_section):
            raise TailoringPolicyError("Tailoring patches cannot change section metadata or styles")

        before_entries = _entry_map(before_section)
        after_entries = _entry_map(after_section)
        for entry_id in set(before_entries) & set(after_entries):
            before_entry = before_entries[entry_id]
            after_entry = after_entries[entry_id]
            permitted = allowed_fields.get((section_id, entry_id), set())
            for key in set(before_entry) | set(after_entry):
                if key in permitted:
                    if key in {"description", "summary"}:
                        _validate_rich_text_delta(
                            before_entry.get(key),
                            after_entry.get(key),
                            rich_text_changes.get((section_id, entry_id, key), []),
                        )
                    continue
                if before_entry.get(key) != after_entry.get(key):
                    raise TailoringPolicyError(f"Protected CV field {key!r} was changed")

        removed = set(before_entries) - set(after_entries)
        if any((section_id, entry_id) not in removable for entry_id in removed):
            raise TailoringPolicyError("CV entries may only be removed with remove_entry")

        added = set(after_entries) - set(before_entries)
        # Library additions receive a server-generated CV entry ID, so the
        # actual added IDs are checked by the operation handler. Here we only
        # ensure no other structural addition occurred.
        expected_additions = sum(
            getattr(change, "operation", None) == "add_library_entry"
            and getattr(change, "section_id", None) == section_id
            for change in changes
        )
        if len(added) != expected_additions:
            raise TailoringPolicyError("CV entries may only be added from the Library")


__all__ = [
    "EDITABLE_RICH_TEXT_FIELDS",
    "ENTRY_SECTION_TYPES",
    "LIBRARY_KIND_TO_SECTION_TYPE",
    "PROTECTED_FIELDS",
    "TailoringPolicyError",
    "editable_rich_text_fields",
    "entry_by_id",
    "protected_fields",
    "section_by_id",
    "validate_document_delta",
    "validate_rich_text_target",
]
