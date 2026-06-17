"""Photo upload response schema."""

from __future__ import annotations

from pydantic import BaseModel


class PhotoUploadResponse(BaseModel):
    url: str


__all__ = ["PhotoUploadResponse"]
