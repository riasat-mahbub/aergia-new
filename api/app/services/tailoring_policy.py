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
            "rewrite_rich_text",
            "remove_bullet",
            "reorder_bullets",
        }:
            field = getattr(change, "field", None) or "description"
            allowed_fields.setdefault(key, set()).add(field)
        elif operation == "remove_entry" and isinstance(entry_id, str):
            removable.add(key)
    return allowed_fields, removable


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
