"""API-key detection + redaction tests.

Locks down the prefix table and the redactor's contract. The route
maps :class:`UnknownProviderError` to HTTP 400; the redactor must
scrub every recognised prefix before any value crosses a logging
boundary.
"""

from __future__ import annotations

import pytest

from app.services.parser.keys import (
    LLMProvider,
    PROVIDER_PREFIXES,
    UnknownProviderError,
    detect_provider,
    redact,
)


# ---------------------------------------------------------------------------
# Prefix detection
# ---------------------------------------------------------------------------


def test_detect_provider_matches_each_known_prefix():
    assert detect_provider("sk-abc123") is LLMProvider.OPENAI
    assert detect_provider("sk-ant-abc123") is LLMProvider.ANTHROPIC
    assert detect_provider("AIzaSyABC") is LLMProvider.GEMINI
    assert detect_provider("gsk_abc123") is LLMProvider.GROQ


def test_detect_provider_rejects_empty_string():
    with pytest.raises(UnknownProviderError):
        detect_provider("")


def test_detect_provider_rejects_unknown_prefix():
    with pytest.raises(UnknownProviderError):
        detect_provider("totally-not-a-key")


def test_detect_provider_chooses_longest_known_prefix():
    # "sk-ant-" must beat "sk-" because the matcher walks prefixes in
    # order and the Anthropic slot is declared before OpenAI.
    assert detect_provider("sk-ant-xyz") is LLMProvider.ANTHROPIC


def test_provider_prefixes_table_is_complete():
    # Every enum member has a prefix entry — guards against adding a
    # new provider to the enum without registering its prefix.
    for provider in LLMProvider:
        assert provider in PROVIDER_PREFIXES
        assert len(PROVIDER_PREFIXES[provider]) >= 1


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected_marker",
    [
        ("sk-abcdefghijklmnop", "sk-***REDACTED***"),
        ("sk-ant-abcdefghijklmnop", "sk-ant-***REDACTED***"),
        ("AIzaSyAbcDefGhiJklMnoPqrStuVwxYz012345678", "AIza***REDACTED***"),
        ("gsk_abc123def456", "gsk_***REDACTED***"),
    ],
)
def test_redact_strips_body_of_each_known_prefix(raw, expected_marker):
    assert expected_marker in redact(raw)


def test_redact_preserves_surrounding_text_unmodified():
    msg = "user pre sk-abcdefghijklmnop user post"
    out = redact(msg)
    assert "user pre" in out
    assert "user post" in out
    assert "sk-***REDACTED***" in out


def test_redact_handles_multiple_keys_in_one_message():
    msg = "openai sk-openai-key123 and anthropic sk-ant-anthropic-key456 both fail"
    out = redact(msg)
    assert "sk-***REDACTED***" in out
    assert "sk-ant-***REDACTED***" in out
    # Original key bodies must be gone.
    assert "openai-key123" not in out
    assert "anthropic-key456" not in out


def test_redact_passthrough_for_messages_with_no_key():
    msg = "operation succeeded without any sensitive values"
    assert redact(msg) == msg


def test_redact_handles_empty_string():
    assert redact("") == ""


def test_redact_handles_quoted_key_in_error_message():
    msg = 'auth failed for key "sk-bogus-key-marker"'
    out = redact(msg)
    assert "sk-***REDACTED***" in out
    assert "bogus-key-marker" not in out
