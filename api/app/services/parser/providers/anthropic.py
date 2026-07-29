"""Anthropic Messages adapter for the LLM parser path.

Schema-constrained output via the vendor's tool-use primitive:
``tools=[{name, input_schema}]`` + ``tool_choice={name}`` forces the
model to emit a single ``tool_use`` block whose ``input`` validates
against ``input_schema``. The adapter parses ``resp.content`` for the
first ``tool_use`` block and converts it to ``SectionInstance`` list.

Failure mapping mirrors the other adapters — auth → invalid key, 429
→ rate limit, anything else → transport. Error messages are passed
through :func:`redact_payload` before re-raising.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import (
    APIStatusError,
    AsyncAnthropic,
    AuthenticationError as AnthropicAuthenticationError,
    PermissionDeniedError,
    RateLimitError as AnthropicRateLimitError,
)

from app.schema.models import SectionInstance

from ..keys import (
    InvalidAPIKeyError,
    ProviderTransportError,
    RateLimitError,
)
from .base import redact_payload


class AnthropicProvider:
    """Anthropic Messages adapter (tool-use structured output)."""

    name = "anthropic"

    async def structure(
        self,
        *,
        plain_text: str,
        api_key: str,
        section_schema: dict[str, Any],
        hints: dict[str, Any] | None = None,
    ) -> list[SectionInstance]:
        client = AsyncAnthropic(api_key=api_key)
        try:
            try:
                resp = await client.messages.create(
                    model="claude-3-5-haiku-latest",
                    max_tokens=8192,
                    system="Return JSON matching the schema. Output ONLY JSON.",
                    messages=[{"role": "user", "content": plain_text}],
                    tools=[
                        {
                            "name": "emit_sections",
                            "description": "Emit the parsed CV sections.",
                            "input_schema": section_schema,
                        }
                    ],
                    tool_choice={"name": "emit_sections"},
                )
            except (AnthropicAuthenticationError, PermissionDeniedError) as e:
                raise InvalidAPIKeyError(
                    redact_payload(getattr(e, "message", e))
                ) from e
            except AnthropicRateLimitError as e:
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

        tool_blocks = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        if not tool_blocks:
            # Tool-use forced — empty list means the model refused or
            # hit max_tokens. Surface as transport so the orchestrator
            # can fall back.
            raise ProviderTransportError(
                "Anthropic returned no tool_use blocks; "
                "model may have refused or hit max_tokens."
            )

        raw_input = tool_blocks[0].input
        try:
            data = raw_input if isinstance(raw_input, dict) else json.loads(raw_input)
        except json.JSONDecodeError as e:
            raise ProviderTransportError(
                f"Anthropic tool_use payload was non-JSON: {redact_payload(str(raw_input)[:200])}"
            ) from e

        try:
            raw_sections = data["sections"]
        except (KeyError, TypeError) as e:
            raise ProviderTransportError(
                f"Anthropic response missing 'sections' key: {redact_payload(str(data)[:200])}"
            ) from e

        return [SectionInstance.model_validate(s) for s in raw_sections]


__all__ = ["AnthropicProvider"]
