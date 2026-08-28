"""Owner-scoped profile photo storage and image validation."""

from __future__ import annotations

import io
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_PIXELS = 25_000_000


class PhotoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = Path(settings.uploads_path)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _bad_file(detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    def _owned_path(self, filename: str, user_id: str) -> Path | None:
        """Return a safe owner path, rejecting traversal and foreign IDs."""

        pattern = rf"{re.escape(str(user_id))}_[0-9a-f]{{32}}(?:\.jpg|\.jpeg|\.png|\.webp)"
        if not re.fullmatch(pattern, filename or ""):
            return None
        root = self.upload_dir.resolve()
        candidate = (self.upload_dir / filename).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _verify_image(contents: bytes) -> None:
        try:
            with Image.open(io.BytesIO(contents)) as image:
                width, height = image.size
                if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                    raise PhotoService._bad_file("Image dimensions exceed the allowed limit")
                image.verify()
        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise PhotoService._bad_file("Uploaded file is not a valid image") from exc

    async def upload(self, file: UploadFile, user_id: str) -> str:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise self._bad_file(
                f"Invalid file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        if file.content_type != ALLOWED_CONTENT_TYPES[ext]:
            raise self._bad_file("Uploaded image type does not match its file extension")

        contents = await file.read(MAX_FILE_SIZE + 1)
        if len(contents) > MAX_FILE_SIZE:
            raise self._bad_file(f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB")
        self._verify_image(contents)

        filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
        filepath = self._owned_path(filename, user_id)
        if filepath is None:
            raise self._bad_file("Invalid generated filename")
        # The filename is generated server-side and validated above; no
        # client path component is ever used for the write.
        try:
            with filepath.open("xb") as output:
                output.write(contents)
        except Exception:
            # Avoid leaving a truncated image if the write fails after the
            # file has been created.
            try:
                filepath.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return f"/api/v1/assets/{filename}"

    async def delete(self, filename: str, user_id: str) -> bool:
        filepath = self._owned_path(filename, user_id)
        if filepath is None or not filepath.is_file():
            return False
        try:
            os.remove(filepath)
        except FileNotFoundError:
            return False
        return True

    def get_path(self, filename: str, user_id: str) -> Path | None:
        filepath = self._owned_path(filename, user_id)
        return filepath if filepath is not None and filepath.is_file() else None


__all__ = ["ALLOWED_EXTENSIONS", "MAX_FILE_SIZE", "MAX_IMAGE_PIXELS", "PhotoService"]
