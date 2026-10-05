"""Browser and scoped-capability routes for local-agent tailoring."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.http_schemas.tailoring import (
    PROTOCOL_VERSION,
    TailoringCodeExchange,
    TailoringContextResponse,
    TailoringExchangeResponse,
    TailoringPreviewRequest,
    TailoringPreviewReservationRequest,
    TailoringPreviewReservationResponse,
    TailoringPreviewReservationReleaseResponse,
    TailoringPreviewResponse,
    TailoringReviewResponse,
    TailoringSessionCreateResponse,
    TailoringSessionStatusResponse,
    TailoringSubmitRequest,
    TailoringSubmitResponse,
)
from app.services.tailoring import (
    TailoringConflictError,
    TailoringExpiredError,
    TailoringNotFoundError,
    TailoringCandidateError,
    TailoringSessionNotFoundError,
    TailoringStaleError,
    TailoringService,
    TailoringUnauthorizedError,
    TailoringUnavailableError,
    TailoringPreviewUnavailableError,
)
from app.services.tailoring_skill import build_tailoring_skill_bundle
from app.services.quotas import QuotaExceededError, QuotaResource

router = APIRouter()


@router.get("/tailoring/skill.zip", response_class=Response)
@limiter.limit("30/minute")
async def download_tailoring_skill(request: Request):
    """Download the official self-contained skill without account credentials."""

    try:
        bundle = build_tailoring_skill_bundle()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Aergia tailoring skill bundle is unavailable",
        ) from exc
    return Response(
        content=bundle.content,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="aergia-tailor.zip"',
            "Cache-Control": "public, max-age=300",
            "ETag": f'"sha256-{bundle.sha256}"',
            "X-Aergia-Skill-Protocol-Version": str(PROTOCOL_VERSION),
        },
    )


async def _raise_service_error(exc: Exception, db: AsyncSession) -> JSONResponse:
    """Return the frozen top-level conflict envelope with route-owned tx control."""

    headers = None
    if isinstance(exc, TailoringSessionNotFoundError):
        code, http_status, detail = "invalid_session", status.HTTP_404_NOT_FOUND, "Tailoring session not found"
    elif isinstance(exc, TailoringNotFoundError):
        code, http_status, detail = "application_unavailable", status.HTTP_404_NOT_FOUND, "Application not found"
    elif isinstance(exc, TailoringUnavailableError):
        code, http_status, detail = exc.code, exc.status_code, str(exc)
    elif isinstance(exc, QuotaExceededError):
        if exc.resource is QuotaResource.CV:
            code, http_status, detail = "quota", status.HTTP_409_CONFLICT, "CV limit reached"
        else:
            raise exc
    elif isinstance(exc, TailoringExpiredError):
        code, http_status, detail = exc.code, exc.status_code, str(exc)
    elif isinstance(exc, TailoringConflictError):
        code, http_status, detail = exc.code, exc.status_code, str(exc)
    elif isinstance(exc, TailoringStaleError):
        code, http_status, detail = exc.code, exc.status_code, str(exc)
    elif isinstance(exc, TailoringCandidateError):
        code, http_status, detail = exc.code, exc.status_code, str(exc)
    elif isinstance(exc, TailoringUnauthorizedError):
        code, http_status, detail = exc.code, exc.status_code, "Invalid tailoring capability"
        headers = {"WWW-Authenticate": "Bearer"}
    elif isinstance(exc, TailoringPreviewUnavailableError):
        code, http_status, detail = exc.code, exc.status_code, str(exc)
    else:
        raise exc

    detail = str(detail)[:1000]
    if not getattr(exc, "commit_outcome", False):
        # A JSONResponse is a normal dependency return, so explicitly roll
        # back any incomplete write set before returning a conflict. Expiry,
        # lease cleanup, and render-release outcomes opt in to committing.
        await db.rollback()
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "detail": detail},
        headers=headers,
    )


@router.post(
    "/applications/{application_id}/tailoring-sessions",
    response_model=TailoringSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_tailoring_session(
    request: Request,
    response: Response,
    application_id: str,
    protocol_version: int = Query(default=PROTOCOL_VERSION, ge=PROTOCOL_VERSION, le=PROTOCOL_VERSION),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result, _session = await TailoringService(db).create_session(
            application_id,
            current_user.id,
            # Use the configured browser origin rather than an untrusted Host
            # header when constructing a link that will be pasted into an
            # external coding agent.
            session_url_base=get_settings().frontend_url.rstrip("/"),
            protocol_version=protocol_version,
        )
        return result
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.get(
    "/applications/{application_id}/tailoring-sessions/latest",
    response_model=TailoringSessionStatusResponse,
)
@limiter.limit("30/minute")
async def get_latest_tailoring_session(
    request: Request,
    response: Response,
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).latest_session_status(application_id, current_user.id)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.get(
    "/tailoring/sessions/{session_id}",
    response_model=TailoringSessionStatusResponse,
)
@limiter.limit("30/minute")
async def get_tailoring_session_status(
    request: Request,
    response: Response,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).session_status(session_id, current_user.id)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/sessions/{session_id}/cancel",
    response_model=TailoringSessionStatusResponse,
)
@limiter.limit("10/minute")
async def cancel_tailoring_session(
    request: Request,
    response: Response,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).cancel_session(session_id, current_user.id)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/exchange",
    response_model=TailoringExchangeResponse,
)
@limiter.limit("10/minute")
async def exchange_tailoring_code(
    request: Request,
    response: Response,
    data: TailoringCodeExchange,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).exchange_code(data)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.get("/tailoring/context", response_model=TailoringContextResponse)
@limiter.limit("30/minute")
async def get_tailoring_context(
    request: Request,
    response: Response,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).context(capability)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/preview-reservations",
    response_model=TailoringPreviewReservationResponse,
)
@limiter.limit("30/minute")
async def reserve_tailoring_preview(
    request: Request,
    response: Response,
    payload: TailoringPreviewReservationRequest,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    """Acquire a short retry-stable lease before expensive PDF work."""

    try:
        return await TailoringService(db).reserve_preview(capability, payload)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/preview-reservations/{reservation_id}/release",
    response_model=TailoringPreviewReservationReleaseResponse,
)
@limiter.limit("30/minute")
async def release_tailoring_preview_reservation(
    request: Request,
    response: Response,
    reservation_id: str,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    """Release an uncompleted preview lease without spending a preview slot."""

    try:
        return await TailoringService(db).release_preview_reservation(capability, reservation_id)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/preview",
    response_model=TailoringPreviewResponse,
)
@limiter.limit("10/minute")
async def preview_tailoring_candidate(
    request: Request,
    response: Response,
    payload: TailoringPreviewRequest,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    """Render a freeform candidate without persisting it."""

    try:
        return await TailoringService(db).candidate_preview(capability, payload)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/submit",
    response_model=TailoringSubmitResponse,
)
@limiter.limit("5/minute")
async def submit_tailoring_candidate(
    request: Request,
    response: Response,
    payload: TailoringSubmitRequest,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).submit(capability, payload)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/sessions/{session_id}/accept",
    response_model=TailoringReviewResponse,
)
@limiter.limit("10/minute")
async def accept_tailoring_draft(
    request: Request,
    response: Response,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).accept_draft(session_id, current_user.id)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


@router.post(
    "/tailoring/sessions/{session_id}/reject",
    response_model=TailoringReviewResponse,
)
@limiter.limit("10/minute")
async def reject_tailoring_draft(
    request: Request,
    response: Response,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).reject_draft(session_id, current_user.id)
    except Exception as exc:  # noqa: BLE001
        return await _raise_service_error(exc, db)


__all__ = ["router"]
