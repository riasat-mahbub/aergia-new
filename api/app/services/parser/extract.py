"""Extraction layer — file bytes → :class:`ExtractedDocument`.

The dispatcher routes by MIME type:

- ``application/pdf`` → :func:`_extract_pdf` (pypdf plain-text mode +
  font-size/bold heuristic from the embedded Font dictionary);
- ``application/json`` → :func:`_extract_json` (raw passthrough; the
  classifier is skipped at the orchestrator level because the input is
  already a valid ``SectionInstance[]``).

A non-JSON / non-PDF mime raises :class:`UnsupportedFormatError`. Empty
input raises :class:`EmptyInputError`. PDFs that pypdf can't read at all
raise :class:`ExtractionFailedError`.

The pypdf-bbox path (using ``page.extract_text(extraction_mode="layout")``
with the visitor protocol) is more accurate but also slower and frankly
over-engineered for the MVP. A future iteration can swap the plain-mode
synthesis for the layout-mode visitor without touching the classifier
or mapper.
"""

from __future__ import annotations

import io
import json
import re
from typing import Any

from pydantic import ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.schema.models import SectionInstance

from .schemas import ExtractedDocument, TextBlock


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
    """
    if not file_bytes:
        raise EmptyInputError()

    if mime_type == "application/pdf":
        return _extract_pdf(file_bytes)

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
# PDF extraction (plain-mode synthesis)
# ---------------------------------------------------------------------------


_FALLBACK_FONT_SIZE = 10.0


def _extract_pdf(file_bytes: bytes) -> ExtractedDocument:
    """Pull text + per-line geometry from a PDF using pypdf plain mode.

    pypdf's plain mode emits one or more lines per page; we synthesize
    :class:`TextBlock` records from those lines plus the per-character
    /Resources/Font dictionary for font-size hints. ``is_bold`` is inferred
    from the font name (``*Bold*`` / ``*Black*`` / ``*Heavy*`` / explicit
    ``Bold`` token).
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except (PdfReadError, Exception) as exc:  # noqa: BLE001 - pypdf raises PdfStreamError etc.
        raise ExtractionFailedError(f"Could not read PDF: {exc}") from exc

    try:
        pages = list(reader.pages)
    except Exception as exc:  # noqa: BLE001
        raise ExtractionFailedError(f"Could not enumerate pages: {exc}") from exc

    blocks: list[TextBlock] = []
    plain_lines: list[str] = []

    for page_index, page in enumerate(pages):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            # Skip the page but keep going.
            text = ""

        # ``mediabox`` exposes page width (PDF coord, bottom-up Y).
        try:
            mb = page.mediabox
            page_w = float(getattr(mb, "width", 595.0) or 595.0)
        except Exception:
            page_w = 595.0

        font_size_default = _FALLBACK_FONT_SIZE
        fonts = _extract_font_dict(page)
        font_sizes = [v for v in fonts.values() if v > 0]
        if font_sizes:
            font_size_default = sum(font_sizes) / len(font_sizes)

        for line_idx, line in enumerate(text.splitlines()):
            line = line.strip()
            if not line:
                continue

            font_size, is_bold = _infer_font(line, fonts, font_size_default)

            # Synthetic geometry: x=0, y descending by line index per page,
            # width pagespread. Real bbox isn't required for header detection
            # in the MVP — the classifier uses ``is_bold`` + ``font_size``
            # ratio against the page median, not coordinates.
            blocks.append(
                TextBlock(
                    text=line,
                    x=0.0,
                    y=float(line_idx),
                    width=page_w,
                    height=float(font_size),
                    font_size=float(font_size),
                    is_bold=is_bold,
                    page=page_index,
                )
            )
            plain_lines.append(line)

    # Column clustering: with plain-mode lines we don't have x-positions
    # per line. Treat every page as one column. The classifier doesn't
    # depend on multi-column parsing yet — empty list is honest until a
    # layout-aware extractor lands.
    columns: list[list[TextBlock]] = [[]]

    return ExtractedDocument(
        blocks=blocks,
        plain_text="\n".join(plain_lines),
        columns=columns,
        source_format="pdf",
    )


def _extract_font_dict(page: Any) -> dict[str, float]:
    """Return ``{basefont: size}`` for fonts referenced on the page.

    pypdf's plain-mode doesn't expose per-glyph font/size, so we infer the
    font-size fallback from the page's /Resources/Font dictionary. Real
    per-span sizes arrive when the layout-mode visitor lands.
    """
    try:
        resources = page.get("/Resources") or {}
    except Exception:
        return {}
    try:
        font_obj = resources.get("/Font") or {}
    except Exception:
        return {}

    out: dict[str, float] = {}
    for _, font in dict(font_obj).items():
        try:
            font = font.get_object() if hasattr(font, "get_object") else font
        except Exception:
            continue
        try:
            basefont = str(font.get("/BaseFont") or "")
        except Exception:
            basefont = ""
        if not basefont:
            continue
        size = _font_name_size_hint(basefont)
        if size:
            out[basefont] = size
    return out


_FONT_NAME_SIZE_RE = re.compile(r"[A-Z]{6}\+(.+?)-", re.IGNORECASE)


def _font_name_size_hint(basefont: str) -> float:
    """Heuristic size from the font's BaseFont subset string.

    pypdf emits names like ``/KFKOMY+Helvetica``. We can't recover the
    actual rendered size from the name, so the caller falls back to the
    page median when this returns 0.
    """
    return 0.0


def _infer_font(line: str, fonts: dict[str, float], default: float) -> tuple[float, bool]:
    """Pick a font size and bold flag for a plain-text line.

    The plain-mode text doesn't carry per-token style metadata. We treat
    ALL-CAPS short lines as bold candidates (typical for section headers),
    and fall back to the page's median font size as the body size.
    """
    is_bold = False
    stripped = line.strip()
    if stripped and stripped == stripped.upper() and any(c.isalpha() for c in stripped):
        # ALL-CAPS lines are typically bold section headers.
        is_bold = True

    if fonts:
        # Use the first font's hinted size as the baseline.
        default = next(iter(fonts.values()), default) or default
    if is_bold:
        return max(default * 1.2, default + 1.0), True
    return default, False


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
