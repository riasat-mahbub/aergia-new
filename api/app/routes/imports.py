"""Import routes — multipart PDF → typed ``ParseResult``.

``POST /api/v1/cvs/import/pdf`` accepts an uploaded PDF and returns the
:class:`ParseResult` shape that the front-end builder consumes. No
persistence happens here — the user reviews the parsed sections in
the editor and saves via the existing ``POST /api/v1/cvs`` flow.

When the multipart request includes ``provider`` + ``api_key`` form
fields, the orchestrator may route through a vendor LLM. The key
lives in memory only for the lifetime of the request; it is dropped
when the adapter's async client is closed and never reaches a log
line (every vendor error passes through ``redact()`` first). The
route also applies ``redact()`` to any ``InvalidAPIKeyError``
message body — belt-and-suspenders so a misbehaving adapter cannot
leak the key into the 401 response body.

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
    InvalidAPIKeyError,
    ParseResult,
    UnknownProviderError,
    detect_provider,
    parse_cv,
)
from app.services.parser.extract import UnsupportedFormatError
from app.services.parser.keys import LLMProvider, redact as _redact


router = APIRouter(prefix="/cvs/import", tags=["imports"])


ALLOWED_MIME = {"application/pdf"}
MAX_BYTES = 15 * 1024 * 1024  # 15MB


@router.post("/pdf", response_model=ParseResult)
async def import_pdf(
    file: UploadFile = File(...),
    api_key: str | None = Form(default=None),
    provider: str | None = Form(default=None),
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

    provider_enum: LLMProvider | None = None
    if provider:
        try:
            provider_enum = LLMProvider(provider.strip().lower())
        except ValueError:
            allowed = ", ".join(p.value for p in LLMProvider)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider!r}. Allowed: {allowed}",
            )

    if api_key and provider_enum is not None:
        try:
            detected = detect_provider(api_key)
        except UnknownProviderError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unrecognised API key prefix. Supported prefixes: "
                    "sk- (OpenAI), sk-ant- (Anthropic), AIza (Gemini), gsk_ (Groq)."
                ),
            )
        if detected != provider_enum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"API key shape does not match declared provider "
                    f"{provider_enum.value!r}."
                ),
            )

    try:
        return await parse_cv(
            raw,
            file.content_type,
            provider=provider_enum,
            api_key=api_key,
        )
    except InvalidAPIKeyError as e:
        # Adapter redacts by contract; route redacts again as a safety net.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_redact(str(e)),
        )
    except EmptyInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ExtractionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


__all__ = ["router"]
