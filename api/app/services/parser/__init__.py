"""Parser package — CV import pipeline (PDF → AST → SectionInstance list).

Public surface:

- :func:`parse_cv` — top-level entry point; accepts raw bytes + MIME type
  and returns a typed :class:`ParseResult`.
- :class:`ParseResult` and friends — Pydantic shapes carried over HTTP.
- :class:`RegexStrategy`, :class:`LLMStrategy` — the strategy seam.
- :class:`UnsupportedFormatError`, :class:`EmptyInputError`,
  :class:`ExtractionFailedError` — error mapping keys.
"""

from __future__ import annotations

from app.services.parser.extract import (
    EmptyInputError,
    ExtractionFailedError,
    ParserError,
    UnsupportedFormatError,
)
from app.services.parser.imports import parse_cv
from app.services.parser.schemas import (
    ConfidenceReport,
    ExtractedDocument,
    FieldConfidence,
    ParseMeta,
    ParseResult,
    TextBlock,
)
from app.services.parser.strategies import LLMStrategy, RegexStrategy

__all__ = [
    "parse_cv",
    "ParseResult",
    "ParseMeta",
    "ConfidenceReport",
    "FieldConfidence",
    "TextBlock",
    "ExtractedDocument",
    "RegexStrategy",
    "LLMStrategy",
    "ParserError",
    "UnsupportedFormatError",
    "EmptyInputError",
    "ExtractionFailedError",
]
