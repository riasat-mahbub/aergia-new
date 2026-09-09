"""Server-owned field policy for tailoring patches.

Tailoring receives an untrusted JSON patch. This module deliberately keeps the
policy separate from the local agent prompt and from the flexible CV AST so a
new CV field is not implicitly editable merely because a model can address it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import ValidationError

from app.document_schema.capabilities import (
    EDITABLE_RICH_TEXT_FIELDS,
    ENTRY_SECTION_TYPES,
    LIMITS,
    LIBRARY_KIND_TO_SECTION_TYPE,
    PROTECTED_FIELDS,
    RENDERABLE_SECTION_TYPES,
)
from app.document_schema.models import RichTextBlock, SectionInstance


class TailoringPolicyError(ValueError):
    """A patch attempts a field or structural mutation outside the policy."""


def editable_rich_text_fields(section_type: str) -> frozenset[str]:
    return EDITABLE_RICH_TEXT_FIELDS.get(section_type, frozenset())


def protected_fields(section_type: str) -> frozenset[str]:
    return PROTECTED_FIELDS.get(section_type, frozenset({"*"}))


def validate_section_payload(section: Mapping[str, Any]) -> None:
    """Validate the bounded wire shape used by a structural section change.

    The normal CV schema intentionally leaves row fields flexible because the
    renderer owns type-specific interpretation. Structural tailoring still
    needs a smaller boundary: only renderer-backed section types, stable row
    IDs, and the generic ``extras`` row shape are accepted.
    """

    try:
        SectionInstance.model_validate(section)
    except ValidationError as exc:
        raise TailoringPolicyError("Section payload does not match the renderer wire schema") from exc

    section_type = section.get("type")
    if section_type not in RENDERABLE_SECTION_TYPES:
        raise TailoringPolicyError(f"Section type {section_type!r} cannot be rendered")
    if (
        not isinstance(section.get("id"), str)
        or not section["id"].strip()
        or len(section["id"]) > LIMITS["max_section_id_length"]
    ):
        raise TailoringPolicyError("Tailoring sections require a non-empty ID")
    if (
        not isinstance(section.get("title"), str)
        or not section["title"].strip()
        or len(section["title"]) > LIMITS["max_section_title_length"]
    ):
        raise TailoringPolicyError("Tailoring sections require a non-empty title")

    _validate_nested_limits(section.get("data"))

    data = section.get("data")
    if section_type == "profile":
        if not isinstance(data, dict):
            raise TailoringPolicyError("Profile sections require object data")
        _validate_rich_text_fields(data)
        return
    if not isinstance(data, list):
        raise TailoringPolicyError("Entry-based sections require list data")

    entry_ids: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            raise TailoringPolicyError("Section entries must be objects")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip():
            raise TailoringPolicyError("Section entries require non-empty IDs")
        if row_id in entry_ids:
            raise TailoringPolicyError("Section entry IDs must be unique")
        entry_ids.add(row_id)
        _validate_rich_text_fields(row)
        if section_type != "extras":
            continue
        fields = row.get("fields", [])
        if not isinstance(fields, list):
            raise TailoringPolicyError("Extras entries require a fields list")
        for field in fields:
            if not isinstance(field, dict):
                raise TailoringPolicyError("Extras fields must be objects")
            label = field.get("label")
            if not isinstance(label, str) or not label.strip():
                raise TailoringPolicyError("Extras fields require non-empty labels")
            if "value" not in field:
                raise TailoringPolicyError("Extras fields require a value")


def _validate_nested_limits(value: Any) -> None:
    """Apply renderer wire limits to the otherwise generic data payload."""

    if isinstance(value, str):
        if len(value) > LIMITS["max_field_text_length"]:
            raise TailoringPolicyError("Section field text exceeds the renderer limit")
        return
    if isinstance(value, list):
        if len(value) > LIMITS["max_section_entries"]:
            raise TailoringPolicyError("Section data contains too many entries")
        for child in value:
            _validate_nested_limits(child)
        return
    if isinstance(value, dict):
        if len(value) > LIMITS["max_section_entries"]:
            raise TailoringPolicyError("Section data contains too many fields")
        for child in value.values():
            _validate_nested_limits(child)


def _validate_rich_text_fields(row: Mapping[str, Any]) -> None:
    """Validate rich-text values embedded in a complete section payload."""

    for field_name in ("description", "summary"):
        value = row.get(field_name)
        if not isinstance(value, list):
            continue
        for block in value:
            if not isinstance(block, Mapping):
                raise TailoringPolicyError(f"Rich-text field {field_name!r} contains an invalid block")
            try:
                RichTextBlock.model_validate(block)
            except ValidationError as exc:
                raise TailoringPolicyError(f"Rich-text field {field_name!r} contains an invalid block") from exc
            if not isinstance(block.get("id"), str) or not block["id"].strip():
                raise TailoringPolicyError("Structural rich-text blocks require stable IDs")
            items = block.get("items")
            if not isinstance(items, list):
                raise TailoringPolicyError(f"Rich-text field {field_name!r} contains invalid items")
            for item in items:
                if not isinstance(item, Mapping) or not isinstance(item.get("id"), str) or not item["id"].strip():
                    raise TailoringPolicyError("Structural rich-text items require stable IDs")


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


def _fresh_section_activation_allowed(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    changes: Iterable[object],
) -> bool:
    """Allow an empty fresh section to become visible when it receives a row."""

    if before.get("enabled") is not False or after.get("enabled") is not True:
        return False
    if any(
        before.get(key) != after.get(key)
        for key in ("id", "type", "title", "style")
    ):
        return False
    if str(before.get("type", "")) not in ENTRY_SECTION_TYPES or before.get("data") != []:
        return False
    if not isinstance(after.get("data"), list) or not after.get("data"):
        return False
    return any(
        getattr(change, "operation", None) == "add_library_entry"
        and getattr(change, "section_id", None) == before.get("id")
        for change in changes
    )


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
    """Allow prose rewrites while keeping existing structure and styles safe.

    A full ``rewrite_rich_text`` may add plain blocks/items when the model has
    supported evidence for genuinely new prose. Explicit bullet operations
    remain removal/reordering-only, and existing formatting cannot be changed.
    """

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
        added_items = set(after_items) - set(before_items)
        if added_items and not rewrite_allowed:
            raise TailoringPolicyError("Tailoring patches cannot add rich-text items")
        for item_id in added_items:
            if after_items[item_id].get("style") not in (None, {}):
                raise TailoringPolicyError("Tailoring patches cannot add rich-text styles or links")
        for item_id in set(before_items) & set(after_items):
            before_item = before_items[item_id]
            after_item = after_items[item_id]
            if before_item.get("style") != after_item.get("style"):
                raise TailoringPolicyError("Tailoring patches cannot change rich-text styles or links")

    added_blocks = set(after_blocks) - set(before_blocks)
    if added_blocks and not rewrite_allowed:
        raise TailoringPolicyError("Tailoring patches cannot add rich-text blocks")
    for block_id in added_blocks:
        for item in _rich_text_items(after_blocks[block_id]).values():
            if item.get("style") not in (None, {}):
                raise TailoringPolicyError("Tailoring patches cannot add rich-text styles or links")


def validate_document_delta(
    before_sections: list[dict[str, Any]], after_sections: list[dict[str, Any]], changes: Iterable[object]
) -> None:
    """Reject mutations outside the operation-specific tailoring policy.

    The narrow operations keep their original copy-on-write guarantees. The
    auditable structural operations can replace, create, remove, or reorder
    complete sections; their handlers validate the proposed section shape and
    the fact guard validates the declared evidence separately.
    """

    changes = list(changes)

    def _created_id(change: object) -> str | None:
        section = getattr(change, "section", None)
        if isinstance(section, Mapping):
            value = section.get("id")
        else:
            value = getattr(section, "id", None)
        return value if isinstance(value, str) else None

    create_changes = [change for change in changes if getattr(change, "operation", None) == "create_section"]
    replace_changes = [change for change in changes if getattr(change, "operation", None) == "replace_section"]
    remove_changes = [change for change in changes if getattr(change, "operation", None) == "remove_section"]
    reorder_changes = [change for change in changes if getattr(change, "operation", None) == "reorder_sections"]
    created_ids = [_created_id(change) for change in create_changes]
    created_ids = [section_id for section_id in created_ids if section_id is not None]
    replaced_ids = [getattr(change, "section_id", None) for change in replace_changes]
    removed_ids = [getattr(change, "section_id", None) for change in remove_changes]
    if len(set(created_ids)) != len(created_ids) or len(set(replaced_ids)) != len(replaced_ids):
        raise TailoringPolicyError("Structural section targets must be unique")
    if len(set(removed_ids)) != len(removed_ids):
        raise TailoringPolicyError("A section may only be removed once")

    before_ids = [str(section.get("id")) for section in before_sections]
    after_ids = [str(section.get("id")) for section in after_sections]
    before_by_id = {section_id: section for section_id, section in zip(before_ids, before_sections, strict=True)}
    after_by_id = {section_id: section for section_id, section in zip(after_ids, after_sections, strict=True)}
    if len(before_by_id) != len(before_sections) or len(after_by_id) != len(after_sections):
        raise TailoringPolicyError("Tailoring patches require unique section IDs")

    before_id_set = set(before_by_id)
    created_id_set = set(created_ids)
    replaced_id_set = set(replaced_ids)
    removed_id_set = set(removed_ids)
    if created_id_set & before_id_set:
        raise TailoringPolicyError("Created section IDs must be new")
    if replaced_id_set - (before_id_set | created_id_set):
        raise TailoringPolicyError("Replacement section target was not created or present")
    if removed_id_set - before_id_set:
        raise TailoringPolicyError("Removed section target was not present")
    if (created_id_set & removed_id_set) or (replaced_id_set & removed_id_set):
        raise TailoringPolicyError("A structural section target cannot be replaced and removed in one patch")

    expected_ids = (before_id_set - removed_id_set) | created_id_set
    if set(after_by_id) != expected_ids:
        raise TailoringPolicyError("Section additions/removals do not match the structural operations")
    if not reorder_changes:
        expected_order = [section_id for section_id in before_ids if section_id not in removed_id_set]
        expected_order.extend(created_ids)
        if after_ids != expected_order:
            raise TailoringPolicyError("Section order may only change with reorder_sections")
    elif len(reorder_changes) != 1:
        raise TailoringPolicyError("A patch may contain at most one reorder_sections operation")

    allowed_fields, removable = _allowed_changes(changes)
    rich_text_changes = _rich_text_changes(changes)
    for section_id, before_section in before_by_id.items():
        if section_id in removed_id_set:
            continue
        after_section = after_by_id[section_id]
        if section_id in replaced_id_set:
            # The complete replacement is authorized by the structural
            # operation; the handler and evidence/fact validators inspect it.
            continue
        if _section_shell(before_section) != _section_shell(after_section) and not _fresh_section_activation_allowed(
            before_section,
            after_section,
            changes,
        ):
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
    "RENDERABLE_SECTION_TYPES",
    "TailoringPolicyError",
    "editable_rich_text_fields",
    "entry_by_id",
    "protected_fields",
    "section_by_id",
    "validate_section_payload",
    "validate_document_delta",
    "validate_rich_text_target",
]
