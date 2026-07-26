"""Import routes — multipart PDF → typed ``ParseResult``.

`POST /api/v1/cvs/import/pdf` accepts an uploaded PDF and returns the
:class:`ParseResult` shape that the front-end builder consumes. No
persistence happens here — the user reviews the parsed sections in the
editor and saves via the existing ``POST /api/v1/cvs`` flow.

Status code map:

- 200 → ``ParseResult``
- 400 → unsupported MIME / empty input / invalid JSON-shape
- 401 → unauthenticated (``get_current_user``)
- 413 → file too large (>15 MB)
- 422 → ``ExtractionFailedError`` (corrupt PDF)
- 500 → unhandled Pydantic ``ValidationError``
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.parser import (
    EmptyInputError,
    ExtractionFailedError,
    ParseResult,
    parse_cv,
)
from app.services.parser.extract import UnsupportedFormatError


router = APIRouter(prefix="/cvs/import", tags=["imports"])


ALLOWED_MIME = {"application/pdf"}
MAX_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/pdf", response_model=ParseResult)
async def import_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: pdf",
        )

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum {MAX_BYTES // (1024 * 1024)}MB",
        )

    try:
        return parse_cv(raw, file.content_type)
    except EmptyInputError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ExtractionFailedError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


__all__ = ["router"]
