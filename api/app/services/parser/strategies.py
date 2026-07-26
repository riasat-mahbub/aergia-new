"""Strategy protocol — the seam between regex and (future) LLM paths.

The :class:`ParseStrategy` protocol lives here so adding a new path means
implementing one class without touching the orchestrator. ``RegexStrategy``
ships today; ``LLMStrategy`` is a stub raising :class:`NotImplementedError`
until provider adapters and key handling are built.
"""

from __future__ import annotations

from typing import Protocol

from app.schema.models import SectionInstance

from .schemas import ConfidenceReport, ExtractedDocument


class ParseStrategy(Protocol):
    """A path that turns an :class:`ExtractedDocument` into typed sections."""

    name: str

    def structure(
        self, extracted: ExtractedDocument
    ) -> tuple[list[SectionInstance], ConfidenceReport]:
        ...


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


class LLMStrategy:
    """Stub — providers land in the next iteration.

    Wire-up checklist before this stops raising:

    1. ``app/services/parser/keys.py`` — provider detection + per-prefix
       redaction (see plan §Future LLM).
    2. ``app/services/parser/providers/{base,anthropic,openai,gemini}.py``
       — adapters that return ``list[SectionInstance]`` directly.
    3. ``ParseMeta.source`` widened to ``Literal["regex", "llm"]``.
    4. ``routes/imports.py`` accepts ``api_key`` + ``provider`` form
       fields.
    5. Strategy selection in ``imports.parse_cv`` based on provider-key
       presence; ``AuthError`` raised verbatim, 429 / parse-repair
       exhaustion fall back with a warning (per plan).
    """

    name = "llm"

    def structure(
        self, extracted: ExtractedDocument
    ) -> tuple[list[SectionInstance], ConfidenceReport]:
        raise NotImplementedError(
            "LLM path deferred — see plan §Future LLM and "
            "the LLMStrategy stub in app/services/parser/strategies.py"
        )


__all__ = ["ParseStrategy", "RegexStrategy", "LLMStrategy"]
