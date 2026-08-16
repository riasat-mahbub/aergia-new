from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.photo import PhotoUploadResponse
from app.services.photo import PhotoService
from app.core.deps import get_current_user
from app.models.user import User
from app.core.rate_limit import limiter

router = APIRouter()


@router.post("", response_model=PhotoUploadResponse)
@limiter.limit("30/minute")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PhotoService(db)
    url = await service.upload(file, current_user.id)
    return PhotoUploadResponse(url=url)


@router.get("/{filename}")
async def get_photo(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PhotoService(db)
    path = service.get_path(filename, current_user.id)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media_type)


@router.delete("/{filename}", status_code=status.HTTP_200_OK)
async def delete_photo(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PhotoService(db)
    deleted = await service.delete(filename, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return {"message": "File deleted"}
