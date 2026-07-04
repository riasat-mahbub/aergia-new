"""Template routes — list and retrieve system templates.

Phase 6 step 1 deleted user-template authoring. The list and detail
endpoints return every :class:`Template` row ordered by name; users
pick from the three seed templates (modern, classic, minimal).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.schema.models import TemplateListItem, TemplateDetail
from app.core.deps import get_optional_current_user


NOT_FOUND = "Template not found"

router = APIRouter()


@router.get("", response_model=list[TemplateListItem])
async def list_templates(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Template).order_by(Template.name)
    result = await db.execute(query)
    templates = result.scalars().all()
    return [TemplateListItem.model_validate(t) for t in templates]


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


__all__ = ["router"]
