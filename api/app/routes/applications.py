"""Authenticated application tracker routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationGenerateResponse,
    ApplicationListItem,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.services.application import (
    APPLICATION_ALREADY_GENERATED,
    APPLICATION_NOT_FOUND,
    PROFILE_REQUIRED,
    ApplicationGenerationConflictError,
    ApplicationService,
    ProfileRequiredError,
)
from app.services.relevance import KEYWORD_EXTRACTION_ERROR

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
    application = await ApplicationService(db).create_application(current_user.id, data)
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
    except ValueError as exc:
        if str(exc) == KEYWORD_EXTRACTION_ERROR:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
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


@router.post("/{application_id}/generate", response_model=ApplicationGenerateResponse)
async def generate_application_cv(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    try:
        generated = await service.generate_cv(application_id, current_user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProfileRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=PROFILE_REQUIRED) from exc
    except ApplicationGenerationConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=APPLICATION_ALREADY_GENERATED) from exc
    except ValueError as exc:
        if str(exc) == KEYWORD_EXTRACTION_ERROR:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        raise
    return ApplicationGenerateResponse(application=_response(generated.application), cv_id=generated.cv_id)


@router.post("/{application_id}/relevance", response_model=ApplicationResponse)
async def recompute_application_relevance(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ApplicationService(db)
    try:
        application = await service.recompute_relevance(application_id, current_user.id)
    except ValueError as exc:
        if str(exc) == KEYWORD_EXTRACTION_ERROR:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        raise
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=APPLICATION_NOT_FOUND)
    return _response(application)
