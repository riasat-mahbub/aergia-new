from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.cv import CVCreate, CVUpdate, CVResponse, CVListItem
from fastapi.responses import StreamingResponse

from app.services.cv import CVService
from app.services.pdf import PDFService
from app.services.renderer import render_preview
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("", response_model=list[CVListItem])
async def list_cvs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cvs = await service.list_cvs(current_user.id)
    return [CVListItem.model_validate(cv) for cv in cvs]


@router.post("", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def create_cv(
    data: CVCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cv = await service.create_cv(current_user.id, data)
    return CVResponse.model_validate(cv)


@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cv = await service.get_cv(cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return CVResponse.model_validate(cv)


@router.patch("/{cv_id}", response_model=CVResponse)
async def update_cv(
    cv_id: str,
    data: CVUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cv = await service.update_cv(cv_id, current_user.id, data)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return CVResponse.model_validate(cv)


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    deleted = await service.delete_cv(cv_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return None


@router.post("/{cv_id}/copy", response_model=CVResponse)
async def copy_cv(
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    new_cv = await service.copy_cv(cv_id, current_user.id)
    if not new_cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")
    return CVResponse.model_validate(new_cv)


@router.get("/{cv_id}/preview")
async def preview_cv(
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cv = await service.get_cv(cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found")

    instances = cv.sections or []
    if isinstance(instances, dict):
        instances = []
    html = render_preview(
        instances=instances,
        customizations=cv.customizations or {},
        template_id=cv.template_id,
    )
    return {"html": html}


@router.post("/{cv_id}/export/pdf")
async def export_cv_pdf(
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PDFService(db)
    try:
        pdf_bytes = await service.export_pdf(cv_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cv-{cv_id}.pdf"'},
    )
