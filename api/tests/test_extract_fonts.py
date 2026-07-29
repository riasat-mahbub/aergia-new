"""Font-dictionary extraction tests for the PDF parser.

The parser used to flag a line as bold only when its text was ALL-CAPS
(`line == line.upper()`). Real-world resumes are mixed-case, and Chromium
embeds Type0 subset fonts whose BaseFont names never match the size-hint
regex. The fix reads the font dictionary directly and infers boldness
from the font family name.

These tests cover the three layers:

1. `_extract_font_dict` returns ``{basefont: family_name}`` (string, not
   float) for Type0 subset PDFs.
2. `_infer_font` decides bold from the font family, not the text.
3. `_extract_pdf` produces ``TextBlock`` records whose ``is_bold`` and
   ``font_size`` reflect the actual rendered font of each line.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.parser.extract import (
    _extract_font_dict,
    _extract_pdf,
    _infer_font,
    _font_family_from_basefont,
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
# _extract_font_dict
# ---------------------------------------------------------------------------


def _make_page_with_fonts(fonts: dict[str, str]):
    """Build a fake page object whose ``/Resources/Font`` holds the given
    ``{key: BaseFont}`` mapping. The dict is the same shape pypdf uses
    in its real /Resources/Font table."""

    class _Font:
        def __init__(self, basefont: str) -> None:
            self._basefont = basefont

        def get(self, key, default=None):
            return {"/BaseFont": self._basefont}.get(str(key), default)

    class _Page:
        def __init__(self, font_dict: dict[str, _Font]) -> None:
            self._resources = {"/Resources": {"/Font": font_dict}}

        def get(self, key):
            return self._resources.get(str(key))

    return _Page({k: _Font(v) for k, v in fonts.items()})


def test_extract_font_dict_returns_family_names_for_type0_subset():
    """The benchmark PDF (NotoSans-* as Type0 subsets) returns the family
    string, not the 0.0 size that the old heuristic produced."""
    page = _make_page_with_fonts({
        "/F4": "/AAAAAA+NotoSans-Bold",
        "/F5": "/BAAAAA+NotoSans-Regular",
        "/F8": "/EAAAAA+NotoSans-SemiBold",
    })

    fonts = _extract_font_dict(page)

    assert fonts["/AAAAAA+NotoSans-Bold"] == "NotoSans-Bold"
    assert fonts["/BAAAAA+NotoSans-Regular"] == "NotoSans-Regular"
    assert fonts["/EAAAAA+NotoSans-SemiBold"] == "NotoSans-SemiBold"


def test_extract_font_dict_skips_fonts_without_basefont():
    """A font dict entry without /BaseFont is dropped (no family to lookup)."""
    class _Font:
        def get(self, key, default=None):
            return default

    class _Page:
        def get(self, key):
            return {"Font": {"/F1": _Font()}}

    assert _extract_font_dict(_Page()) == {}


def test_extract_font_dict_returns_empty_on_extract_failure():
    """When the page has no /Resources (corrupt / unusual PDF), the
    function returns an empty dict — never raises."""

    class _Page:
        def get(self, key):
            return None

    assert _extract_font_dict(_Page()) == {}


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


# ---------------------------------------------------------------------------
# _extract_pdf (real-PDF path)
# ---------------------------------------------------------------------------


def test_extract_pdf_recognises_bold_headers_in_benchmark_corpus():
    """End-to-end check: the benchmark corpus (/home/riasat/Downloads/Resume.pdf)
    produces TextBlock records whose is_bold flag tracks the actual
    rendered font family."""

    bench = Path("/home/riasat/Downloads/Resume.pdf")
    if not bench.exists():
        pytest.skip("benchmark corpus not available at ~/Downloads/Resume.pdf")

    doc = _extract_pdf(bench.read_bytes())

    assert doc.source_format == "pdf"
    assert len(doc.blocks) > 0

    # The benchmark PDF has a "Riasat Mahbub" name in NotoSans-Bold.
    name_block = next((b for b in doc.blocks if b.text == "Riasat Mahbub"), None)
    assert name_block is not None, "name block missing from extraction"
    assert name_block.is_bold is True, "name block should be bold (NotoSans-Bold)"

    # The PDF's "Experience" section header is NotoSans-Bold.
    exp_block = next((b for b in doc.blocks if b.text == "Experience"), None)
    assert exp_block is not None, "Experience header missing"
    assert exp_block.is_bold is True, "Experience header should be bold"

    # Body text is NotoSans-Regular and must NOT be bold.
    body_block = next((b for b in doc.blocks if b.text.startswith("Worked with")), None)
    assert body_block is not None, "body text missing"
    assert body_block.is_bold is False, "body text must not be bold"


def test_extract_pdf_handles_degenerate_pdf():
    """A non-PDF byte stream raises ExtractionFailedError."""
    from app.services.parser.extract import ExtractionFailedError

    with pytest.raises(ExtractionFailedError):
        _extract_pdf(b"NOT A PDF")
