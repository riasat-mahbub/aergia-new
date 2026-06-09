from sqlalchemy.ext.asyncio import AsyncSession
from app.models.template import Template


def build_manifest(template: dict) -> dict:
    """Construct a manifest dict from the seed template data."""
    layout_config = template["layout_config"]
    customizations = template.get("default_customizations", {})
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})

    # Build global style schema from default_customizations
    global_style_schema = []
    for key, default in colors.items():
        global_style_schema.append({
            "key": key,
            "type": "color",
            "label": key.replace("_", " ").title(),
            "default": default
        })
    for key, default in fonts.items():
        global_style_schema.append({
            "key": key,
            "type": "font",
            "label": key.replace("_", " ").title(),
            "default": default
        })
    for key, default in spacing.items():
        global_style_schema.append({
            "key": key,
            "type": "length",
            "label": key.replace("_", " ").title(),
            "default": default
        })
    # Schema buckets must mirror the keys used in default_customizations (`spacing`).
    # Re-key `length` entries into `spacing` so `_build_css_vars` picks them up.
    manifest = {
        "version": 1,
        "id": template["id"],
        "name": template["name"],
        "description": template.get("description"),
        "layout_config": layout_config,
        "zones": layout_config.get("zones", []),
        "placement": layout_config.get("placement", {}),
        "globalStyleSchema": global_style_schema,
        "assets": {},
        "sectionSchema": template.get("section_schema", {}),
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
                {"id": "main", "styles": {"width": "70%", "padding": "24px"}}
            ],
            "placement": {
                "profile": "sidebar",
                "experience": "main",
                "education": "main",
                "skills": "main",
                "projects": "main",
                "languages": "main",
                "certifications": "main"
            }
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "phone", "location", "summary", "photo_url"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "location", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "gpa", "summary"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "link_text", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date", "credential_url"]},
        },
        "default_customizations": {
            "colors": {"accent": "#2563eb", "bg_sidebar": "#f8fafc"},
            "fonts": {"body": "Inter, system-ui, sans-serif", "heading": "Inter, system-ui, sans-serif"},
            "spacing": {"section_gap": "24px", "profile_name_size": "1.75rem"},
        },
    },
    {
        "id": "generic-classic",
        "name": "Classic",
        "description": "Single-column layout with serif fonts and traditional styling",
        "layout_config": {
            "zones": [
                {"id": "main", "styles": {"width": "100%", "padding": "32px"}}
            ],
            "placement": {
                "profile": "main",
                "experience": "main",
                "education": "main",
                "skills": "main",
                "projects": "main",
                "languages": "main",
                "certifications": "main"
            }
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "phone", "location", "summary"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "location", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "gpa", "summary"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "link_text", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date", "credential_url"]},
        },
        "default_customizations": {
            "colors": {"header": "#000000", "divider": "#d1d5db"},
            "fonts": {"body": "Georgia, Crimson, serif", "heading": "Georgia, Crimson, serif"},
            "spacing": {"section_gap": "20px", "profile_name_size": "1.5rem"},
        },
    },
    {
        "id": "generic-minimal",
        "name": "Minimal",
        "description": "Clean single-column layout with grayscale styling and no decoration",
        "layout_config": {
            "zones": [
                {"id": "main", "styles": {"width": "100%", "padding": "32px"}}
            ],
            "placement": {
                "profile": "main",
                "experience": "main",
                "education": "main",
                "skills": "main",
                "projects": "main",
                "languages": "main",
                "certifications": "main"
            }
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "phone", "location"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "summary"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "link_text", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date"]},
        },
        "default_customizations": {
            "colors": {"text": "#374151", "heading": "#111827"},
            "fonts": {"body": "system-ui, sans-serif", "heading": "system-ui, sans-serif"},
            "spacing": {"section_gap": "16px", "profile_name_size": "1.25rem"},
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
    await db.commit()
