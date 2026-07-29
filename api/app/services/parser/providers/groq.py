"""Groq OpenAI-compatible Chat Completions adapter.

Groq's hosted models support ``response_format={"type": "json_object"}``
but not the strict ``json_schema`` shape — the adapter therefore
fortifies the system prompt with the schema text and relies on
``SectionInstance.model_validate(...)`` for actual schema enforcement.
"""

from __future__ import annotations

import json
from typing import Any

from groq import (
    APIStatusError,
    AsyncGroq,
    AuthenticationError as GroqAuthenticationError,
    PermissionDeniedError,
    RateLimitError as GroqRateLimitError,
)

from app.schema.models import SectionInstance

from ..keys import (
    InvalidAPIKeyError,
    ProviderTransportError,
    RateLimitError,
)
from .base import redact_payload


class GroqProvider:
    """Groq OpenAI-compatible Chat Completions adapter.

    Uses ``llama-3.3-70b-versatile`` — cheap, supports JSON mode.
    """

    name = "groq"

    async def structure(
        self,
        *,
        plain_text: str,
        api_key: str,
        section_schema: dict[str, Any],
        hints: dict[str, Any] | None = None,
    ) -> list[SectionInstance]:
        client = AsyncGroq(api_key=api_key)
        try:
            try:
                resp = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Return JSON matching the schema. "
                                "Output ONLY the JSON. No commentary.\n"
                                f"Schema: {json.dumps(section_schema)}"
                            ),
                        },
                        {"role": "user", "content": plain_text},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
            except (GroqAuthenticationError, PermissionDeniedError) as e:
                raise InvalidAPIKeyError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except GroqRateLimitError as e:
                raise RateLimitError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except APIStatusError as e:
                raise ProviderTransportError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except Exception as e:
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
                f"Groq returned non-JSON content: {redact_payload(content[:200])}"
            ) from e

        try:
            raw_sections = data["sections"]
        except (KeyError, TypeError) as e:
            raise ProviderTransportError(
                f"Groq response missing 'sections' key: {redact_payload(str(data)[:200])}"
            ) from e

        return [SectionInstance.model_validate(s) for s in raw_sections]


__all__ = ["GroqProvider"]
