from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.cv import CVCreate, CVUpdate, CVResponse, CVListItem
from fastapi.responses import StreamingResponse

from app.services.cv import CVService
from app.services.pdf import PDFService
from app.services.renderer import HTMLDocumentRenderer, build_document, resolve
from app.services.renderer._pdf_runtime import html_to_pdf
from app.routes.render import strip_anchor_hrefs
from app.core.deps import get_current_user
from app.models.user import User
from app.services.cv import coerce_customizations, CVService

NOT_FOUND = "CV not found"

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)

    instances = cv.sections or []
    if isinstance(instances, dict):
        instances = []

    template_data = await service.get_template_data(cv.template_id)

    manifest = (template_data or {}).get("manifest", {})
    layout_config = manifest.get("layout_config") if manifest else None
    cv_layout = (cv.customizations or {}).get("layout")
    if isinstance(cv_layout, dict) and cv_layout.get("zones"):
        layout_config = cv_layout

    from app.schema.models import Customizations, SectionInstance, TemplateManifest

    document = build_document(cv, None)
    try:
        manifest_model = TemplateManifest.model_validate(manifest)
    except Exception:
        manifest_model = None
    customizations_model = coerce_customizations(cv.customizations)
    model = resolve(document, manifest_model, customizations_model, HTMLDocumentRenderer.support)
    html = HTMLDocumentRenderer().render(model)
    # Preview is rendered inside a sandboxed iframe. Without stripping hrefs,
    # clicking a project / credential / site link navigates the iframe away
    # from the CV preview. Strip hrefs so the user sees the link text but
    # cannot accidentally navigate while editing.
    html = strip_anchor_hrefs(html)
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
