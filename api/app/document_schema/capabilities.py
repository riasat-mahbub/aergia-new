"""Machine-readable authoring capabilities for the document pipeline.

The tailoring protocol used to repeat section names, field policies, style
tokens, and size limits in several Python and JavaScript modules.  This module
is intentionally close to :mod:`app.document_schema.models`: it is the single
descriptor exported to clients which need to author a document (the web
editor, the local tailoring skill, and future integrations).

The descriptor has two layers:

* ``document`` describes the wire shape and the renderer-backed section
  fields; and
* ``tailoring`` describes which edits are safe for an untrusted agent.

The server still validates the resulting document.  The descriptor is a
contract for clients, not an authorization boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.document_schema.models import (
    AlignmentToken,
    FontSizeToken,
    FontToken,
    SAFE_FONT_FAMILY_VALUES,
    SpacingToken,
    SectionInstance,
)
from app.services.renderer.builders import BUILDERS
from app.services.renderer.support import RendererSupport
from app.services.rich_text import RICH_TEXT_FIELDS_BY_SECTION


# These names are the fields consumed by the renderer builders.  Keeping the
# table here makes the tailoring policy and the evidence packet share one
# source, while the actual field constraints remain generated from the
# Pydantic wire schema below.
SECTION_FIELDS: dict[str, dict[str, str]] = {
    "profile": {
        "name": "string",
        "title": "string",
        "email": "string",
        "email_link": "boolean",
        "phone": "string",
        "location": "string",
        "site_text": "string",
        "site_url": "url",
        "summary": "rich_text",
        "photo_url": "url",
        "social_links": "social_links",
    },
    "experience": {
        "id": "id",
        "position": "string",
        "company": "string",
        "location": "string",
        "start_date": "date",
        "end_date": "date",
        "current": "boolean",
        "description": "rich_text",
    },
    "education": {
        "id": "id",
        "degree": "string",
        "institution": "string",
        "start_date": "date",
        "end_date": "date",
        "current": "boolean",
        "gpa": "string",
        "summary": "rich_text",
    },
    "skills": {
        "id": "id",
        "category": "string",
        "items": "string[]",
    },
    "projects": {
        "id": "id",
        "name": "string",
        "url": "url",
        "link_text": "string",
        "start_date": "date",
        "end_date": "date",
        "description": "rich_text",
        "tech_stack": "string[]",
    },
    "languages": {
        "id": "id",
        "language": "string",
        "proficiency": "string",
    },
    "certifications": {
        "id": "id",
        "name": "string",
        "date": "date",
        "issuer": "string",
        "credential_url": "url",
        "link_text": "string",
    },
    "research": {
        "id": "id",
        "title": "string",
        "publication_date": "date",
        "publication_value": "string",
        "paper_url": "url",
        "paper_link_text": "string",
        "description": "rich_text",
    },
    "extras": {
        "id": "id",
        "title": "string",
        "fields": "label_value[]",
    },
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

# The server advertises the complete protocol operation set in the same
# descriptor used by the skill.  Keeping it here avoids a second capability
# table in the tailoring service.
TAILORING_OPERATIONS: tuple[str, ...] = (
    "replace_description",
    "replace_rich_text",
    "rewrite_rich_text",
    "remove_bullet",
    "reorder_bullets",
    "remove_entry",
    "reorder_entries",
    "add_library_entry",
    "create_section",
    "replace_section",
    "remove_section",
    "reorder_sections",
    "replace_candidate",
    "report_gap",
)

# The builder registry is the renderer's authoritative dispatch set.  The
# Library mapping covers reusable entry kinds; ``extras`` is the renderer's
# generic entry section and therefore does not need a Library kind.
RENDERABLE_SECTION_TYPES = frozenset(BUILDERS)
ENTRY_SECTION_TYPES = frozenset(RENDERABLE_SECTION_TYPES - {"profile"})

# Keep future renderer additions explicit: a builder without a field
# descriptor would otherwise be silently unavailable to tailoring agents.
if RENDERABLE_SECTION_TYPES != frozenset(SECTION_FIELDS):
    missing = sorted(RENDERABLE_SECTION_TYPES - set(SECTION_FIELDS))
    stale = sorted(set(SECTION_FIELDS) - RENDERABLE_SECTION_TYPES)
    raise RuntimeError(
        "Renderer capability fields are out of sync "
        f"(missing={missing!r}, stale={stale!r})"
    )

# Structured identity facts may be copied only when the source evidence is
# cited.  Prose fields are deliberately absent; they can be rewritten as
# truthful paraphrases by a candidate author.
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
    "experience": frozenset({"id", "company", "position", "start_date", "end_date", "current", "location"}),
    "education": frozenset({"id", "institution", "degree", "start_date", "end_date", "current", "gpa"}),
    "skills": frozenset({"id", "category", "items"}),
    "projects": frozenset({"id", "name", "url", "link_text", "start_date", "end_date", "tech_stack"}),
    "languages": frozenset({"id", "language", "proficiency"}),
    "certifications": frozenset({"id", "name", "issuer", "date", "credential_url", "link_text"}),
    "research": frozenset({"id", "title", "paper_url", "paper_link_text", "publication_date", "publication_value"}),
    # Extras are user-defined; their values still pass the generic fact guard.
    "extras": frozenset({"*"}),
}

# Reuse the normalizer's allowlist so a newly supported rich-text field cannot
# silently diverge from tailoring's editable-field policy.
EDITABLE_RICH_TEXT_FIELDS = RICH_TEXT_FIELDS_BY_SECTION


STYLE_CAPABILITIES: dict[str, Any] = {
    "text": {
        "fields": {
            "bold": "boolean",
            "italic": "boolean",
            "underline": "boolean",
            "strike": "boolean",
            "color": "color_ref",
            "link": "url",
            "font_size": list(FontSizeToken.__args__),
        },
        "max_fields": 100,
    },
    "subsection": {
        "fields": {
            "text_align": list(AlignmentToken.__args__),
            "spacing_before": {"type": "spacing_token", "values": list(SpacingToken.__args__)},
            "spacing_after": {"type": "spacing_token", "values": list(SpacingToken.__args__)},
            "entry_gap": {"type": "spacing_token", "values": list(SpacingToken.__args__)},
            "field_gap": {"type": "spacing_token", "values": list(SpacingToken.__args__)},
            "background_color": "color_ref",
            "section_color": "color_ref",
            "accent_color": "color_ref",
        }
    },
    "layout": {
        "fields": {
            "font_family": {
                "tokens": list(FontToken.__args__),
                "safe_stacks": list(SAFE_FONT_FAMILY_VALUES),
            },
            "date_style": "date_style",
            "break_before": "boolean",
            "keep_together": "boolean",
            "heading_keeps_with_first": "boolean",
            "orphans": "integer",
            "widows": "integer",
            "chip_keys": "string[]",
        },
        "max_chip_keys": 32,
    },
    "typography": {
        "roles": ["heading", "body"],
        "fields": {
            "font_family": list(FontToken.__args__),
            "font_size": list(FontSizeToken.__args__),
            "line_height": ["tight", "normal", "relaxed"],
            "color": "color_ref",
            "bold": "boolean",
        },
    },
    "policy": {
        "fields": {
            "show_title": "boolean",
            "heading_divider": "boolean",
            "skill_variant": ["block", "inline"],
            "entry_layout": ["stack", "two-column"],
        }
    },
    "global": {
        "fields": {
            "accent_color": "color_ref",
            "body_font": list(FontToken.__args__),
            "heading_font": list(FontToken.__args__),
            "default_text_align": list(AlignmentToken.__args__),
            "spacing": ["none", "compact", "comfortable", "minimal"],
        }
    },
}


LIMITS: dict[str, int] = {
    "max_sections": 32,
    "max_section_id_length": 128,
    "max_section_type_length": 64,
    "max_section_title_length": 255,
    "max_section_entries": 100,
    "max_field_text_length": 20_000,
    "max_rich_text_blocks": 100,
    "max_rich_text_items": 100,
    "max_section_style_fields": 100,
    "max_chip_keys": 32,
    "max_zones": 8,
    "max_placement_entries": 64,
}


def _section_descriptor(section_type: str) -> dict[str, Any]:
    fields = SECTION_FIELDS[section_type]
    protected = PROTECTED_FIELDS.get(section_type, frozenset({"*"}))
    editable = EDITABLE_RICH_TEXT_FIELDS.get(section_type, frozenset())
    return {
        "data_shape": "object" if section_type == "profile" else "entries",
        "fields": {
            name: {
                "type": field_type,
                "protected": name in protected or "*" in protected,
                "editable": name in editable,
            }
            for name, field_type in fields.items()
        },
        "max_entries": None if section_type == "profile" else LIMITS["max_section_entries"],
        "allowed_library_kinds": [
            kind for kind, mapped_type in LIBRARY_KIND_TO_SECTION_TYPE.items() if mapped_type == section_type
        ],
        "style_axes": ["text", "subsection", "layout", "typography", "policy"],
    }


def renderer_capabilities(support: RendererSupport | None = None) -> dict[str, Any]:
    """Return a deterministic, JSON-serializable authoring descriptor."""

    support = support or RendererSupport()
    section_types = {
        section_type: _section_descriptor(section_type)
        for section_type in BUILDERS
        if section_type in SECTION_FIELDS
    }
    descriptor: dict[str, Any] = {
        "version": 1,
        "renderer": {
            "id": "html",
            "features": {field: level.value for field, level in vars(support).items()},
        },
        "document": {
            "section_types": section_types,
            "styles": STYLE_CAPABILITIES,
            "limits": LIMITS,
            # The generated schema carries the exact Pydantic constraints;
            # consumers should use this rather than reimplementing limits.
            "wire_schema": SectionInstance.model_json_schema(),
        },
        "tailoring": {
            "renderable_section_types": sorted(RENDERABLE_SECTION_TYPES),
            "entry_section_types": sorted(ENTRY_SECTION_TYPES),
            "library_kind_to_section_type": dict(LIBRARY_KIND_TO_SECTION_TYPE),
            "protected_fields": {
                section_type: sorted(fields) for section_type, fields in PROTECTED_FIELDS.items()
            },
            "editable_rich_text_fields": {
                section_type: sorted(fields) for section_type, fields in EDITABLE_RICH_TEXT_FIELDS.items()
            },
            "operations": list(TAILORING_OPERATIONS),
            "ai_relevance": {
                "rubric_version": "ai-relevance-v1",
                "score_range": [0.0, 1.0],
                "coverage_levels": ["absent", "weak", "partial", "strong", "excellent"],
                "coverage_score_guidance": {
                    "absent": 0.0,
                    "weak": 0.25,
                    "partial": 0.5,
                    "strong": 0.75,
                    "excellent": 1.0,
                },
                "requires_requirement_ids": True,
                "requires_evidence_for_positive_scores": True,
            },
        },
    }
    return descriptor


def capabilities_hash(capabilities: Mapping[str, Any] | None = None) -> str:
    """Hash the canonical descriptor for stale-session detection."""

    value = capabilities if capabilities is not None else renderer_capabilities()
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "EDITABLE_RICH_TEXT_FIELDS",
    "ENTRY_SECTION_TYPES",
    "LIBRARY_KIND_TO_SECTION_TYPE",
    "LIMITS",
    "PROTECTED_FIELDS",
    "RENDERABLE_SECTION_TYPES",
    "SECTION_FIELDS",
    "STYLE_CAPABILITIES",
    "TAILORING_OPERATIONS",
    "capabilities_hash",
    "renderer_capabilities",
]
