from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.photo import PhotoUploadResponse
from app.services.photo import PhotoService
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PhotoService(db)
    url = await service.upload(file, current_user.id)
    return PhotoUploadResponse(url=url)


@router.delete("/{filename}", status_code=status.HTTP_200_OK)
async def delete_photo(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PhotoService(db)
    deleted = await service.delete(filename)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return {"message": "File deleted"}
