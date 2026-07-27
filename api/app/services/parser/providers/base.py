"""LLM provider protocol + adapter-side safety helpers.

This is the seam between the parser orchestrator and the four
vendor-specific adapters (``openai.py``, ``anthropic.py``,
``gemini.py``, ``groq.py``). Each adapter implements
:class:`LLMProvider` against the signature below and is the ONLY
place an API key may exist in memory.

Key handling contract:
    1. The adapter receives the key as a parameter to ``structure``.
    2. It MUST NOT store the key on ``self`` between calls.
    3. It MUST NOT include the key in any return value.
    4. It MUST pass any error message through :func:`redact_payload`
       before raising so the route's logging handler never sees raw
       key bytes.
    5. After the call, the adapter closes its async client; the key
       is dropped at the same line.

A subclass that violates any of these five rules is a bug — write
tests that lock the behaviour.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.schema.models import SectionInstance

from ..keys import redact


class LLMProvider(Protocol):
    """Adapter contract — one implementation per vendor.

    The orchestrator calls :meth:`structure` with the extracted plain
    text, a schema to constrain the model output, the API key (good
    for one call), and optional prompt hints. The adapter returns a
    validated ``list[SectionInstance]`` — never raw dicts.
    """

    name: str

    async def structure(
        self,
        *,
        plain_text: str,
        api_key: str,
        section_schema: dict[str, Any],
        hints: dict[str, Any] | None = None,
    ) -> list[SectionInstance]:
        ...


def redact_payload(value: Any) -> str:
    """Stringify + redact a payload/value before logging or raising.

    Adapters MUST use this helper — never raise or log
    ``str(exception)`` directly, because vendor SDKs sometimes echo
    key fragments into the exception message text.
    """
    if value is None:
        return ""
    return redact(str(value))


__all__ = ["LLMProvider", "redact_payload"]
