"""Authenticated application tracker routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.http_schemas.application import (
    ApplicationCreate,
    ApplicationListItem,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.services.application import (
    APPLICATION_NOT_FOUND,
    ApplicationCVLinkError,
    ApplicationService,
)
from app.services.relevance import (
    KEYWORD_EXTRACTION_ERROR,
    REQUIREMENT_EXTRACTION_ERROR,
    RequirementExtractionError,
)
from app.services.quotas import QuotaExceededError, QuotaResource

router = APIRouter()


def _response(application) -> ApplicationResponse:
    return ApplicationResponse.model_validate(application)


@router.get("", response_model=list[ApplicationListItem])
async def list_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    applications = await ApplicationService(db).list_applications(current_user.id)
    return [ApplicationListItem.model_validate(application) for application in applications]


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        application = await ApplicationService(db).create_application(current_user.id, data)
    except QuotaExceededError as exc:
        if exc.resource is QuotaResource.APPLICATION:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application limit reached",
            ) from exc
        raise
    except RequirementExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=REQUIREMENT_EXTRACTION_ERROR,
        ) from exc
    return _response(application)


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await ApplicationService(db).get_application(application_id, current_user.id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=APPLICATION_NOT_FOUND)
    return _response(application)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    try:
        application = await service.update_application(application_id, current_user.id, data)
    except ApplicationCVLinkError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RequirementExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=REQUIREMENT_EXTRACTION_ERROR,
        ) from exc
    except ValueError as exc:
        if str(exc) == KEYWORD_EXTRACTION_ERROR:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=KEYWORD_EXTRACTION_ERROR) from exc
        raise
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=APPLICATION_NOT_FOUND)
    return _response(application)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await ApplicationService(db).delete_application(application_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=APPLICATION_NOT_FOUND)
    return None


@router.post("/{application_id}/relevance", response_model=ApplicationResponse)
async def recompute_application_relevance(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    try:
        application = await service.recompute_relevance(application_id, current_user.id)
    except RequirementExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=REQUIREMENT_EXTRACTION_ERROR,
        ) from exc
    except ValueError as exc:
        if str(exc) == KEYWORD_EXTRACTION_ERROR:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=KEYWORD_EXTRACTION_ERROR) from exc
        raise
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=APPLICATION_NOT_FOUND)
    return _response(application)


@router.post("/{application_id}/scan", response_model=ApplicationResponse)
@limiter.limit("5/minute")
async def scan_application(
    request: Request,
    response: Response,
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application_service = ApplicationService(db)
    try:
        application = await application_service.scan_application(application_id, current_user.id)
    except ValueError as exc:
        if str(exc) in {"Application has no linked CV", "Application's linked CV is unavailable"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        raise
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=APPLICATION_NOT_FOUND)
    return _response(application)
