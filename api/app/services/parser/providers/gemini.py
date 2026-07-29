"""Google Gemini ``generateContent`` adapter for the LLM parser path.

Schema-constrained output via ``response_schema`` + ``response_mime_type``
in :class:`google.genai.types.GenerateContentConfig`. The SDK returns
parsed JSON on ``resp.parsed`` when those two flags are set.

Failure mapping mirrors the other adapters:

- :class:`google.api_core.exceptions.Unauthenticated` (and friends)
  → :class:`InvalidAPIKeyError`.
- :class:`google.api_core.exceptions.ResourceExhausted` → :class:`RateLimitError`.
- Everything else → :class:`ProviderTransportError`.

The adapter imports ``google.api_core.exceptions`` lazily inside the
except-clauses because ``google-genai`` doesn't declare it as a hard
runtime dep (it only re-raises errors bubbled from underlying RPCs).
"""

from __future__ import annotations

from typing import Any

from google import genai

from app.schema.models import SectionInstance

from ..keys import (
    InvalidAPIKeyError,
    ProviderTransportError,
    RateLimitError,
)
from .base import redact_payload


class GeminiProvider:
    """Google Gemini ``generateContent`` adapter."""

    name = "gemini"

    async def structure(
        self,
        *,
        plain_text: str,
        api_key: str,
        section_schema: dict[str, Any],
        hints: dict[str, Any] | None = None,
    ) -> list[SectionInstance]:
        # Lazy import — google-genai re-raises underlying google.api_core
        # errors but does not declare google.api_core as a hard dep.
        from google.api_core import exceptions as gapi_exc

        client = genai.Client(api_key=api_key)
        try:
            try:
                resp = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=plain_text,
                    config=genai.types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=section_schema,
                        system_instruction=(
                            "Return JSON matching the schema. Output ONLY JSON."
                        ),
                        temperature=0,
                    ),
                )
            except gapi_exc.Unauthenticated as e:
                raise InvalidAPIKeyError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except gapi_exc.PermissionDenied as e:
                raise InvalidAPIKeyError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except (gapi_exc.ResourceExhausted, gapi_exc.TooManyRequests) as e:
                raise RateLimitError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except gapi_exc.GoogleAPIError as e:
                raise ProviderTransportError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except Exception as e:
                raise ProviderTransportError(
                    redact_payload(getattr(e, "message", e))
                ) from e
        finally:
            # genai.Client is sync (the aio namespace is request-scoped) —
            # nothing to close. The api_key is captured only in the local
            # closure and dies with it.
            _ = client

        data = getattr(resp, "parsed", None)
        if data is None:
            # Fall back to text round-trip (older SDKs without response_schema).
            text = getattr(resp, "text", "") or ""
            try:
                import json as _json

                data = _json.loads(text)
            except Exception as e:
                raise ProviderTransportError(
                    f"Gemini returned no parsed content: {redact_payload(text[:200])}"
                ) from e

        try:
            raw_sections = data["sections"]
        except (KeyError, TypeError) as e:
            raise ProviderTransportError(
                f"Gemini response missing 'sections' key: {redact_payload(str(data)[:200])}"
            ) from e

        return [SectionInstance.model_validate(s) for s in raw_sections]


__all__ = ["GeminiProvider"]
