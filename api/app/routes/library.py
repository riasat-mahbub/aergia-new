"""Library HTTP routes mounted under ``/api/v1/library``.

All endpoints require an authenticated user (``get_current_user``) and
enforce per-user ownership inside the service layer.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.library import (
    LibraryCloneResponse,
    LibraryEntryCreate,
    LibraryEntryKind,
    LibraryEntryResponse,
    LibraryEntryUpdate,
)
from app.services.library import LibraryService

NOT_FOUND = "Library entry not found"

router = APIRouter()


def _to_response(entry) -> LibraryEntryResponse:
    """Convert an ORM ``LibraryEntry`` to its response shape.

    Centralised so route handlers stay declarative; mirrors the
    ``model_validate(cv)`` pattern used by ``routes/cvs.py``.
    """
    return LibraryEntryResponse(
        id=entry.id,
        kind=LibraryEntryKind(entry.kind),
        payload=list(entry.payload or []),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("", response_model=list[LibraryEntryResponse])
async def list_library(
    kind: LibraryEntryKind | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LibraryService(db)
    entries = await service.list_entries(current_user.id, kind.value if kind else None)
    return [_to_response(e) for e in entries]


@router.post("", response_model=LibraryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_library_entry(
    data: LibraryEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LibraryService(db)
    entry = await service.create_entry(current_user.id, data)
    return _to_response(entry)


@router.get("/{entry_id}", response_model=LibraryEntryResponse)
async def get_library_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LibraryService(db)
    entry = await service.get_entry(entry_id, current_user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return _to_response(entry)


@router.patch("/{entry_id}", response_model=LibraryEntryResponse)
async def update_library_entry(
    entry_id: str,
    data: LibraryEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LibraryService(db)
    entry = await service.update_entry(entry_id, current_user.id, data)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return _to_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LibraryService(db)
    deleted = await service.delete_entry(entry_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return None


@router.post("/{entry_id}/clone", response_model=LibraryCloneResponse)
async def clone_library_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = LibraryService(db)
    try:
        section = await service.clone_to_section_instance(entry_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return LibraryCloneResponse(section_instance=section)
