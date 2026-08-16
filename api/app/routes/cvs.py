from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.cv import CVCreate, CVUpdate, CVResponse, CVListItem
from app.schemas.library import AddEntryToLibraryResponse, PromoteToLibraryResponse
from app.services.cv import CVService
from app.services.cv import coerce_customizations
from app.services.renderer import HTMLDocumentRenderer, build_document, resolve
from app.routes.render import strip_anchor_hrefs
from app.core.deps import get_current_user
from app.models.user import User
from app.services.cv import coerce_customizations

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

    from app.schema.models import TemplateManifest

    try:
        manifest_model = TemplateManifest.model_validate(manifest)
    except Exception:
        manifest_model = None

    # Pass the manifest through so template policy_overrides apply the same
    # way they do in the live preview (/render/html).
    document = build_document(cv, manifest_model)
    customizations_model = coerce_customizations(cv.customizations)
    renderer = HTMLDocumentRenderer()
    model = resolve(document, renderer, manifest_model, customizations_model)
    html = renderer.render(model)
    # Preview is rendered inside a sandboxed iframe. Neutralize hrefs so the
    # links are visible (with the .f-link arrow) but clicking never navigates
    # the preview away from the CV while editing. The exported PDF keeps the
    # real hrefs and produces clickable links.
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


@router.post("/{cv_id}/promote-to-library", response_model=PromoteToLibraryResponse)
async def promote_cv_to_library(
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Promote a CV's eligible sections into Library entries.

    Colocated with the CV's other routes because it operates on a CV
    as its input. ``profile`` and ``summary`` (and any future
    non-eligible section types) are returned in ``skipped``.
    """
    from app.services.library import LibraryService

    lib_service = LibraryService(db)
    try:
        result = await lib_service.promote_cv_to_library(cv_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return PromoteToLibraryResponse(
        library_id=result.library_id,
        promoted=result.promoted,
        skipped=result.skipped,
    )


@router.post(
    "/{cv_id}/sections/{section_id}/entries/{entry_id}/add-to-library",
    response_model=AddEntryToLibraryResponse,
)
async def add_section_entry_to_library(
    cv_id: str,
    section_id: str,
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Push a single CV section entry into the user's Library.

    Idempotent: re-clicking for the same entry returns the existing
    Library entry's id with ``created=False``. Returns 404 if the CV,
    section, or entry does not exist (or belongs to another user),
    or 422 if the section's kind is not library-eligible.
    """
    from app.services.library import LibraryService

    lib_service = LibraryService(db)
    try:
        result = await lib_service.add_section_entry_to_library(
            cv_id, section_id, entry_id, current_user.id
        )
    except ValueError as exc:
        msg = str(exc)
        if "not library-eligible" in msg or "has no entry list" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    return AddEntryToLibraryResponse(
        library_id=result.library_id,
        entry_id=result.entry_id,
        created=result.created,
    )
