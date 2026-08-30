"""Import routes — multipart PDF → typed ``ParseResult``.

``POST /api/v1/cvs/import/pdf`` accepts an uploaded PDF and returns the
:class:`ParseResult` shape that the front-end builder consumes. No
persistence happens here — the user reviews the parsed sections in
the editor and saves via the existing ``POST /api/v1/cvs`` flow.

When the multipart request includes ``provider`` + ``api_key`` form
fields, the orchestrator may route through a vendor LLM. The key
lives in memory only for the lifetime of the request; it is dropped
when the adapter's async client is closed and never reaches a log line.
Provider failures use fixed public messages so a vendor SDK cannot leak a
key or transport detail into a response body.

Status code map:

- 200 → ``ParseResult``
- 400 → unsupported MIME / bad provider string / unrecognised key
  prefix / provider-key mismatch
- 401 → unauthenticated (``get_current_user``) or
  ``InvalidAPIKeyError`` from the LLM adapter (NEVER falls back)
- 413 → file too large (>15 MB)
- 422 → ``EmptyInputError`` or ``ExtractionFailedError``
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.services.parser import (
    EmptyInputError,
    ExtractionFailedError,
    InvalidAPIKeyError,
    ParseResult,
    UnknownProviderError,
    detect_provider,
    parse_cv,
)
from app.services.parser.extract import UnsupportedFormatError
from app.services.parser.keys import LLMProvider


router = APIRouter(prefix="/cvs/import", tags=["imports"])


ALLOWED_MIME = {"application/pdf"}
MAX_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/pdf", response_model=ParseResult)
@limiter.limit("5/minute")
async def import_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    api_key: str | None = Form(default=None),
    provider: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported document format",
        )

    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded document is too large",
        )

    provider_enum: LLMProvider | None = None
    if provider:
        try:
            provider_enum = LLMProvider(provider.strip().lower())
        except ValueError:
            allowed = ", ".join(p.value for p in LLMProvider)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider. Allowed: {allowed}",
            )

    if api_key and provider_enum is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A provider is required when an API key is supplied",
        )
    if api_key is not None and len(api_key) > 512:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key",
        )

    if api_key and provider_enum is not None:
        try:
            detected = detect_provider(api_key)
        except UnknownProviderError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unrecognised API key format",
            )
        if detected != provider_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key format does not match the selected provider",
            )

    try:
        return await parse_cv(
            raw,
            file.content_type,
            provider=provider_enum,
            api_key=api_key,
        )
    except InvalidAPIKeyError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The provider rejected this API key",
        )
    except EmptyInputError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded document contains no readable text",
        )
    except UnsupportedFormatError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported document format")
    except ExtractionFailedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to read the uploaded document",
        )


__all__ = ["router"]
