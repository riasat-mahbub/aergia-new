"""Pipeline orchestrator — file bytes → typed ``ParseResult``.

Three entry points live here:

- :func:`parse_cv` — top-level dispatch. Accepts raw bytes + a MIME
  type and an optional ``(provider, api_key)`` pair. Returns a
  :class:`ParseResult` ready for the route layer.
- :func:`_parse_json_fastpath` — JSON fast-path that bypasses
  extractor/classifier/mapper and validates input straight against
  ``SectionInstance``.
- :func:`_parse_pdf` — runs the extractor → strategy → mapper pipeline
  on PDF bytes. Selects :class:`LLMStrategy` when a key+provider pair
  is supplied and the prefix matches; falls back to
  :class:`RegexStrategy` on rate-limit / transport failures or when no
  key was supplied.

The orchestrator is the only place that sets ``ParseMeta.warnings``
and selects the strategy to invoke. Layers below are pure functions.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .extract import (
    ExtractedDocument,
    extract,
    validate_section_instance_list,
)
from .keys import (
    LLMProvider,
    InvalidAPIKeyError,
    ProviderTransportError,
    RateLimitError,
    detect_provider,
)
from .schemas import ConfidenceReport, ParseMeta, ParseResult
from .strategies import LLMStrategy, RegexStrategy


# Module-level provider map; the orchestrator dispatches via this. Populated
# lazily on first use so missing SDKs (e.g. openai not installed) only fail
# when an LLM path is actually requested.
_PROVIDERS: dict[LLMProvider, Any] | None = None


def _provider_map() -> dict[LLMProvider, Any]:
    global _PROVIDERS
    if _PROVIDERS is None:
        from .providers import _ensure_adapters

        _PROVIDERS = _ensure_adapters()
    return _PROVIDERS


async def parse_cv(
    file_bytes: bytes,
    mime_type: str,
    *,
    provider: LLMProvider | None = None,
    api_key: str | None = None,
) -> ParseResult:
    """Public entry point. Async.

    :param provider: optional explicit provider (route resolves from
        form field ``provider``). When ``None``, regex path runs.
    :param api_key: optional API key (route resolves from form field
        ``api_key``). When ``None`` or empty, regex path runs.
    :raises EmptyInputError: empty input.
    :raises UnsupportedFormatError: bad MIME.
    :raises ExtractionFailedError: corrupt PDF.
    :raises InvalidAPIKeyError: provider rejected the key (the route
        maps this to HTTP 401 — the regex fallback is NEVER permitted
        for auth failures per the user's explicit decision).
    """
    if mime_type == "application/json":
        return _parse_json_fastpath(file_bytes)

    extracted = extract(file_bytes, mime_type)
    if extracted.source_format != "pdf":
        raise ValueError(f"Unexpected source format: {extracted.source_format}")

    return await _parse_pdf(extracted, provider=provider, api_key=api_key)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _parse_pdf(
    extracted: ExtractedDocument,
    *,
    provider: LLMProvider | None,
    api_key: str | None,
) -> ParseResult:
    # Validate (provider, key) shape BEFORE running the regex path so a
    # route never accepts a mis-shaped form pair.
    resolved = _resolve_provider(provider, api_key)
    if resolved is not None:
        adapter_cls, key = resolved
        strategy = LLMStrategy(provider, key)  # type: ignore[arg-type]
        strategy.bind_adapter(adapter_cls())
        try:
            sections, confidence = await strategy.structure_async(extracted)
        except InvalidAPIKeyError:
            # Auth failures are fatal — never silent-fallback to regex.
            raise
        except (RateLimitError, ProviderTransportError) as e:
            warnings = _baseline_warnings(extracted, [], _low_confidence())
            warnings.append("llm_failed_fallback_to_regex")
            warnings.append(f"llm_failed:{type(e).__name__}")
            sections, confidence = RegexStrategy().structure(extracted)
            return ParseResult(
                sections=sections,
                confidence=confidence,
                meta=ParseMeta(source="regex", warnings=warnings),
            )

        warnings = _baseline_warnings(extracted, sections, confidence)
        warnings.append("llm_used")
        return ParseResult(
            sections=sections,
            confidence=confidence,
            meta=ParseMeta(source="llm", warnings=warnings),
        )

    # Regex path (no key provided, no provider resolved, or no pair)
    sections, confidence = RegexStrategy().structure(extracted)
    warnings = _baseline_warnings(extracted, sections, confidence)
    return ParseResult(
        sections=sections,
        confidence=confidence,
        meta=ParseMeta(source="regex", warnings=warnings),
    )


def _resolve_provider(
    provider: LLMProvider | None, api_key: str | None
) -> tuple[Any, str] | None:
    """Return (adapter_cls, api_key) if both are present and consistent.

    Either ``api_key`` empty/missing or ``provider`` missing → return
    ``None`` (regex path). When both are provided, the key's prefix is
    matched against the provider; a mismatch raises :class:`ValueError`
    so the route surfaces a clear 400.
    """
    if api_key is None or api_key.strip() == "":
        return None
    if provider is None:
        raise ValueError("provider is required when api_key is supplied")

    detected = detect_provider(api_key)
    if detected != provider:
        raise ValueError(
            f"api_key looks like {detected.value!r} but provider={provider.value!r}"
        )
    cls = _provider_map()[provider]
    return cls, api_key


def _baseline_warnings(
    extracted: ExtractedDocument,
    sections: list,
    confidence: ConfidenceReport,
) -> list[str]:
    """Mirror the v0 warnings set so the LLM path inherits the same shape."""
    warnings: list[str] = []
    if not extracted.plain_text.strip():
        warnings.append("scanned_pdf_text_empty")
    if any(s.type == "extras" for s in sections):
        warnings.append("parsed_with_unmapped_content")
    if confidence.overall_level == "low":
        warnings.append("low_confidence_regex_parse")
    return warnings


def _low_confidence() -> ConfidenceReport:
    return ConfidenceReport(fields=[], overall_level="low")


def _parse_json_fastpath(file_bytes: bytes) -> ParseResult:
    """Validate a JSON ``SectionInstance[]`` payload straight through.

    Used internally for our own CV rows; the multipart PDF route does NOT
    accept JSON in v1 — the route's ``ALLOWED_MIME`` gates that.
    """
    try:
        sections = validate_section_instance_list(file_bytes)
    except ValidationError:
        # Re-raise — the route maps it to 400.
        raise

    return ParseResult(
        sections=sections,
        confidence=ConfidenceReport(fields=[], overall_level="high"),
        meta=ParseMeta(source="regex", warnings=["json_fastpath"]),
    )


# Re-export for backward-compat if anyone imports the helpers directly.
_ = json  # used implicitly by validate_section_instance_list


__all__ = ["parse_cv"]
