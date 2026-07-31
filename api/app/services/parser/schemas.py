"""Internal data contracts for the PDF/JSON parser pipeline.

These models are NOT exported to the frontend codegen output. The TypeScript
generator (``api/scripts/codegen_schema.py``) only discovers Pydantic models
in ``app.schema.models``. Parser-internal models stay inside the parser
package as long as they don't represent wire/HTTP shapes the frontend
consumes; only :class:`ParseResult` is used at the route boundary.

Public source of truth for a parsed CV is :class:`app.schema.models.SectionInstance`.
Each ``ParseResult.sections`` element must round-trip through
``SectionInstance.model_validate`` and is the same shape the existing
``build_document`` accepts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schema.models import SectionInstance


class TextBlock(BaseModel):
    """A single text span with layout geometry from a PDF page."""

    model_config = ConfigDict(extra="ignore")

    text: str
    x: float
    y: float
    width: float
    height: float
    font_size: float
    is_bold: bool
    page: int
    # URIs attached to this block's bbox via /Annots [/A /URI]; default empty
    # so callers that don't care about link extraction can ignore it.
    links: list[str] = []


class ExtractedDocument(BaseModel):
    """Output of the extraction layer.

    ``blocks`` keeps raw extraction order (not reading-order). ``columns``
    clusters blocks per page by x-position. ``plain_text`` is the
    reading-order flattened string used by the classifier.
    """

    model_config = ConfigDict(extra="ignore")

    blocks: list[TextBlock]
    plain_text: str
    columns: list[list[TextBlock]]
    source_format: Literal["pdf", "json"]


class FieldConfidence(BaseModel):
    """A single field's parse confidence.

    ``path`` is a tuple mirroring a Pydantic-flavoured access pattern,
    e.g. ``("experience", 0, "position")``.
    """

    model_config = ConfigDict(extra="ignore")

    path: tuple[str | int, ...]
    level: Literal["high", "medium", "low"]


class ConfidenceReport(BaseModel):
    """Aggregate confidence across one parse."""

    model_config = ConfigDict(extra="ignore")

    fields: list[FieldConfidence]
    overall_level: Literal["high", "medium", "low"]


class ParseMeta(BaseModel):
    """Provenance and non-fatal diagnostics for a parse.

    ``source`` widens to include ``"llm"`` once the LLM strategy ships.
    ``warnings`` carry non-fatal flags like ``scanned_pdf_text_empty`` or
    ``parsed_with_unmapped_content`` for the frontend to surface as
    info-toasts.
    """

    model_config = ConfigDict(extra="ignore")

    source: Literal["regex", "llm"]
    warnings: list[str]


class ParseResult(BaseModel):
    """Final output of the parser pipeline.

    The frontend consumes this directly to populate the existing builder UI;
    no additional transformation is needed.
    """

    model_config = ConfigDict(extra="ignore")

    sections: list[SectionInstance]
    confidence: ConfidenceReport
    meta: ParseMeta


__all__ = [
    "TextBlock",
    "ExtractedDocument",
    "FieldConfidence",
    "ConfidenceReport",
    "ParseMeta",
    "ParseResult",
]
