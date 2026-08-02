"""Extraction layer — file bytes → :class:`ExtractedDocument`.

The dispatcher routes by MIME type:

- ``application/pdf`` → :func:`extract_with_pdfplumber` (pdfminer.six via
  pdfplumber; resolves the cumulative CTM and exposes ``page.hyperlinks``
  in the same coordinate space as ``page.extract_text_lines``);
- ``application/json`` → empty :class:`ExtractedDocument` for the
  orchestrator's type-discrimination branch (the JSON fast-path itself
  lives in :mod:`app.services.parser.imports`).

A non-JSON / non-PDF mime raises :class:`UnsupportedFormatError`. Empty
input raises :class:`EmptyInputError`. PDFs that pdfminer can't read at
all raise :class:`ExtractionFailedError`.

Font-name-based bold inference (``NotoSans-Bold`` ⇒ ``is_bold=True``)
lives in :mod:`app.services.parser._fonts` so the pdfplumber backend can
import it without dragging in this dispatcher.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.schema.models import SectionInstance

from ._extract_pdfplumber import extract_with_pdfplumber
from .schemas import ExtractedDocument


try:
    from pdfplumber.utils.exceptions import PdfminerException

    _PDFPLUMBER_EXCEPTIONS: tuple[type[BaseException], ...] = (
        PdfminerException,
        ValueError,  # pdfminer raises ValueError on certain truncation cases
        OSError,     # pdfminer opens a real file handle; IO errors propagate
    )
except Exception:  # noqa: BLE001 - pdfplumber may be uninstalled during tests
    _PDFPLUMBER_EXCEPTIONS = (Exception,)


# ---------------------------------------------------------------------------
# Public errors
# ---------------------------------------------------------------------------


class ParserError(Exception):
    """Base for parse failures that map to specific HTTP status codes."""


class UnsupportedFormatError(ParserError):
    """The MIME type is not one of the supported input formats."""

    def __init__(self, mime_type: str) -> None:
        super().__init__(f"Unsupported file type: {mime_type}")
        self.mime_type = mime_type


class EmptyInputError(ParserError):
    """The input bytes were empty."""

    def __init__(self) -> None:
        super().__init__("Empty input file")


class ExtractionFailedError(ParserError):
    """The extractor could not parse the input (e.g. corrupt PDF)."""


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


SUPPORTED_MIME = ("application/pdf", "application/json")


def extract(file_bytes: bytes, mime_type: str) -> ExtractedDocument:
    """Dispatch extraction by MIME type.

    Raises :class:`EmptyInputError` when ``file_bytes`` is empty.
    Raises :class:`UnsupportedFormatError` for unknown MIME types.
    Raises :class:`ExtractionFailedError` when the PDF cannot be parsed.
    """
    if not file_bytes:
        raise EmptyInputError()

    if mime_type == "application/pdf":
        try:
            return extract_with_pdfplumber(file_bytes)
        except _PDFPLUMBER_EXCEPTIONS as exc:  # noqa: BLE001
            raise ExtractionFailedError(f"Could not read PDF: {exc}") from exc

    if mime_type == "application/json":
        # The JSON fast-path lives in ``imports.py``; this dispatcher just
        # produces an empty ExtractedDocument for the orchestrator's
        # type-discrimination branch.
        try:
            decoded = file_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ExtractionFailedError(f"Invalid UTF-8 in JSON: {e}") from e
        try:
            json.loads(decoded)
        except json.JSONDecodeError as e:
            raise ExtractionFailedError(f"Invalid JSON: {e}") from e
        return ExtractedDocument(
            blocks=[],
            plain_text="",
            columns=[],
            source_format="json",
        )

    raise UnsupportedFormatError(mime_type)


# ---------------------------------------------------------------------------
# JSON fast-path (validation only — the orchestrator consumes the bytes)
# ---------------------------------------------------------------------------


def validate_section_instance_list(file_bytes: bytes) -> list[SectionInstance]:
    """Validate a JSON array of SectionInstance dicts.

    Used by the orchestrator's JSON fast-path. ``file_bytes`` must decode
    as a UTF-8 JSON array; raises :class:`ValidationError` for any element
    that doesn't satisfy the closed :class:`SectionInstance` schema.
    """
    try:
        payload = json.loads(file_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExtractionFailedError(f"Invalid JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise ValidationError.from_exception_data(
            title="SectionInstance",
            line_errors=[
                {
                    "type": "list_required",
                    "loc": (),
                    "input": payload,
                    "msg": "Expected a JSON array of SectionInstance dicts",
                }
            ],
        )

    return [SectionInstance.model_validate(item) for item in payload]


__all__ = [
    "ParserError",
    "UnsupportedFormatError",
    "EmptyInputError",
    "ExtractionFailedError",
    "extract",
    "validate_section_instance_list",
    "SUPPORTED_MIME",
]
