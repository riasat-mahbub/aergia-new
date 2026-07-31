"""Font-name-based bold inference.

Lifted out of the old ``extract.py`` so the pdfplumber backend and the
classifier can share the four primitives without dragging in pypdf's
visitor-mode types.

The contract these expose:

- :func:`_font_family_from_basefont` strips the ``AAAAAA+`` subset prefix
  PDF generators prepend for embedded subset fonts (``/AAAAAA+NotoSans-Bold``
  → ``NotoSans-Bold``).
- :func:`_font_family_is_bold` matches family tokens case-insensitively
  against the four weights Chromium-based PDF generators emit.
- :func:`_infer_font` returns ``(size, is_bold)`` for a line, applying a
  small size bump to bold lines so the classifier's ``font_size >=
  median * 1.15`` threshold still fires when body-italicized headers need
  defence in depth.
"""

from __future__ import annotations


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


__all__ = [
    "_FONT_NAME_BOLD_TOKENS",
    "_font_family_from_basefont",
    "_font_family_is_bold",
    "_infer_font",
]
