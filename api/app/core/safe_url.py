"""Small, shared URL policy used at API and renderer boundaries.

URLs are data, not markup.  This module deliberately accepts a narrow set of
schemes and refuses malformed values instead of trying to guess what a
browser, PDF engine, or password manager will do with them.
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit, urlunsplit


DEFAULT_ALLOWED_SCHEMES = frozenset({"http", "https", "mailto", "tel"})
HTTP_SCHEMES = frozenset({"http", "https"})


def _has_unsafe_characters(value: str) -> bool:
    return any(ord(char) < 0x20 or ord(char) == 0x7F for char in value) or any(
        char.isspace() for char in value
    )


def _has_valid_http_host(parsed) -> bool:
    if not parsed.netloc or parsed.username is not None or parsed.password is not None:
        return False
    if "\\" in parsed.netloc:
        return False
    try:
        hostname = parsed.hostname
        # Accessing ``port`` validates malformed port syntax even though the
        # renderer does not need the numeric value.
        parsed.port
    except ValueError:
        return False
    return bool(hostname)


def normalize_url(
    value: object,
    *,
    allowed_schemes: Iterable[str] = DEFAULT_ALLOWED_SCHEMES,
    add_https_for_bare_host: bool = True,
) -> str:
    """Return a normalized safe URL, or ``""`` when it is not allowed.

    HTTP(S) values must have a host and cannot contain credentials.  Bare
    hosts are treated as HTTPS URLs for the CV renderer's PDF-link behavior.
    ``mailto`` and ``tel`` are accepted only when explicitly included by the
    caller's allowlist.  All other schemes, including script and data URLs,
    are rejected.
    """

    if value is None:
        return ""
    raw = str(value)
    # Surrounding whitespace is a common form-input artifact and is safe to
    # discard. Controls and whitespace inside the URL remain invalid.
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in raw):
        return ""
    text = raw.strip()
    if not text or _has_unsafe_characters(text) or text.startswith("//"):
        return ""

    allowed = {scheme.lower() for scheme in allowed_schemes}
    try:
        parsed = urlsplit(text)
    except ValueError:
        return ""

    scheme = parsed.scheme.lower()
    if scheme:
        if scheme not in allowed:
            return ""
        if scheme in HTTP_SCHEMES:
            if not _has_valid_http_host(parsed):
                return ""
        elif scheme in {"mailto", "tel"}:
            if not parsed.path or parsed.netloc:
                return ""
        # Keep the user's path/query/fragment, but canonicalize the scheme.
        return urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))

    if not add_https_for_bare_host or "http" not in allowed and "https" not in allowed:
        return ""
    try:
        candidate = urlsplit(f"https://{text}")
    except ValueError:
        return ""
    if not _has_valid_http_host(candidate):
        return ""
    return f"https://{text}"


def normalize_http_url(value: object) -> str:
    """Normalize an external URL field that supports HTTP(S) only."""

    return normalize_url(value, allowed_schemes=HTTP_SCHEMES)


__all__ = ["DEFAULT_ALLOWED_SCHEMES", "HTTP_SCHEMES", "normalize_http_url", "normalize_url"]
