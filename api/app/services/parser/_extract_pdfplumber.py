"""PDF extraction via pdfplumber.

Used when ``Settings.parser_backend == "pdfplumber"`` (the default). This
replaces the visitor-mode synthesis in :mod:`app.services.parser.extract`
with pdfplumber's pre-resolved CTM machinery — every word arrives in
PDF-native top-down coords and every link arrives with a bbox in the
same space. The CTM-tracking subsystem (hand-rolled text matrix,
``_TEXT_CTM_SCALE``, ``_y_is_page_space``) is no longer needed.

The output shape is identical to :func:`extract._extract_pdf`: a
:class:`ExtractedDocument` whose ``blocks`` are :class:`TextBlock`
records with the same ``links`` field populated. The classifier and
mapper consume that shape unchanged.

**Line grouping.** pdfplumber's ``page.extract_text_lines()`` already
clusters words on the same visual line, including date rails on the
right margin (a body line at x≈24-300 plus a date rail at x≈480-575
become one line whose ``x0..x1`` spans both). We use that grouping
verbatim — re-clustering words ourselves would re-introduce the
column-aware interleaving that the lines API was designed to avoid.

**Font info.** The lines API doesn't propagate per-word fontname/size
through ``extra_attrs`` (only the chars sub-list carries it). We
collect per-word font info via ``page.extract_words(extra_attrs=...)``
and pick the dominant font/size for each line by majority vote.
"""

from __future__ import annotations

import io
from collections import Counter
from typing import Any
from ._fonts import _infer_font
from .schemas import ExtractedDocument, TextBlock


_LINK_OVERLAP_TOLERANCE = 1.0
"""Points of tolerance when matching a hyperlink rect to a text block bbox.

Both anchors use pdfplumber's top-down ``top``/``bottom``. The Chromium
generator places link rects a fraction of a point above/below the visible
glyphs; this tolerance absorbs the gap without admitting unrelated nearby
lines.
"""

_LINE_MATCH_TOLERANCE = 2.0
"""Maximum ``top`` distance (in PDF points) between a line from
``extract_text_lines()`` and a word from ``extract_words()`` for the word
to count toward that line's font/size vote. ``2.0`` covers Chromium's
vertical-metrics drift between glyphs of the same line.
"""


def extract_with_pdfplumber(file_bytes: bytes) -> ExtractedDocument:
    """Pull text + per-line font metadata + link annotations via pdfplumber.

    Opens the PDF in-memory, walks each page with
    ``page.extract_text_lines()`` (line grouping) and
    ``page.extract_words(extra_attrs=["fontname", "size"])`` (per-word
    font metadata). Each line becomes one :class:`TextBlock`; the
    block's font_size and is_bold are picked by majority-voting the
    fontname/size of words that overlap the line bbox. ``links`` are
    populated from hyperlinks whose rect overlaps the line bbox.
    """
    import pdfplumber

    blocks: list[TextBlock] = []
    plain_lines: list[str] = []
    column_groups: list[list[TextBlock]] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            lines = page.extract_text_lines()
            words = page.extract_words(
                keep_blank_chars=False,
                use_text_flow=True,
                extra_attrs=["fontname", "size"],
            )
            page_hyperlinks = page.hyperlinks
            page_blocks = _build_page_blocks(lines, words, page_index)
            for block in page_blocks:
                _attach_hyperlinks_to_block(block, page_hyperlinks)
            blocks.extend(page_blocks)
            column_groups.append(page_blocks)
            plain_lines.extend(b.text for b in page_blocks)

    return ExtractedDocument(
        blocks=blocks,
        plain_text="\n".join(plain_lines),
        columns=column_groups,
        source_format="pdf",
    )


def _build_page_blocks(
    lines: list[dict[str, Any]],
    words: list[dict[str, Any]],
    page_index: int,
) -> list[TextBlock]:
    """Turn lines + per-word font info into TextBlocks for one page.

    Each line becomes one TextBlock. The line's font metadata is the
    majority-vote family + size across the words whose ``top`` is within
    ``_LINE_MATCH_TOLERANCE`` of the line's ``top``. That vote handles
    right-rail date text on the same line as bold body text: the
    majority of words on the line carry the dominant style.
    """
    if not lines:
        return []
    blocks: list[TextBlock] = []
    for line in lines:
        text = (line.get("text") or "").strip()
        if not text:
            continue
        x0 = float(line["x0"])
        top = float(line["top"])
        x1 = float(line["x1"])
        bottom = float(line["bottom"])
        family, size = _majority_font_for_line(line, words)
        size, is_bold = _infer_font(text, family, size)
        blocks.append(
            TextBlock(
                text=text,
                x=x0,
                y=top,
                width=x1 - x0,
                height=bottom - top,
                font_size=size,
                is_bold=is_bold,
                page=page_index,
            )
        )
    return blocks


def _majority_font_for_line(
    line: dict[str, Any], words: list[dict[str, Any]]
) -> tuple[str, float]:
    """Pick the dominant fontname + size for one line.

    Counts the family/size pairs across all words whose ``top`` is
    within ``_LINE_MATCH_TOLERANCE`` of the line's ``top``. Returns
    ``("", 0.0)`` when no word matches — the caller falls back to the
    default in that case via ``_infer_font``.
    """
    line_top = float(line["top"])
    family_counter: Counter[str] = Counter()
    size_total = 0.0
    size_count = 0
    for word in words:
        if abs(float(word["top"]) - line_top) > _LINE_MATCH_TOLERANCE:
            continue
        family = _strip_fontname_prefix(word.get("fontname") or "")
        if family:
            family_counter[family] += 1
        size = float(word.get("size") or 0)
        if size > 0:
            size_total += size
            size_count += 1
    if not family_counter:
        return "", (size_total / size_count) if size_count else 0.0
    family = family_counter.most_common(1)[0][0]
    avg_size = size_total / size_count if size_count else 0.0
    return family, avg_size


def _strip_fontname_prefix(fontname: str) -> str:
    """Strip the ``AAAAAA+`` subset prefix pdfplumber inherits from pypdf.

    ``AAAAAA+NotoSans-Bold`` → ``NotoSans-Bold``.
    """
    if "+" in fontname:
        return fontname.split("+", 1)[1]
    return fontname


def _attach_hyperlinks_to_block(
    block: TextBlock, hyperlinks: list[dict[str, Any]]
) -> None:
    """Copy matching hyperlink URIs into ``block.links``.

    A hyperlink matches when its rect overlaps the block's bbox with
    ``_LINK_OVERLAP_TOLERANCE`` slack on every axis. Both rects are in
    pdfplumber's top-down coords (``top``/``bottom``), so no flipping
    is required.
    """
    if not hyperlinks:
        return

    block_x0 = block.x - _LINK_OVERLAP_TOLERANCE
    block_y0 = block.y - _LINK_OVERLAP_TOLERANCE
    block_x1 = block.x + block.width + _LINK_OVERLAP_TOLERANCE
    block_y1 = block.y + block.height + _LINK_OVERLAP_TOLERANCE

    for link in hyperlinks:
        uri = link.get("uri")
        if not uri:
            continue
        lx0 = float(link.get("x0", 0))
        ltop = float(link.get("top", 0))
        lx1 = float(link.get("x1", 0))
        lbottom = float(link.get("bottom", 0))
        if lx1 < block_x0 or lx0 > block_x1:
            continue
        if lbottom < block_y0 or ltop > block_y1:
            continue
        block.links.append(str(uri))


__all__ = ["extract_with_pdfplumber"]
