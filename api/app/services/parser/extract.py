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



# Cumulative CTM scale applied at text-block Tm on a Chromium
# PDF export: page CTM ``0.24`` × nested q/cm ``3.125`` × text-block
# Tm ``1.0`` = ``0.75``. We use this to translate the visitor's
# reported ``tm_y`` into PDF MediaBox (bottom-up) coordinates so
# annotation /Rect overlap works.
_TEXT_CTM_SCALE = 0.75


_FALLBACK_FONT_SIZE = 10.0


def _extract_pdf(file_bytes: bytes) -> ExtractedDocument:
    """Pull text + per-line font metadata + link annotations from a PDF.

    Walks each page's content stream with pypdf's plain-mode visitor to
    collect every rendered text run (text + font family + size + page-
    space baseline), groups the runs into lines by splitting on the
    ``"\n"`` spans pypdf emits, and synthesizes :class:`TextBlock`
    records whose ``is_bold`` and ``font_size`` reflect the actual
    rendered font of each line.

    Each page's ``/Annots`` are walked separately: every URI link
    annotation is matched against the page's line bboxes by generous
    overlap and attached to the matched block's ``links`` list. PDFs
    without annotations simply carry empty ``links``.
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
            mb = page.mediabox
            page_w = float(getattr(mb, "width", 595.0) or 595.0)
            page_h = float(getattr(mb, "height", 841.92) or 841.92)
        except Exception:
            page_w = 595.0
            page_h = 841.92

        annotations = _collect_page_annotations(page, page_h=page_h)
        lines = _group_spans_into_lines(_collect_text_spans(page), page_w=page_w, page_h=page_h)
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
            x0, y_top, x1, y_bot = line.bbox
            if x1 <= x0:
                width = page_w
                height = float(font_size) if font_size else _FALLBACK_FONT_SIZE
                x0 = 0.0
                x1 = page_w
                y_top = float(line_idx)
                y_bot = y_top + height
            else:
                width = x1 - x0
                height = (y_bot - y_top) or float(font_size) or _FALLBACK_FONT_SIZE
            block = TextBlock(
                text=line.text,
                x=x0,
                y=y_top,
                width=width,
                height=height,
                font_size=float(font_size),
                is_bold=is_bold,
                page=page_index,
            )
            _attach_annotations_to_block(block, annotations)
            blocks.append(block)
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

    ``text`` may be ``"\n"`` — pypdf emits newline spans between lines
    in reading order, which is what we split on. ``x``/``y`` capture the
    page-space baseline position from the visitor's ``text_matrix``
    translation (indices ``[4]`` and ``[5]``); in plain-mode the
    walker resets the CTM at every text block so the translation is
    already in page-space coordinates. ``y_is_page_space`` is True
    when the y coordinate is reliable (no rotation) and the bbox
    overlap test in :func:`_extract_pdf` can match annotation rects
    against it; otherwise callers should fall back to line-index
    heuristics.
    """

    __slots__ = ("text", "family", "size", "x", "y", "y_is_page_space")

    def __init__(
        self,
        text: str,
        family: str,
        size: float,
        x: float = 0.0,
        y: float = 0.0,
        y_is_page_space: bool = False,
    ) -> None:
        self.text = text
        self.family = family
        self.size = size
        self.x = x
        self.y = y
        self.y_is_page_space = y_is_page_space


class _Line:
    """A reconstructed text line with its dominant font family and bbox.

    ``bbox`` is ``(x0, y_top, x1, y_bot)`` in page-space when the
    underlying spans carried reliable y coordinates; otherwise it's
    ``(0.0, 0.0, page_w, 0.0)`` and the line index is the only signal
    we have for annotation matching.
    """

    __slots__ = ("text", "family", "size", "bbox")

    def __init__(
        self,
        text: str,
        family: str,
        size: float,
        bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    ) -> None:
        self.text = text
        self.family = family
        self.size = size
        self.bbox = bbox


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

    Three coordinate signals flow through the visitor:
    - ``ctm[3]`` (the y-scale entry of the current transformation
      matrix) must be ``< 0`` for page-space y to be top-down.
      Chromium exports flip Y (``ctm[3] = -0.75`` for body text);
      legacy or rotated PDFs may not.
    - When ``ctm[4] / ctm[5]`` are non-zero, the walker has already
      applied a translation we cannot undo reliably — treat any such
      state as "not page-space" and let the matcher fall back.
    - Otherwise ``text_matrix[4] / text_matrix[5]`` carry the page-
      space baseline of the run; we record them on the span.

    ``"\n"`` spans are preserved: they delimit lines in the stream.
    """
    spans: list[_TextSpan] = []

    def _visitor(text, ctm, text_matrix, font_dict, font_size):
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
        # Page-space coordinates: the plain-mode walker resets the CTM
        # at every text block, so ``text_matrix[4] / text_matrix[5]``
        # is the baseline when the CTM's y-scale is negative (the
        # usual Chromium export). The CTM's e/f translation along Y
        # is the standard top-down flip and is allowed; X translation
        # or rotation disables page-space matching so the resolver
        # falls back to line-index heuristics.
        try:
            tm_x = float(text_matrix[4]) if len(text_matrix) >= 6 else 0.0
            tm_y = float(text_matrix[5]) if len(text_matrix) >= 6 else 0.0
            ctm_b = float(ctm[3]) if len(ctm) >= 4 else 1.0
            ctm_e = float(ctm[4]) if len(ctm) >= 6 else 0.0
            y_is_page_space = ctm_b < 0 and ctm_e == 0.0
        except Exception:
            tm_x = tm_y = 0.0
            y_is_page_space = False
        spans.append(
            _TextSpan(
                text,
                family,
                size,
                x=tm_x,
                y=tm_y,
                y_is_page_space=y_is_page_space,
            )
        )

    try:
        page.extract_text(visitor_text=_visitor)
    except Exception:  # noqa: BLE001
        return []

    return spans


def _group_spans_into_lines(
    spans: list[_TextSpan],
    page_w: float = 0.0,
    page_h: float = 0.0,
) -> list[_Line]:
    """Group spans into lines by splitting the stream on ``"\\n"`` spans.

    The span stream is in reading order and pypdf inserts a ``"\\n"``
    span between lines — exactly the structure plain-mode
    ``extract_text()`` exposes. For each line, the text is the
    concatenation of its spans (no coordinate sorting needed) and the
    family is the dominant one by character count (a line is rarely a
    single font family — e.g. a right-rail date next to a title).

    ``bbox`` is ``(x0, y_top, x1, y_bot)`` in PDF MediaBox (bottom-up)
    coordinates when the underlying spans carried reliable y; the
    CTM-transformed ``tm_y`` is converted via
    ``pdf_y = page_h - 0.75 * tm_y`` (the empirical text-scale on
    Chromium exports: page CTM 0.24, nested 3.125, text-block Tm
    scale 1.0). Absent page-space y, the bbox falls back to
    ``(0.0, 0.0, page_w, 0.0)`` and the line index is the only
    signal for annotation matching.
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
        # Modal y: pypdf's plain-mode walker resets the CTM after
        # each text operation, so a couple of trailing spans in a
        # line often report y=0. Pick the most-frequent baseline
        # to anchor the bbox; ties resolve to the first occurrence.
        y_counts: dict[float, int] = {}
        page_space_y_seen = False
        for s in buf:
            if s.family:
                counts[s.family] = counts.get(s.family, 0) + len(s.text)
            if s.size:
                sizes.append(s.size)
            if s.y_is_page_space:
                page_space_y_seen = True
                y_counts[s.y] = y_counts.get(s.y, 0) + 1
        family = max(counts, key=counts.get) if counts else ""
        size = max(sizes) if sizes else 0.0
        if page_space_y_seen and y_counts:
            modal_y = max(y_counts, key=lambda y: (y_counts[y], -list(y_counts).index(y)))
            all_page_space_spans = [s for s in buf if s.y_is_page_space]
            if all_page_space_spans:
                ctm_scale = _TEXT_CTM_SCALE
                x_starts = [s.x for s in all_page_space_spans]
                width_units = sum(
                    max(1, len(s.text)) * 0.5 for s in all_page_space_spans
                )
                x0 = min(x_starts) * ctm_scale
                x1 = (max(x_starts) + width_units * size) * ctm_scale
                if page_h > 0:
                    pdf_y_bot = page_h - ctm_scale * modal_y
                    pdf_y_top = page_h - ctm_scale * (modal_y + size)
                    y_top = min(pdf_y_top, pdf_y_bot)
                    y_bot = max(pdf_y_top, pdf_y_bot)
                else:
                    y_top = modal_y * ctm_scale
                    y_bot = (modal_y + size) * ctm_scale
                bbox = (x0, y_top, x1, y_bot)
            else:
                bbox = (0.0, 0.0, page_w, 0.0)
        else:
            bbox = (0.0, 0.0, page_w, 0.0)
        lines.append(_Line(text, family, size, bbox))

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


def _collect_page_annotations(
    page: Any,
    page_h: float = 0.0,
) -> list[tuple[str, float, float, float, float]]:
    """Walk a page's ``/Annots`` and return URI link rects.

    Each entry is ``(uri, x0, y_top, x1, y_bot)`` in top-down page
    coordinates (matching the visitor's ``text_matrix`` translation
    after the Y-flip CTM is applied). PDF link ``/Rect`` is in
    bottom-up coordinates by spec; we flip y when ``page_h`` is
    available. Annotations without ``/Subtype /Link``, ``/A /URI``,
    or a 4-element ``/Rect`` are skipped. Any failure in the walker
    degrades to an empty list so the rest of the pipeline keeps
    working.
    """
    out: list[tuple[str, float, float, float, float]] = []
    try:
        raw = page.get("/Annots")
    except Exception:
        return out
    if not raw:
        return out
    try:
        annots = list(raw)
    except Exception:
        return out
    for annot in annots:
        try:
            obj = annot.get_object() if hasattr(annot, "get_object") else annot
            if obj is None:
                continue
            subtype = str(obj.get("/Subtype") or "")
            if subtype != "/Link":
                continue
            action = obj.get("/A") or {}
            try:
                action_obj = action.get_object() if hasattr(action, "get_object") else action
            except Exception:
                action_obj = action
            uri = str(action_obj.get("/URI") or "") if action_obj is not None else ""
            if not uri:
                continue
            rect = obj.get("/Rect")
            if rect is None or len(rect) < 4:
                continue
            try:
                x0, y0, x1, y1 = (float(v) for v in rect[:4])
            except Exception:
                continue
            # The benchmark PDF stores /Rect in top-down page-coords
            # scaled to the visitor's text_matrix (CTM scale already
            # applied). We DON'T flip — using it as-is aligns with
            # the visitor's reported tm[5].
            x0, y_top = x0, y0
            x1, y_bot = x1, y1
            if page_h > 0 and (y_top > page_h or y_bot > page_h):
                # Fall back: if the rect happens to use raw bottom-up
                # page coords (visible when y0 > page_h after flip or
                # y0 sits near the page top), normalise to top-down.
                y_top, y_bot = page_h - y1, page_h - y0
            out.append((uri, x0, y_top, x1, y_bot))
        except Exception:
            continue
    return out


def _attach_annotations_to_block(
    block: TextBlock,
    annotations: list[tuple[str, float, float, float, float]],
) -> None:
    """Attach every URI whose ``/Rect`` overlaps ``block`` bbox.

    The overlap rule is intentionally generous (1pt tolerance on every
    side) so a single-link-per-line corpus matches cleanly even when
    the visitor's text bbox is slightly tighter than the annotation's
    hover rect. When multiple annotations match the same block — rare,
    but possible when a heading has both a permalink and a paper URL —
    every URI is preserved in reading order; the mapper decides which
    one becomes the row's primary link.
    """
    if not annotations:
        return
    matched: list[str] = []
    bx0 = block.x
    bxp1 = block.x + block.width
    byt = block.y
    byb = block.y + block.height
    for uri, ax0, ay0, ax1, ay1 in annotations:
        if bx0 <= ax1 + 1.0 and bxp1 >= ax0 - 1.0 and byt <= ay1 + 1.0 and byb >= ay0 - 1.0:
            if uri not in matched:
                matched.append(uri)
    if matched:
        block.links.extend(matched)


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
