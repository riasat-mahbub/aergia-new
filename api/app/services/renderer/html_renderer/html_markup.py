"""Small, shared helpers for safe HTML fragment serialization.

The renderer builds HTML strings deliberately, so all escaping and inline
style serialization lives behind these helpers.  Higher-level modules only
need to describe the fragment they are rendering.
"""

from __future__ import annotations

import html as _stdlib_html
import re


_STYLE_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f\"'<>]")


def h(text: object) -> str:
    """HTML-escape a value for use between tags."""

    if text is None:
        return ""
    return _stdlib_html.escape(str(text))


def attr(text: object) -> str:
    """HTML-escape a value for use in a double-quoted attribute."""

    if text is None:
        return ""
    return _stdlib_html.escape(str(text), quote=True)


def style_attr(style: str | None) -> str:
    """Return a safe serialized style attribute, or omit it entirely.

    All user-controlled CSS values are validated before reaching this helper.
    The character check is a second defense for manually-created render
    models and future call sites that accidentally pass raw text.
    """

    if not style or _STYLE_UNSAFE_CHARS.search(style):
        return ""
    return f' style="{attr(style)}"'


def format_inline_style(declarations: list[str]) -> str:
    """Join non-empty CSS declarations in renderer order."""

    return ";".join(declaration for declaration in declarations if declaration)


__all__ = ["attr", "format_inline_style", "h", "style_attr"]
