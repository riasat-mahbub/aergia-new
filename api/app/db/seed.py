from sqlalchemy.ext.asyncio import AsyncSession
from app.models.template import Template
import json


def generate_layout_template(layout_config: dict) -> str:
    """Generate a full HTML document template from layout_config.
    
    Mirrors the logic in web/src/lib/sections/templateHtml.ts
    """
    zones = layout_config.get("zones", [])
    row_heights = layout_config.get("rowHeights", {})
    
    # Group zones by row
    rows: dict[int, list[dict]] = {}
    for zone in zones:
        r = zone.get("row", 0)
        if r not in rows:
            rows[r] = []
        rows[r].append(zone)
    
    sorted_rows = sorted(rows.items())
    
    body_content = ""
    for row_num, row_zones in sorted_rows:
        row_height = row_heights.get(str(row_num)) or row_heights.get(row_num)
        if row_height:
            try:
                pct = int(str(row_height).replace("%", ""))
                if pct > 0:
                    flex_val = f"{pct} 0 0%"
                else:
                    flex_val = "1 0 auto"
            except (ValueError, AttributeError):
                flex_val = "1 0 auto"
        else:
            flex_val = "1 0 auto"
        
        body_content += f'  <div style="display:flex;flex:{flex_val};">\n'
        for zone in row_zones:
            body_content += f'    {{{{{zone["id"]}}}}}\n'
        body_content += '  </div>\n'
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: {{body_font}};
      color: var(--text, #374151);
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: {{heading_font}};
      color: var(--heading, #111827);
    }}
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
{body_content}</div>
</body>
</html>'''


def build_manifest(template: dict) -> dict:
    """Construct a manifest dict from the seed template data."""
    layout_config = template["layout_config"]
    customizations = template.get("default_customizations", {})
    colors = customizations.get("colors", {})
    fonts = customizations.get("fonts", {})
    spacing = customizations.get("spacing", {})
    
    # Build global style schema from default_customizations
    global_style_schema = []
    # Colors
    for key, default in colors.items():
        global_style_schema.append({
            "key": key,
            "type": "color",
            "label": key.replace("_", " ").title(),
            "default": default
        })
    # Fonts
    for key, default in fonts.items():
        global_style_schema.append({
            "key": key,
            "type": "font",
            "label": key.replace("_", " ").title(),
            "default": default
        })
    # Spacing
    for key, default in spacing.items():
        global_style_schema.append({
            "key": key,
            "type": "length",
            "label": key.replace("_", " ").title(),
            "default": default
        })
    
    manifest = {
        "version": 1,
        "id": template["id"],
        "name": template["name"],
        "description": template.get("description"),
        "layout_config": layout_config,
        "zones": layout_config.get("zones", []),
        "placement": layout_config.get("placement", {}),
        "rowHeights": layout_config.get("rowHeights", {}),
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
                {"id": "sidebar", "row": 0, "styles": {"width": "30%", "background-color": "#f8fafc", "padding": "24px"}},
                {"id": "main", "row": 0, "styles": {"width": "70%", "padding": "24px"}}
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
            "zones": [
                {"id": "main", "row": 0, "styles": {"width": "100%", "padding": "32px"}}
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
            "zones": [
                {"id": "main", "row": 0, "styles": {"width": "100%", "padding": "32px"}}
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

# Add layout_template and manifest to each seed template
for template in SEED_TEMPLATES:
    template["layout_template"] = generate_layout_template(template["layout_config"])
    template["manifest"] = build_manifest(template)
    template["assets"] = {}


async def seed_templates(db: AsyncSession) -> None:
    for data in SEED_TEMPLATES:
        existing = await db.get(Template, data["id"])
        if existing is None:
            db.add(Template(**data))
        elif existing.manifest is None:
            existing.manifest = data["manifest"]
    await db.commit()