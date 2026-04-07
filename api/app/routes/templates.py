from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.template import TemplateListItem, TemplateDetail, UserTemplateCreate
from app.core.deps import get_current_user, get_optional_current_user

router = APIRouter()


@router.get("", response_model=list[TemplateListItem])
async def list_templates(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Template).order_by(Template.name)
    if current_user:
        query = query.union_all(
            select(Template).where(Template.user_id == current_user.id).order_by(Template.name)
        )
    result = await db.execute(query)
    templates = result.scalars().all()
    return [TemplateListItem.model_validate(t) for t in templates]


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
    template = Template(
        id=f"user_{current_user.id}_{data.name.lower().replace(' ', '_')}",
        name=data.name,
        description=f"User template: {data.name}",
        preview_image_url=None,
        layout_config={},
        section_schema={},
        default_customizations=None,
        is_system=False,
        content=data.content,
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
