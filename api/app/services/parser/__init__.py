"""Parser package — CV import pipeline (PDF → AST → SectionInstance list).

Public surface:

- :func:`parse_cv` — top-level entry point; accepts raw bytes + MIME
  type and optional ``(provider, api_key)`` and returns a typed
  :class:`ParseResult`.
- :class:`ParseResult` and friends — Pydantic shapes carried over HTTP.
- :class:`RegexStrategy`, :class:`LLMStrategy` — the strategy seam.
- :class:`LLMProvider`, :func:`detect_provider`,
  :class:`UnknownProviderError`, :class:`InvalidAPIKeyError` — the
  LLM-specific re-export surface used by the route layer.
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
from app.services.parser.keys import (
    InvalidAPIKeyError,
    LLMProvider,
    UnknownProviderError,
    detect_provider,
)
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
    "LLMProvider",
    "detect_provider",
    "UnknownProviderError",
    "InvalidAPIKeyError",
    "ParserError",
    "UnsupportedFormatError",
    "EmptyInputError",
    "ExtractionFailedError",
]
