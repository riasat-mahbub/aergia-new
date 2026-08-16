"""Strategy protocol — the seam between regex and LLM paths.

The :class:`ParseStrategy` protocol lives here so adding a new path means
implementing one class without touching the orchestrator. ``RegexStrategy``
ships today; ``LLMStrategy`` calls a vendor-specific adapter that turns
plain text into ``SectionInstance`` objects and returns high confidence.

Each strategy exposes ``structure`` (for sync regex) or ``structure_async``
(for async LLM). The orchestrator picks the right entry point based on
which path it chose.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schema.models import SectionInstance

from .keys import LLMProvider, redact
from .schemas import ConfidenceReport, ExtractedDocument


@runtime_checkable
class ParseStrategy(Protocol):
    """A path that turns an :class:`ExtractedDocument` into typed sections."""

    name: str


# ---------------------------------------------------------------------------
# Regex path
# ---------------------------------------------------------------------------


class RegexStrategy:
    """The ship-today path. Runs classify + map_to_sections."""

    name = "regex"

    def structure(
        self, extracted: ExtractedDocument
    ) -> tuple[list[SectionInstance], ConfidenceReport]:
        from .classify import classify
        from .mapper import map_to_sections

        labeled, conf_entries = classify(extracted)
        return map_to_sections(labeled, conf_entries)


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------


def _section_instance_array_schema() -> dict:
    """Wrap ``SectionInstance.model_json_schema()`` as a {sections:[..]} dict.

    Every vendor's structured-output path consumes this exact shape — the
    adapter copies it into ``response_format.json_schema.schema`` (OpenAI),
    the system prompt (Groq / Anthropic via tool ``input_schema``), or
    ``response_schema`` (Gemini).
    """
    inner = SectionInstance.model_json_schema()
    return {
        "type": "object",
        "properties": {"sections": {"type": "array", "items": inner}},
        "required": ["sections"],
    }


class LLMStrategy:
    """Calls a vendor adapter behind the protocol seam.

    Holds the API key only for the lifetime of one
    :meth:`structure_async` call — eager-cleared at the end of the method
    so the key never sits on ``self`` between requests.

    Construction does not pre-instantiate the adapter — the adapter is
    resolved by :func:`app.services.parser.imports._resolve_provider` and
    passed in as ``provider_cls``. That keeps the strategy ignorant of
    which vendor is in play.
    """

    name = "llm"

    def __init__(self, provider: LLMProvider, api_key: str) -> None:
        self._provider = provider
        # Provider resolution and adapter construction live in the
        # orchestrator; this class is only the typed tuple-returning
        # call wrapper.
        self._api_key = api_key
        # Adapter callable injected at construction time by the orchestrator.
        # It carries signature ``async structure(*, plain_text, api_key,
        # section_schema, hints) -> list[SectionInstance]``. We accept it as
        # ``Any`` to avoid an import cycle with the providers package.
        from .providers.base import LLMProvider as _LLMProviderT

        self._adapter: _LLMProviderT | None = None

    def bind_adapter(self, adapter) -> None:
        """Inject the resolved adapter. Done by the orchestrator after construction."""
        self._adapter = adapter

    async def structure_async(
        self, extracted: ExtractedDocument
    ) -> tuple[list[SectionInstance], ConfidenceReport]:
        try:
            if self._adapter is None:
                raise RuntimeError(
                    "LLMStrategy.structure_async called without a bound adapter "
                    "(use orchestrator._resolve_provider)"
                )

            sections = await self._adapter.structure(
                plain_text=extracted.plain_text,
                api_key=self._api_key,
                section_schema=_section_instance_array_schema(),
                hints=None,
            )

            # Provider success → confidence is high; consumers don't get
            # per-field confidence from the LLM yet (a future PR can request
            # structured per-field confidence from the model).
            confidence = ConfidenceReport(fields=[], overall_level="high")
            return sections, confidence
        finally:
            # Clear on success, provider error, cancellation, and validation
            # failure. Do not wait for garbage collection or object teardown.
            self._api_key = ""

    # ---------------------------------------------------------------------------
    # Backwards-compat shim — call sites using the old synchronous protocol
    # surface get a clear error instead of silent wrong-shape returns.
    # ---------------------------------------------------------------------------

    def structure(
        self, extracted: ExtractedDocument
    ) -> tuple[list[SectionInstance], ConfidenceReport]:
        raise TypeError(
            "LLMStrategy is async-only; the orchestrator awaits "
            "structure_async(...) directly. Did you mean to use "
            "RegexStrategy?"
        )


# ---------------------------------------------------------------------------
# Internal — used by the orchestrator to wrap exception messages so a
# key fragment can never reach a log line. Redaction happens INSIDE the
# adapter today; this helper exists so the orchestrator can defensively
# redact any string it received as a stray transport message.
# ---------------------------------------------------------------------------


def safe_message(message: str) -> str:
    """Redact-and-return — convenience wrapper used by orchestrator helpers."""
    return redact(message)


__all__ = [
    "ParseStrategy",
    "RegexStrategy",
    "LLMStrategy",
    "_section_instance_array_schema",
    "safe_message",
]
