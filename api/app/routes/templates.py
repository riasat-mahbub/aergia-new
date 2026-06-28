"""Template routes — list, retrieve, create, delete templates.

The multipart upload endpoint validates against the v2
:class:`TemplateManifest` schema. Legacy ``layout_config`` /
``globalStyleSchema`` fields are gone.
"""

from __future__ import annotations

import uuid as uuid_module
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.schema.models import TemplateManifest
from app.schema.models import TemplateListItem, TemplateDetail, UserTemplateCreate
from app.core.deps import get_current_user, get_optional_current_user


NOT_FOUND = "Template not found"

router = APIRouter()


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return TemplateDetail.model_validate(template)


@router.get("/{template_id}/manifest", response_model=dict)
async def get_template_manifest(template_id: str, db: AsyncSession = Depends(get_db)):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return template.manifest or {}


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
        manifest = TemplateManifest.model_validate(manifest_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid manifest: {e}")

    if template_html:
        content = await template_html.read()
        _ = content.decode("utf-8")  # validated for future use
    if styles_css:
        pass

    asset_map = {}
    if assets:
        for asset in assets:
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
        manifest=manifest.model_dump(),
        default_customizations=None,
        is_system=False,
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
        description=data.description or data.manifest.description or f"User template: {data.name}",
        preview_image_url=None,
        manifest=data.manifest.model_dump(),
        default_customizations=None,
        is_system=False,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    if template.is_system or template.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this template")
    await db.delete(template)
    await db.commit()
    return None


