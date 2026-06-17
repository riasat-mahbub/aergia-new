"""Seed templates for the new v2 manifest pipeline.

Each template declares:

- ``manifest_version: 2``
- ``zones`` — layout zones with explicit CSS-level styles.
- ``placement`` — section_type → zone_id.
- ``layout_defaults.spacing`` — design-token preference (compact / comfortable / minimal).
- ``policy_overrides.by_type`` — per-type policy overrides (empty for the seed).
- ``global_styles`` — accent color and body/heading fonts.

The legacy ``layout_config`` / ``globalStyleSchema`` fields are gone.
User-uploaded templates must use the same shape.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template


def _spacing_preset_for(section_gap: str) -> str:
    """Map the legacy ``section_gap`` CSS string to a v2 spacing preset."""

    if section_gap in {"16px", "20px"}:
        return "compact"
    if section_gap == "8px":
        return "minimal"
    return "comfortable"


def build_manifest(template: dict) -> dict:
    """Construct a v2 manifest dict from the seed template data."""

    layout_config = template["layout_config"]
    customizations = template.get("default_customizations", {})
    colors = customizations.get("colors") or {}
    fonts = customizations.get("fonts") or {}
    spacing = (customizations.get("spacing") or {}).get("section_gap", "24px")
    spacing_preset = _spacing_preset_for(spacing)

    zones = []
    for zone in layout_config.get("zones", []):
        styles = dict(zone.get("styles") or {})
        # Normalize the hyphenated background-color key for ZoneStyle.
        if "background-color" in styles and "background_color" not in styles:
            styles["background_color"] = styles.pop("background-color")
        zones.append({
            "id": zone["id"],
            "label": zone.get("label"),
            "styles": styles,
        })

    placement = layout_config.get("placement") or {}
    global_styles: dict[str, str] = {}
    if colors.get("accent"):
        global_styles["accent_color"] = colors["accent"]
    elif colors.get("header"):
        global_styles["accent_color"] = colors["header"]
    elif colors.get("heading"):
        global_styles["accent_color"] = colors["heading"]
    elif colors.get("text"):
        global_styles["accent_color"] = colors["text"]
    if fonts.get("body"):
        global_styles["body_font"] = fonts["body"]
    if fonts.get("heading"):
        global_styles["heading_font"] = fonts["heading"]
    if colors.get("bg_sidebar"):
        global_styles["bg_sidebar"] = colors["bg_sidebar"]
    if colors.get("divider"):
        global_styles["divider"] = colors["divider"]

    manifest = {
        "manifest_version": 2,
        "id": template["id"],
        "name": template["name"],
        "description": template.get("description"),
        "zones": zones,
        "placement": placement,
        "layout_defaults": {"spacing": spacing_preset},
        "policy_overrides": {"by_type": {}},
        "global_styles": global_styles,
    }
    return manifest


SEED_TEMPLATES = [
    {
        "id": "generic-modern",
        "name": "Modern",
        "description": "Two-column layout with accent color header and light sidebar",
        "layout_config": {
            "zones": [
                {"id": "sidebar", "styles": {"width": "30%", "background-color": "#f8fafc", "padding": "24px"}},
                {"id": "main", "styles": {"width": "70%", "padding": "24px"}},
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
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "email_link", "phone", "location", "site_text", "site_url", "summary", "photo_url"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "location", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "gpa", "summary"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "link_text", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date", "credential_url"]},
            "research": {"fields": ["title", "paper_url", "paper_link_text", "description", "publication_date"]},
        },
        "default_customizations": {
            "colors": {"accent": "#2563eb", "bg_sidebar": "#f8fafc"},
            "fonts": {"body": "Inter, system-ui, sans-serif", "heading": "Inter, system-ui, sans-serif"},
            "spacing": {"section_gap": "24px", "subsection_gap": "16px"},
            "flags": {"underline_section_titles": False, "default_link_style": False},
        },
    },
    {
        "id": "generic-classic",
        "name": "Classic",
        "description": "Single-column layout with serif fonts and traditional styling",
        "layout_config": {
            "zones": [
                {"id": "main", "styles": {"width": "100%", "padding": "32px"}},
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
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "email_link", "phone", "location", "site_text", "site_url", "summary"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "location", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "gpa", "summary"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "link_text", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date", "credential_url"]},
            "research": {"fields": ["title", "paper_url", "paper_link_text", "description", "publication_date"]},
        },
        "default_customizations": {
            "colors": {"header": "#000000", "divider": "#d1d5db"},
            "fonts": {"body": "Georgia, Crimson, serif", "heading": "Georgia, Crimson, serif"},
            "spacing": {"section_gap": "20px", "subsection_gap": "12px"},
            "flags": {"underline_section_titles": False, "default_link_style": False},
        },
    },
    {
        "id": "generic-minimal",
        "name": "Minimal",
        "layout_config": {
            "zones": [
                {"id": "main", "styles": {"width": "100%", "padding": "32px"}},
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
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "email_link", "phone", "location", "site_text", "site_url"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "summary"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "link_text", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date"]},
            "research": {"fields": ["title", "paper_url", "paper_link_text", "description", "publication_date"]},
        },
        "default_customizations": {
            "colors": {"text": "#374151", "heading": "#111827"},
            "fonts": {"body": "system-ui, sans-serif", "heading": "system-ui, sans-serif"},
            "spacing": {"section_gap": "8px", "subsection_gap": "8px"},
            "flags": {"underline_section_titles": False, "default_link_style": False},
        },
    },
]


# Pre-compute manifests for each seed template
for t in SEED_TEMPLATES:
    t["manifest"] = build_manifest(t)


async def seed_templates(db: AsyncSession) -> None:
    for data in SEED_TEMPLATES:
        existing = await db.get(Template, data["id"])
        if existing is None:
            db.add(Template(
                id=data["id"],
                name=data["name"],
                description=data.get("description"),
                is_system=True,
                manifest=data["manifest"],
                default_customizations=data.get("default_customizations"),
            ))
        elif existing.manifest is None:
            existing.manifest = data["manifest"]
        else:
            existing.manifest = data["manifest"]
            existing.default_customizations = data.get("default_customizations")
    await db.commit()
