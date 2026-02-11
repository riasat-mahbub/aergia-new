import uuid
import os
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class PhotoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = Path(settings.uploads_path)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile, user_id: str) -> str:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
        filepath = self.upload_dir / filename

        with open(filepath, "wb") as f:
            f.write(contents)

        return f"/uploads/{filename}"

    async def delete(self, filename: str) -> bool:
        filepath = self.upload_dir / filename
        if filepath.exists():
            os.remove(filepath)
            return True
        return False
