"""move per-section customizations onto their owning CV sections

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9
Create Date: 2026-09-11 00:00:00.000000

Section styles have one owner after this migration: SectionInstance.style.
When values overlap, the old Customizations.per_section override wins because
that was its position in the renderer cascade.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import json

import sqlalchemy as sa
from alembic import op


revision: str = "k6l7m8n9o0p1"
down_revision: str | None = "j5k6l7m8n9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def merge_per_section_styles(
    sections: object,
    customizations: object,
) -> tuple[list[dict], dict]:
    """Move ID-keyed style overrides into the corresponding section objects."""

    if not isinstance(sections, list) or not all(isinstance(section, dict) for section in sections):
        raise ValueError("cvs.sections must be an array of section objects")
    if not isinstance(customizations, dict):
        raise ValueError("cvs.customizations must be an object")

    migrated_sections = deepcopy(sections)
    migrated_customizations = deepcopy(customizations)
    overrides = migrated_customizations.pop("per_section", {})
    if not isinstance(overrides, dict):
        raise ValueError("customizations.per_section must be an object")

    sections_by_id: dict[str, list[dict]] = {}
    for section in migrated_sections:
        section_id = section.get("id")
        if isinstance(section_id, str):
            sections_by_id.setdefault(section_id, []).append(section)

    for section_id, override in overrides.items():
        if not isinstance(section_id, str) or not isinstance(override, dict):
            raise ValueError("customizations.per_section entries must map section IDs to objects")
        matches = sections_by_id.get(section_id, [])
        if len(matches) > 1:
            raise ValueError(f"CV contains duplicate section ID {section_id!r}")
        if not matches:
            # An override for a removed section has no rendering effect.
            continue
        current = matches[0].get("style")
        if current is None:
            current = {}
        if not isinstance(current, dict):
            raise ValueError(f"section {section_id!r}.style must be an object")
        matches[0]["style"] = _deep_merge(current, override)

    return migrated_sections, migrated_customizations


def _deep_merge(base: dict, override: Mapping) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _decode_json(value: object, *, label: str, default: object) -> object:
    if value is None:
        return deepcopy(default)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} contains invalid JSON") from exc
    return value


def upgrade() -> None:
    bind = op.get_bind()
    table = sa.Table("cvs", sa.MetaData(), autoload_with=bind)
    rows = bind.execute(sa.select(table.c.id, table.c.sections, table.c.customizations)).all()
    for cv_id, raw_sections, raw_customizations in rows:
        sections = _decode_json(raw_sections, label=f"cv {cv_id}.sections", default=[])
        customizations = _decode_json(
            raw_customizations,
            label=f"cv {cv_id}.customizations",
            default={},
        )
        migrated_sections, migrated_customizations = merge_per_section_styles(sections, customizations)
        if migrated_sections == sections and migrated_customizations == customizations:
            continue
        bind.execute(
            sa.update(table)
            .where(table.c.id == cv_id)
            .values(sections=migrated_sections, customizations=migrated_customizations)
        )


def downgrade() -> None:
    # There is no schema object to reverse. Keeping the section-local styles
    # canonical is safe for the previous runtime, whose model accepted both
    # section styles and the now-absent optional override bucket.
    pass


__all__ = ["merge_per_section_styles"]
