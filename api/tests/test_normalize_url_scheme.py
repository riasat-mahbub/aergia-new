"""Tests for the normalize_url_scheme helper.

Strips whitespace, then ensures every returned string starts with a URL
scheme. Empty / None inputs return '' so callers can keep treating them
as 'no link'.
"""
from app.services.renderer.builders._utils import normalize_url_scheme


def test_none_returns_empty():
    assert normalize_url_scheme(None) == ""


def test_empty_string_returns_empty():
    assert normalize_url_scheme("") == ""


def test_whitespace_only_returns_empty():
    assert normalize_url_scheme("   ") == ""
    assert normalize_url_scheme("\t\n") == ""


def test_bare_domain_gets_https_prefix():
    """The user-facing bug: 'rmahbub.com' is treated as a relative URL by
    Chromium's print pipeline and produces no /Link annotation. The helper
    must prepend https:// so the PDF export carries a clickable link."""
    assert normalize_url_scheme("rmahbub.com") == "https://rmahbub.com"


def test_bare_subdomain_gets_https_prefix():
    assert normalize_url_scheme("www.example.com") == "https://www.example.com"


def test_https_url_passes_through_unchanged():
    """Already-scheme'd URLs must not be doubled-up."""
    assert normalize_url_scheme("https://aergia.dev") == "https://aergia.dev"


def test_http_url_passes_through_unchanged():
    """Even http:// is preserved — the caller may have a reason to prefer it."""
    assert normalize_url_scheme("http://insecure.example.com") == "http://insecure.example.com"


def test_contact_schemes_pass_through_unchanged():
    """mailto: and tel: are supported contact-link schemes."""
    assert normalize_url_scheme("mailto:foo@bar.com") == "mailto:foo@bar.com"
    assert normalize_url_scheme("tel:+1234567890") == "tel:+1234567890"


def test_unsafe_schemes_are_omitted():
    assert normalize_url_scheme("javascript:alert(1)") == ""
    assert normalize_url_scheme("data:text/html,hello") == ""
    assert normalize_url_scheme("vbscript:msgbox(1)") == ""


def test_malformed_urls_are_omitted():
    assert normalize_url_scheme("https://") == ""
    assert normalize_url_scheme("https://example.com/with space") == ""
    assert normalize_url_scheme("\x01https://example.com") == ""


def test_whitespace_around_input_is_stripped():
    assert normalize_url_scheme("  rmahbub.com  ") == "https://rmahbub.com"
    assert normalize_url_scheme("  https://x.dev  ") == "https://x.dev"


def test_non_string_passes_through_normalization():
    """Non-string inputs are coerced via str() before normalization. Keeps
    the helper safe for callers that read from loosely-typed storage."""
    assert normalize_url_scheme(42) == "https://42"
