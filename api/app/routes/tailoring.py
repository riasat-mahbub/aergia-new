"""Browser and scoped-capability routes for local-agent tailoring."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.tailoring import (
    TailoringCodeExchange,
    TailoringEvidencePacket,
    TailoringExchangeResponse,
    TailoringPatch,
    TailoringSessionCreateResponse,
    TailoringSubmitResponse,
)
from app.services.tailoring import (
    StoredRequirementsUnavailableError,
    TailoringConflictError,
    TailoringExpiredError,
    TailoringNotFoundError,
    TailoringPatchError,
    TailoringService,
    TailoringUnauthorizedError,
    TailoringUnavailableError,
)

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, TailoringNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found") from exc
    if isinstance(exc, TailoringUnavailableError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, StoredRequirementsUnavailableError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, TailoringExpiredError):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Tailoring session expired") from exc
    if isinstance(exc, TailoringConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, TailoringPatchError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if isinstance(exc, TailoringUnauthorizedError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tailoring capability",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    raise exc


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result, _session = await TailoringService(db).create_session(application_id, current_user.id)
        return result
    except Exception as exc:  # noqa: BLE001
        _raise_service_error(exc)


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
        _raise_service_error(exc)


@router.get(
    "/tailoring/evidence",
    response_model=TailoringEvidencePacket,
)
@limiter.limit("30/minute")
async def get_tailoring_evidence(
    request: Request,
    response: Response,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).evidence(capability)
    except Exception as exc:  # noqa: BLE001
        _raise_service_error(exc)


@router.post(
    "/tailoring/submit",
    response_model=TailoringSubmitResponse,
)
@limiter.limit("5/minute")
async def submit_tailoring_patch(
    request: Request,
    response: Response,
    patch: TailoringPatch,
    capability: str | None = Header(default=None, alias="X-Aergia-Tailoring-Capability"),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await TailoringService(db).submit(capability, patch)
    except Exception as exc:  # noqa: BLE001
        _raise_service_error(exc)


__all__ = ["router"]
