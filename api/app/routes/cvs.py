from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.cv import CVApplicationSummary, CVCreate, CVUpdate, CVResponse, CVListItem
from app.schemas.library import AddEntryToLibraryRequest, AddEntryToLibraryResponse, PromoteToLibraryResponse
from app.services.cv import CVLinkedToApplicationError, CVService
from app.services.cv import coerce_customizations
from app.services.pdf import PDFService
from app.services.renderer import HTMLDocumentRenderer, build_document, resolve
from app.routes.render import strip_anchor_hrefs
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User

NOT_FOUND = "CV not found"

router = APIRouter()
logger = logging.getLogger("aergia.cvs")

@router.get("", response_model=list[CVListItem])
async def list_cvs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cv_pairs = await service.list_cv_summaries(current_user.id)
    return [
        CVListItem(
            id=cv.id,
            title=cv.title,
            template_id=cv.template_id,
            created_at=cv.created_at,
            updated_at=cv.updated_at,
            application=(
                CVApplicationSummary(
                    id=application.id,
                    company=application.company,
                    role=application.role,
                    status=application.status,
                    generation_status=application.generation_status,
                    applied_at=application.applied_at,
                )
                if application
                else None
            ),
        )
        for cv, application in cv_pairs
    ]


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
    try:
        deleted = await service.delete_cv(cv_id, current_user.id)
    except CVLinkedToApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="CV is linked to an application",
        ) from exc
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
@limiter.limit("10/minute")
async def preview_cv(
    request: Request,
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CVService(db)
    cv = await service.get_cv(cv_id, current_user.id)
    if not cv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)


    try:
        template_data = await service.get_template_data(cv.template_id)
        manifest = (template_data or {}).get("manifest", {})

        from app.schema.models import TemplateManifest

        manifest_model = TemplateManifest.model_validate(manifest)
        document = build_document(cv, manifest_model)
        customizations_model = coerce_customizations(cv.customizations)
        renderer = HTMLDocumentRenderer()
        model = resolve(document, renderer, manifest_model, customizations_model)
        html = renderer.render(model)
    except Exception as exc:  # noqa: BLE001
        logger.error("cv_preview_failed", extra={"exception_type": type(exc).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to render CV preview",
        ) from exc

    # Preview is rendered inside a sandboxed iframe. Neutralize hrefs so the
    # links are visible but cannot navigate the editing surface.
    html = strip_anchor_hrefs(html)
    return {"html": html}


@router.post("/{cv_id}/export/pdf")
@limiter.limit("5/minute")
async def export_cv_pdf(
    request: Request,
    cv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PDFService(db)
    try:
        pdf_bytes = await service.export_pdf(cv_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found") from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("cv_pdf_export_failed", extra={"exception_type": type(exc).__name__})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to export CV",
        ) from exc

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from exc
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
    data: AddEntryToLibraryRequest | None = None,
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
            cv_id,
            section_id,
            entry_id,
            current_user.id,
            entry_snapshot=data.entry if data else None,
            snapshot_kind=data.kind.value if data else None,
        )
    except ValueError as exc:
        msg = str(exc)
        if (
            "not library-eligible" in msg
            or "has no entry list" in msg
            or "does not match section kind" in msg
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Section is not eligible for the Library",
            ) from exc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND) from exc
    return AddEntryToLibraryResponse(
        library_id=result.library_id,
        entry_id=result.entry_id,
        created=result.created,
    )
