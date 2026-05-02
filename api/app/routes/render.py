"""Template rendering endpoint for the new IR-based renderer."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.core.deps import get_current_user
from app.services.renderer import render_html

router = APIRouter(prefix="/render", tags=["render"])


class RenderRequest(BaseModel):
    manifest: dict[str, Any]
    cv_data: dict[str, Any]
    customizations: dict[str, Any]


@router.post("/html")
async def render_template_html(
    request: RenderRequest,
    current_user: User = Depends(get_current_user),
):
    """Render a template to HTML using the new IR-based renderer."""
    try:
        html = render_html(
            manifest=request.manifest,
            cv_data=request.cv_data,
            customizations=request.customizations,
        )
        return {"html": html}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))