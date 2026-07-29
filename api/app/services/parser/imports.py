"""Pipeline orchestrator — file bytes → typed ``ParseResult``.

Three entry points live here:

- :func:`parse_cv` — top-level dispatch. Accepts raw bytes + a MIME type
  and returns a ``ParseResult`` ready for the route layer.
- :func:`_parse_json_fastpath` — JSON fast-path that bypasses
  extractor/classifier/mapper and validates input straight against
  ``SectionInstance``.
- :func:`_parse_pdf` — runs the extractor → strategy → mapper pipeline
  on PDF bytes.

The orchestrator is the only place that sets ``ParseMeta.warnings`` and
selects the strategy to invoke. Layers below are pure functions.
"""

from __future__ import annotations

import json

from pydantic import ValidationError


from .extract import (
    ExtractedDocument,
    extract,
    validate_section_instance_list,
)
from .schemas import ConfidenceReport, ParseMeta, ParseResult
from .strategies import RegexStrategy


def parse_cv(file_bytes: bytes, mime_type: str) -> ParseResult:
    """Public entry point. ``mime_type`` is one of the supported inputs.

    Raises :class:`EmptyInputError`, :class:`UnsupportedFormatError`,
    :class:`ExtractionFailedError`, or :class:`ValidationError` (JSON).
    """
    if mime_type == "application/json":
        return _parse_json_fastpath(file_bytes)

    extracted = extract(file_bytes, mime_type)
    if extracted.source_format != "pdf":
        # Currently impossible (the dispatcher routes json/pdf only) but a
        # narrow contract — keep the check.
        raise ValueError(f"Unexpected source format: {extracted.source_format}")

    return _parse_pdf(extracted)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_pdf(extracted: ExtractedDocument) -> ParseResult:
    strategy = RegexStrategy()
    sections, confidence = strategy.structure(extracted)

    warnings: list[str] = []
    if not extracted.plain_text.strip():
        warnings.append("scanned_pdf_text_empty")
    if any(s.type == "extras" for s in sections):
        warnings.append("parsed_with_unmapped_content")
    if confidence.overall_level == "low":
        warnings.append("low_confidence_regex_parse")

    return ParseResult(
        sections=sections,
        confidence=confidence,
        meta=ParseMeta(source="regex", warnings=warnings),
    )


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
