"""Font-name bold inference tests for the PDF parser.

The parser used to flag a line as bold only when its text was ALL-CAPS
(`line == line.upper()`). Real-world resumes are mixed-case, and Chromium
embeds Type0 subset fonts whose BaseFont names never match the size-hint
regex. The fix reads the font dictionary directly and infers boldness
from the font family name.

These tests cover the two surviving primitives (now in
:mod:`app.services.parser._fonts`):

1. :func:`_font_family_from_basefont` strips the ``AAAAAA+`` subset
   prefix.
2. :func:`_infer_font` decides bold from the font family, not the text.

The pdfplumber backend applies ``_infer_font`` to the majority fontname
of each text line (see ``_extract_pdfplumber._majority_font_for_line``),
so bold flags now flow through without any visitor-mode wiring.
"""

from __future__ import annotations

from app.services.parser._fonts import (
    _font_family_from_basefont,
    _infer_font,
)


# ---------------------------------------------------------------------------
# _font_family_from_basefont
# ---------------------------------------------------------------------------


def test_font_family_from_basefont_strips_subset_prefix():
    """``/AAAAAA+NotoSans-Bold`` -> ``NotoSans-Bold``."""
    assert _font_family_from_basefont("/AAAAAA+NotoSans-Bold") == "NotoSans-Bold"


def test_font_family_from_basefont_handles_bare_name():
    """No prefix; the whole name is the family."""
    assert _font_family_from_basefont("Helvetica") == "Helvetica"


def test_font_family_from_basefont_handles_empty():
    """Empty / None becomes empty string."""
    assert _font_family_from_basefont("") == ""
    assert _font_family_from_basefont("/") == ""


# ---------------------------------------------------------------------------
# _infer_font (font-name-based)
# ---------------------------------------------------------------------------


def _looks_bold(family: str) -> bool:
    """Mirror the bold regex used inside _infer_font."""
    f = family.lower()
    return any(tok in f for tok in ("bold", "semibold", "black", "heavy"))


def test_infer_font_flags_bold_for_bold_family():
    """Family=NotoSans-Bold + line='Experience' is bold (regardless of
    the ALL-CAPS text shape)."""
    size, is_bold = _infer_font("Experience", "NotoSans-Bold", 10.0)
    assert is_bold is True
    assert size > 10.0  # bold lines get a size bump for the header detector


def test_infer_font_flags_bold_for_semibold_family():
    """NotoSans-SemiBold is treated as bold (used for section headers in
    the benchmark corpus)."""
    _size, is_bold = _infer_font("Experience", "NotoSans-SemiBold", 10.0)
    assert is_bold is True


def test_infer_font_does_not_flag_bold_for_regular_family():
    """Regular and Medium font families are not bold — even if the line
    text is ALL-CAPS. The old heuristic would have flagged them."""
    size, is_bold = _infer_font("EXPERIENCE", "NotoSans-Regular", 10.0)
    assert is_bold is False
    assert size == 10.0


def test_infer_font_drops_text_uppercase_heuristic():
    """The line == line.upper() path is gone. A lowercased line in a
    bold font is still bold; an uppercased line in a regular font is
    still not bold."""
    _, is_bold_lower = _infer_font("experience", "NotoSans-Bold", 10.0)
    _, is_bold_upper = _infer_font("EXPERIENCE", "NotoSans-Regular", 10.0)
    assert is_bold_lower is True
    assert is_bold_upper is False


def test_infer_font_handles_unknown_family_gracefully():
    """An empty/missing family falls back to the default size and
    non-bold. No exception, no surprise."""
    size, is_bold = _infer_font("anything", "", 10.0)
    assert size == 10.0
    assert is_bold is False
