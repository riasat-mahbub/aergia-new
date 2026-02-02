from sqlalchemy.ext.asyncio import AsyncSession
from app.models.template import Template

SEED_TEMPLATES = [
    {
        "id": "generic-modern",
        "name": "Modern",
        "description": "Two-column layout with accent color header and light sidebar",
        "layout_config": {
            "columns": 2,
            "widths": [30, 70],
            "margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "phone", "location", "summary", "photo_url"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "location", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "gpa"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date", "credential_url"]},
        },
        "default_customizations": {
            "colors": {"accent": "#2563eb", "bg_sidebar": "#f8fafc"},
            "fonts": {"body": "Inter, system-ui, sans-serif", "heading": "Inter, system-ui, sans-serif"},
            "spacing": {"section_gap": "24px"},
        },
    },
    {
        "id": "generic-classic",
        "name": "Classic",
        "description": "Single-column layout with serif fonts and traditional styling",
        "layout_config": {
            "columns": 1,
            "widths": [100],
            "margins": {"top": 50, "bottom": 50, "left": 60, "right": 60},
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "phone", "location", "summary"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "location", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date", "gpa"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date", "credential_url"]},
        },
        "default_customizations": {
            "colors": {"header": "#000000", "divider": "#d1d5db"},
            "fonts": {"body": "Georgia, Crimson, serif", "heading": "Georgia, Crimson, serif"},
            "spacing": {"section_gap": "20px"},
        },
    },
    {
        "id": "generic-minimal",
        "name": "Minimal",
        "description": "Clean single-column layout with grayscale styling and no decoration",
        "layout_config": {
            "columns": 1,
            "widths": [100],
            "margins": {"top": 40, "bottom": 40, "left": 50, "right": 50},
        },
        "section_schema": {
            "profile": {"fields": ["name", "title", "email", "phone", "location"]},
            "experience": {"fields": ["company", "position", "start_date", "end_date", "current", "description"]},
            "education": {"fields": ["institution", "degree", "start_date", "end_date"]},
            "skills": {"fields": ["category", "items"]},
            "projects": {"fields": ["name", "url", "start_date", "end_date", "description", "tech_stack"]},
            "languages": {"fields": ["language", "proficiency"]},
            "certifications": {"fields": ["name", "issuer", "date"]},
        },
        "default_customizations": {
            "colors": {"text": "#374151", "heading": "#111827"},
            "fonts": {"body": "system-ui, sans-serif", "heading": "system-ui, sans-serif"},
            "spacing": {"section_gap": "16px"},
        },
    },
]


async def seed_templates(db: AsyncSession) -> None:
    for data in SEED_TEMPLATES:
        existing = await db.get(Template, data["id"])
        if existing is None:
            db.add(Template(**data))
    await db.commit()
