import uuid as uuid_module
import re
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.template import TemplateListItem, TemplateDetail, UserTemplateCreate
from app.schemas.manifest import Manifest
from app.core.deps import get_current_user, get_optional_current_user

router = APIRouter()

# Known zone placeholder names (common CSS layout zones)
ZONE_KNOWN = {"header", "main", "sidebar", "left", "right", "center",
              "col", "panel", "zone", "area", "top", "bottom", "nav",
              "footer", "aside", "primary", "secondary"}

ALL_SECTIONS = ["profile", "experience", "education", "skills",
                "projects", "languages", "certifications"]


def generate_layout_config(layout_template: str) -> dict:
    """Generate layout_config from template HTML zone placeholders.

    Scans the template for {{zone_id}} patterns and creates a proper
    layout_config with zones and placement.
    """
    matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', layout_template)
    zone_placeholders = set(matches)

    # Filter to known zone names (exclude data variables like {{name}})
    zones = [z for z in zone_placeholders if z in ZONE_KNOWN or "-" in z]

    if not zones:
        zones = ["main"]

    zone_objects = [{"id": z, "row": 0, "styles": {"width": "100%"}} for z in zones]
    placement = {}
    for section in ALL_SECTIONS:
        placement[section] = zones[0]  # default to first zone

    return {"zones": zone_objects, "placement": placement}


def manifest_to_layout_config(manifest: Manifest) -> dict:
    """Convert manifest zones and placement to layout_config."""
    zones = []
    for zone in manifest.zones:
        zone_dict = {
            "id": zone.id,
            "row": zone.row,
            "styles": zone.styles.model_dump(exclude_none=True, by_alias=True)
        }
        zones.append(zone_dict)
    placement = manifest.placement
    row_heights = {}
    # rowHeights not used in new system, but keep if present
    # Could be added later if needed
    return {"zones": zones, "placement": placement, "rowHeights": row_heights}


def manifest_to_layout_template(manifest: Manifest) -> str:
    """Generate a full HTML document template from manifest."""
    zones = manifest.zones
    if not zones:
        raise ValueError("Manifest must have at least one zone")
    # Group zones by row
    rows: dict[int, list] = {}
    for zone in zones:
        r = zone.row
        if r not in rows:
            rows[r] = []
        rows[r].append(zone)
    sorted_rows = sorted(rows.items())

    body_content = ""
    for row_num, row_zones in sorted_rows:
        body_content += '  <div style="display:flex;flex:1 0 auto;">\n'
        for zone in row_zones:
            body_content += f'    {{{{{zone.id}}}}}\n'
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


@router.get("", response_model=list[TemplateListItem])
async def list_templates(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Template).order_by(Template.name)
    if current_user:
        query = query.where((Template.user_id == current_user.id) | (Template.user_id.is_(None)))
    result = await db.execute(query)
    templates = result.scalars().all()
    return [TemplateListItem.model_validate(t) for t in templates]


@router.get("/user", response_model=list[TemplateListItem])
async def list_user_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Template).where(Template.user_id == current_user.id).order_by(Template.name)
    result = await db.execute(query)
    return [TemplateListItem.model_validate(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=TemplateDetail)
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return TemplateDetail.model_validate(template)


@router.get("/{template_id}/manifest", response_model=dict)
async def get_template_manifest(template_id: str, db: AsyncSession = Depends(get_db)):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template.manifest or {}


@router.get("/{template_id}/html", response_class=PlainTextResponse)
async def get_template_html(template_id: str, db: AsyncSession = Depends(get_db)):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template.layout_template or ""


@router.post("", response_model=TemplateDetail)
async def create_template_from_manifest(
    manifest_json: str = Form(...),
    template_html: Optional[UploadFile] = File(None),
    styles_css: Optional[UploadFile] = File(None),
    assets: Optional[list[UploadFile]] = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a template from a manifest.json (multipart)."""
    try:
        manifest_data = json.loads(manifest_json)
        manifest = Manifest(**manifest_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid manifest: {e}")

    # Generate layout_config and layout_template from manifest if not provided via files
    layout_config = manifest_to_layout_config(manifest)
    layout_template = manifest_to_layout_template(manifest)

    # If user uploaded custom HTML/CSS, use them (optional)
    if template_html:
        content = await template_html.read()
        layout_template = content.decode("utf-8")
    if styles_css:
        # Could embed CSS into layout_template or store separately; for now ignore
        pass

    # Assets handling: store asset mapping
    asset_map = {}
    if assets:
        for asset in assets:
            # For simplicity, store filename -> content (in real app, save to storage)
            asset_content = await asset.read()
            asset_map[asset.filename] = asset_content.decode("utf-8", errors="ignore")

    base_id = f"user_{current_user.id}_{manifest.name.lower().replace(' ', '_')}"
    if len(base_id) > 90:
        base_id = base_id[:90]
    template_id = base_id
    result = await db.execute(select(Template).where(Template.id == template_id))
    existing = result.scalar_one_or_none()
    if existing:
        template_id = f"{base_id}_{uuid_module.uuid4().hex[:8]}"

    template = Template(
        id=template_id,
        name=manifest.name,
        description=manifest.description,
        preview_image_url=None,
        layout_config=layout_config,
        section_schema=manifest.section_schema,
        default_customizations={var.key: var.default for var in manifest.global_style_schema},
        is_system=False,
        content=None,
        layout_template=layout_template,
        manifest=manifest.model_dump(),
        assets=asset_map,
        user_id=current_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateDetail.model_validate(template)


@router.post("/user", response_model=TemplateDetail)
async def create_user_template(
    data: UserTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_id = f"user_{current_user.id}_{data.name.lower().replace(' ', '_')}"
    if len(base_id) > 90:
        base_id = base_id[:90]
    template_id = base_id
    result = await db.execute(select(Template).where(Template.id == template_id))
    existing = result.scalar_one_or_none()
    if existing:
        template_id = f"{base_id}_{uuid_module.uuid4().hex[:8]}"

    template = Template(
        id=template_id,
        name=data.name,
        description=data.description or f"User template: {data.name}",
        preview_image_url=None,
        layout_config=data.layout_config or generate_layout_config(data.layout_template) or {},
        section_schema=data.section_schema or {},
        default_customizations=data.default_customizations,
        is_system=False,
        content=None,
        layout_template=data.layout_template,
        user_id=current_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateDetail.model_validate(template)


@router.delete("/user/{template_id}")
async def delete_user_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    if template.is_system or template.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this template")
    await db.delete(template)
    await db.commit()
    return None
