"""Extraction layer — file bytes → :class:`ExtractedDocument`.

The dispatcher routes by MIME type:

- ``application/pdf`` → :func:`_extract_pdf` (pypdf plain-mode visitor +
  font-family-based bold inference);
- ``application/json`` → :func:`_extract_json` (raw passthrough; the
  classifier is skipped at the orchestrator level because the input is
  already a valid ``SectionInstance[]``).

A non-JSON / non-PDF mime raises :class:`UnsupportedFormatError`. Empty
input raises :class:`EmptyInputError`. PDFs that pypdf can't read at all
raise :class:`ExtractionFailedError`.

Bold inference reads the actual font family from each rendered text
run. Earlier versions treated ALL-CAPS lines as bold — that heuristic
silently failed on real-world resumes with mixed-case headers
(``Experience``, ``Research``) exported by Chromium, where the fonts
are Type0 subsets (``/AAAAAA+NotoSans-Bold``) and the size-hint regex
never matched. The font-family path is reliable on that corpus.
"""

from __future__ import annotations

import io
import json
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
# PDF extraction (visitor-mode synthesis)
# ---------------------------------------------------------------------------


_FALLBACK_FONT_SIZE = 10.0


def _extract_pdf(file_bytes: bytes) -> ExtractedDocument:
    """Pull text + per-line font metadata from a PDF.

    Walks each page's content stream with pypdf's plain-mode visitor to
    collect every rendered text run (text + font family + size), groups
    the runs into lines by splitting on the ``"\\n"`` spans pypdf
    emits, and synthesizes :class:`TextBlock` records whose ``is_bold``
    and ``font_size`` reflect the actual rendered font of each line.

    Geometry is synthetic (x=0, y by line index) — the classifier keys
    off ``is_bold`` + ``font_size`` ratio, not coordinates, so real
    bboxes aren't required for header detection.
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
        # ``mediabox`` exposes page width (PDF coord, bottom-up Y).
        try:
            mb = page.mediabox
            page_w = float(getattr(mb, "width", 595.0) or 595.0)
        except Exception:
            page_w = 595.0

        lines = _group_spans_into_lines(_collect_text_spans(page))
        # If the visitor produced nothing (corrupt / degenerate page),
        # fall back to plain-mode text-only so the orchestrator still
        # surfaces *something* (the degrade behaviour matches the
        # pre-visitor contract).
        if not lines:
            try:
                fallback = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                fallback = ""
            for line_idx, line in enumerate(fallback.splitlines()):
                line = line.strip()
                if not line:
                    continue
                blocks.append(
                    TextBlock(
                        text=line,
                        x=0.0,
                        y=float(line_idx),
                        width=page_w,
                        height=_FALLBACK_FONT_SIZE,
                        font_size=_FALLBACK_FONT_SIZE,
                        is_bold=False,
                        page=page_index,
                    )
                )
                plain_lines.append(line)
            continue

        for line_idx, line in enumerate(lines):
            font_size, is_bold = _infer_font(line.text, line.family, line.size)
            blocks.append(
                TextBlock(
                    text=line.text,
                    x=0.0,
                    y=float(line_idx),
                    width=page_w,
                    height=float(font_size),
                    font_size=float(font_size),
                    is_bold=is_bold,
                    page=page_index,
                )
            )
            plain_lines.append(line.text)

    # Column clustering: with visitor-mode lines we don't have x-positions
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


# ---------------------------------------------------------------------------
# Visitor-driven text-span collection
# ---------------------------------------------------------------------------


class _TextSpan:
    """One rendered text run from the page's content stream.

    ``text`` may be ``"\\n"`` — pypdf emits newline spans between lines
    in reading order, which is what we split on. No coordinates are
    tracked: the span stream order matches plain-mode reading order,
    so line boundaries come from the newline spans, not from y math.
    """

    __slots__ = ("text", "family", "size")

    def __init__(self, text: str, family: str, size: float) -> None:
        self.text = text
        self.family = family
        self.size = size


class _Line:
    """A reconstructed text line with its dominant font family."""

    __slots__ = ("text", "family", "size")

    def __init__(self, text: str, family: str, size: float) -> None:
        self.text = text
        self.family = family
        self.size = size


def _collect_text_spans(page: Any) -> list[_TextSpan]:
    """Walk the page's content stream and return one ``_TextSpan`` per
    rendered text run, in content-stream (reading) order.

    Uses pypdf's plain-mode ``visitor_text`` callback, which receives
    ``(text, ctm, text_matrix, font_dict, font_size)`` for every text
    drawing operation. The font_dict's ``/BaseFont`` is the BaseFont
    subset string (``/AAAAAA+NotoSans-Bold``); we strip the prefix
    to get the family name (``NotoSans-Bold``).

    Two classes of spans are dropped:
    - Empty text (whitespace-only positioning moves) — no content.
    - Fontless spans (``font_dict is None``) — Chromium exports
      decorative positioning layers without a font; keeping them
      duplicates text into the wrong lines.

    ``"\\n"`` spans are preserved: they delimit lines in the stream.
    """
    spans: list[_TextSpan] = []

    def _visitor(text, _ctm, _text_matrix, font_dict, font_size):
        if not text:
            return
        if text == "\n":
            spans.append(_TextSpan("\n", "", 0.0))
            return
        if not text.strip():
            return
        if font_dict is None:
            return
        family = ""
        try:
            font = font_dict.get_object() if hasattr(font_dict, "get_object") else font_dict
            basefont = str(font.get("/BaseFont") or "")
        except Exception:
            basefont = ""
        family = _font_family_from_basefont(basefont)
        size = float(font_size) if font_size else 0.0
        spans.append(_TextSpan(text, family, size))

    try:
        page.extract_text(visitor_text=_visitor)
    except Exception:  # noqa: BLE001
        return []

    return spans


def _group_spans_into_lines(spans: list[_TextSpan]) -> list[_Line]:
    """Group spans into lines by splitting the stream on ``"\\n"`` spans.

    The span stream is in reading order and pypdf inserts a ``"\\n"``
    span between lines — exactly the structure plain-mode
    ``extract_text()`` exposes. For each line, the text is the
    concatenation of its spans (no coordinate sorting needed) and the
    family is the dominant one by character count (a line is rarely a
    single font family — e.g. a right-rail date next to a title).
    """
    if not spans:
        return []

    lines: list[_Line] = []
    buf: list[_TextSpan] = []

    def _flush() -> None:
        if not buf:
            return
        text = "".join(s.text for s in buf).strip()
        if not text:
            return
        counts: dict[str, int] = {}
        sizes: list[float] = []
        for s in buf:
            if s.family:
                counts[s.family] = counts.get(s.family, 0) + len(s.text)
            if s.size:
                sizes.append(s.size)
        family = max(counts, key=counts.get) if counts else ""
        size = max(sizes) if sizes else 0.0
        lines.append(_Line(text, family, size))

    for span in spans:
        if span.text == "\n":
            _flush()
            buf = []
        else:
            buf.append(span)
    _flush()
    return lines


def _extract_font_dict(page: Any) -> dict[str, str]:
    """Return ``{basefont: family_name}`` for fonts referenced on the page.

    The page's ``/Resources/Font`` table maps font keys to a font
    dictionary whose ``/BaseFont`` is the subset-prefixed family name
    (e.g. ``/AAAAAA+NotoSans-Bold``). The ``+`` prefix is added by the
    PDF generator for embedded subset fonts and is stripped here — the
    caller wants the family name to derive boldness.

    Earlier versions returned ``{basefont: size}`` and tried to read
    the rendered size from the BaseFont name. That never worked for
    Type0 subset fonts (the size isn't in the name), so the dictionary
    always came back empty and the extractor fell back to a constant
    page-default size. The fix is to keep the family name and let
    ``_infer_font`` decide bold from the family.
    """
    try:
        resources = page.get("/Resources") or {}
    except Exception:
        return {}
    try:
        font_obj = resources.get("/Font") or {}
    except Exception:
        return {}

    out: dict[str, str] = {}
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
        family = _font_family_from_basefont(basefont)
        if family:
            out[basefont] = family
    return out


_FONT_NAME_BOLD_TOKENS = ("bold", "semibold", "black", "heavy")


def _font_family_from_basefont(basefont: str) -> str:
    """Strip the subset prefix from a PDF BaseFont name.

    ``/AAAAAA+NotoSans-Bold`` → ``NotoSans-Bold``. The ``+`` prefix is
    added by PDF generators for embedded subset fonts; it's noise for
    bold-detection. Empty / whitespace-only input returns empty string.
    """
    if not basefont:
        return ""
    cleaned = basefont.lstrip("/")
    if "+" in cleaned:
        cleaned = cleaned.split("+", 1)[1]
    return cleaned.strip()


def _font_name_size_hint(basefont: str) -> float:
    """Heuristic size from the font's BaseFont subset string.

    pypdf emits names like ``/KFKOMY+Helvetica``. We can't recover the
    actual rendered size from the name, so the caller falls back to the
    page median when this returns 0. Retained for backwards compatibility
    with callers that still consume the float-dict shape; the new
    ``_extract_font_dict`` returns ``{basefont: family_name}`` instead.
    """
    return 0.0


def _font_family_is_bold(family: str) -> bool:
    """Return True when the font family name marks a bold weight.

    Recognises ``bold``, ``semibold``, ``black``, ``heavy`` — the four
    weights Chromium-based PDF generators emit for headers. Substring
    match (case-insensitive) is intentional: ``NotoSans-Bold`` and
    ``NotoSans-SemiBold`` both contain ``bold`` after the lowercase.
    """
    if not family:
        return False
    f = family.lower()
    return any(tok in f for tok in _FONT_NAME_BOLD_TOKENS)


def _infer_font(line: str, family: str, default: float) -> tuple[float, bool]:
    """Pick a font size and bold flag for a line given its font family.

    ``family`` is the BaseFont-derived family name (e.g. ``NotoSans-Bold``,
    ``NotoSans-Regular``). Boldness is decided from the family, not the
    line text — the old ALL-CAPS heuristic was unreliable on real-world
    resumes where headers are mixed-case.

    Returns ``(size, is_bold)``. ``size`` is the line's rendered size when
    known, otherwise ``default``. Bold lines get a small size bump so the
    classifier's ``font_size >= median * 1.15`` threshold still fires for
    body-italicized headers (defence in depth — the bold flag is the
    primary signal).
    """
    is_bold = _font_family_is_bold(family)
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
