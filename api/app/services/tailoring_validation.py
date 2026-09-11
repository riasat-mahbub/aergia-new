"""Mechanical validation for complete tailoring candidates.

This module is intentionally small. It checks the renderer wire shape and
resource limits; it does not attempt to prove prose, infer a user's skills, or
maintain a second patch policy.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.document_schema.capabilities import ENTRY_SECTION_TYPES, LIMITS, RENDERABLE_SECTION_TYPES
from app.document_schema.models import RichTextBlock, SectionInstance


class CandidateValidationError(ValueError):
    """A candidate is not safe for the renderer's bounded wire model."""


def _validate_nested_limits(value: Any) -> None:
    if isinstance(value, str):
        if len(value) > LIMITS["max_field_text_length"]:
            raise CandidateValidationError("Section field text exceeds the renderer limit")
        return
    if isinstance(value, list):
        if len(value) > LIMITS["max_section_entries"]:
            raise CandidateValidationError("Section data contains too many entries")
        for child in value:
            _validate_nested_limits(child)
        return
    if isinstance(value, dict):
        if len(value) > LIMITS["max_section_entries"]:
            raise CandidateValidationError("Section data contains too many fields")
        for child in value.values():
            _validate_nested_limits(child)


def _validate_rich_text_fields(row: Mapping[str, Any]) -> None:
    for field_name in ("description", "summary"):
        value = row.get(field_name)
        if not isinstance(value, list):
            continue
        for block in value:
            if not isinstance(block, Mapping):
                raise CandidateValidationError(f"Rich-text field {field_name!r} contains an invalid block")
            try:
                RichTextBlock.model_validate(block)
            except ValidationError as exc:
                raise CandidateValidationError(f"Rich-text field {field_name!r} contains an invalid block") from exc


def validate_section_payload(section: Mapping[str, Any]) -> None:
    try:
        SectionInstance.model_validate(section)
    except ValidationError as exc:
        raise CandidateValidationError("Section payload does not match the renderer wire schema") from exc

    section_type = section.get("type")
    if section_type not in RENDERABLE_SECTION_TYPES:
        raise CandidateValidationError(f"Section type {section_type!r} cannot be rendered")
    if not isinstance(section.get("id"), str) or not section["id"].strip() or len(section["id"]) > LIMITS["max_section_id_length"]:
        raise CandidateValidationError("Sections require a non-empty ID")
    if not isinstance(section.get("title"), str) or not section["title"].strip() or len(section["title"]) > LIMITS["max_section_title_length"]:
        raise CandidateValidationError("Sections require a non-empty title")

    _validate_nested_limits(section.get("data"))
    data = section.get("data")
    if section_type == "profile":
        if not isinstance(data, dict):
            raise CandidateValidationError("Profile sections require object data")
        _validate_rich_text_fields(data)
        return
    if section_type not in ENTRY_SECTION_TYPES or not isinstance(data, list):
        raise CandidateValidationError("Entry-based sections require list data")
    ids: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            raise CandidateValidationError("Section entries must be objects")
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id.strip() or row_id in ids:
            raise CandidateValidationError("Section entry IDs must be unique and non-empty")
        ids.add(row_id)
        _validate_rich_text_fields(row)
        if section_type == "extras":
            fields = row.get("fields", [])
            if not isinstance(fields, list):
                raise CandidateValidationError("Extras entries require a fields list")
            for field in fields:
                if not isinstance(field, dict) or not isinstance(field.get("label"), str) or "value" not in field:
                    raise CandidateValidationError("Extras fields require labels and values")


__all__ = ["CandidateValidationError", "validate_section_payload"]
