import uuid as uuid_module
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.template import TemplateListItem, TemplateDetail, UserTemplateCreate
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
        description=f"User template: {data.name}",
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
