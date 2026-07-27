"""OpenAI Chat Completions adapter for the LLM parser path.

Strict JSON-Schema shape via the ``json_schema`` response_format. The
adapter is the ONLY place the API key lives in memory; the async
client is constructed per call, used once, and closed immediately.

Failure handling:
- ``openai.AuthenticationError`` / ``PermissionDeniedError`` →
  :class:`InvalidAPIKeyError`.
- ``openai.RateLimitError`` → :class:`RateLimitError`.
- Anything else → :class:`ProviderTransportError`.

All messages are passed through :func:`redact_payload` before
re-raising so the route's logging handler never sees raw key bytes.
"""

from __future__ import annotations

import json
from typing import Any

from openai import (
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError as OpenAIAuthenticationError,
    PermissionDeniedError,
    RateLimitError as OpenAIRateLimitError,
)

from app.schema.models import SectionInstance

from ..keys import (
    InvalidAPIKeyError,
    ProviderTransportError,
    RateLimitError,
)
from .base import redact_payload


class OpenAIProvider:
    """OpenAI Chat Completions adapter.

    Uses ``gpt-4o-mini`` — cheap and supports structured outputs via
    the ``json_schema`` response format.
    """

    name = "openai"

    async def structure(
        self,
        *,
        plain_text: str,
        api_key: str,
        section_schema: dict[str, Any],
        hints: dict[str, Any] | None = None,
    ) -> list[SectionInstance]:
        client = AsyncOpenAI(api_key=api_key)
        try:
            try:
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Return JSON matching the schema. "
                                "Output ONLY the JSON. No commentary."
                            ),
                        },
                        {"role": "user", "content": plain_text},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "section_instances",
                            "schema": section_schema,
                            "strict": True,
                        },
                    },
                    temperature=0,
                )
            except (OpenAIAuthenticationError, PermissionDeniedError) as e:
                raise InvalidAPIKeyError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except OpenAIRateLimitError as e:
                raise RateLimitError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except APIStatusError as e:
                raise ProviderTransportError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except Exception as e:
                # Network errors, timeouts, malformed replies — anything
                # non-status. Treat as transport; orchestrator may fall
                # back to regex.
                raise ProviderTransportError(
                    redact_payload(getattr(e, "message", e))
                ) from e
        finally:
            await client.close()

        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ProviderTransportError(
                f"OpenAI returned non-JSON content: {redact_payload(content[:200])}"
            ) from e

        try:
            raw_sections = data["sections"]
        except (KeyError, TypeError) as e:
            raise ProviderTransportError(
                f"OpenAI response missing 'sections' key: {redact_payload(str(data)[:200])}"
            ) from e

        return [SectionInstance.model_validate(s) for s in raw_sections]


__all__ = ["OpenAIProvider"]
