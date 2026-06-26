"""Seed templates for the v2 manifest pipeline.

Each template declares a v2 :class:`TemplateManifest` directly, using the
closed design vocabulary:

- ``zones[].styles.width`` is a :data:`WidthToken` (``narrow | half | full | auto``).
- ``zones[].styles.background`` is a color ref (hex literal or palette name).
- ``zones[].styles.padding`` is a :data:`SpacingToken`.
- ``global_styles.accent_color`` is a color ref; ``body_font`` and
  ``heading_font`` are :data:`FontToken` enums.
- ``layout_defaults.spacing`` is the legacy v2 enum
  (``compact | comfortable | minimal``).

The manifest never carries raw CSS strings; the resolver maps each token
to the renderer's native value. The three seeds ship the token values
that match the design intent (modern = two-column with a narrow sidebar,
classic = single column with compact spacing, minimal = single column
with minimal spacing).

The seed writes ``manifest`` only. The legacy ``default_customizations``
column is no longer populated; the editor reads the manifest directly.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template
from app.schema.models import TemplateManifest


# These seeds are the canonical reference for the design vocabulary.
# Each value is a token; no raw CSS strings.
SEED_TEMPLATES = [
    {
        "id": "generic-modern",
        "name": "Modern",
        "description": "Two-column layout with a narrow sidebar and a wide main column.",
        "manifest": {
            "manifest_version": 2,
            "id": "generic-modern",
            "name": "Modern",
            "description": "Two-column layout with a narrow sidebar and a wide main column.",
            "zones": [
                {
                    "id": "sidebar",
                    "label": None,
                    "styles": {
                        "width": "narrow",
                        "background": "palette.surface-2",
                        "padding": "comfortable",
                    },
                },
                {
                    "id": "main",
                    "label": None,
                    "styles": {
                        "width": "full",
                        "padding": "comfortable",
                    },
                },
            ],
            "placement": {
                "profile": "sidebar",
                "experience": "main",
                "education": "main",
                "skills": "main",
                "projects": "main",
                "languages": "main",
                "certifications": "main",
                "research": "main",
            },
            "layout_defaults": {"spacing": "comfortable"},
            "policy_overrides": {"by_type": {}},
            "global_styles": {
                "accent_color": "#2563eb",
                "body_font": "sans-serif",
                "heading_font": "sans-serif",
            },
        },
    },
    {
        "id": "generic-classic",
        "name": "Classic",
        "description": "Single-column layout with serif fonts and compact spacing.",
        "manifest": {
            "manifest_version": 2,
            "id": "generic-classic",
            "name": "Classic",
            "description": "Single-column layout with serif fonts and compact spacing.",
            "zones": [
                {
                    "id": "main",
                    "label": None,
                    "styles": {
                        "width": "full",
                        "padding": "comfortable",
                    },
                },
            ],
            "placement": {
                "profile": "main",
                "experience": "main",
                "education": "main",
                "skills": "main",
                "projects": "main",
                "languages": "main",
                "certifications": "main",
                "research": "main",
            },
            "layout_defaults": {"spacing": "compact"},
            "policy_overrides": {"by_type": {}},
            "global_styles": {
                "accent_color": "#000000",
                "body_font": "serif",
                "heading_font": "serif",
            },
        },
    },
    {
        "id": "generic-minimal",
        "name": "Minimal",
        "description": "Single-column layout with minimal spacing and neutral palette.",
        "manifest": {
            "manifest_version": 2,
            "id": "generic-minimal",
            "name": "Minimal",
            "description": "Single-column layout with minimal spacing and neutral palette.",
            "zones": [
                {
                    "id": "main",
                    "label": None,
                    "styles": {
                        "width": "full",
                        "padding": "loose",
                    },
                },
            ],
            "placement": {
                "profile": "main",
                "experience": "main",
                "education": "main",
                "skills": "main",
                "projects": "main",
                "languages": "main",
                "certifications": "main",
                "research": "main",
            },
            "layout_defaults": {"spacing": "minimal"},
            "policy_overrides": {"by_type": {}},
            "global_styles": {
                "accent_color": "#111827",
                "body_font": "sans-serif",
                "heading_font": "sans-serif",
            },
        },
    },
]


async def seed_templates(db: AsyncSession) -> None:
    for data in SEED_TEMPLATES:
        manifest = TemplateManifest.model_validate(data["manifest"])
        existing = await db.get(Template, data["id"])
        if existing is None:
            db.add(Template(
                id=data["id"],
                name=data["name"],
                description=data.get("description"),
                is_system=True,
                manifest=manifest.model_dump(),
            ))
        else:
            existing.manifest = manifest.model_dump()
            existing.default_customizations = None
    await db.commit()
