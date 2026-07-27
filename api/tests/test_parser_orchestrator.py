"""Orchestrator-level tests for the LLM path.

Monkey-patches the provider adapters via ``_PROVIDERS`` so no network
calls happen. Locks the four behaviours:

1. No key → regex path (existing behaviour preserved).
2. Matching key + provider → LLM adapter called, ``meta.source == "llm"``,
   ``warnings`` includes ``"llm_used"``.
3. Adapter raises :class:`InvalidAPIKeyError` → orchestrator re-raises
   (route maps to 401).
4. Adapter raises :class:`RateLimitError` or
   :class:`ProviderTransportError` → orchestrator falls back to regex
   with the explicit warning pair.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schema.models import SectionInstance
from app.services.parser import imports as orch
from app.services.parser.imports import parse_cv
from app.services.parser.keys import (
    InvalidAPIKeyError,
    LLMProvider,
    ProviderTransportError,
    RateLimitError,
    UnknownProviderError,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _empty_pdf() -> bytes:
    """Real PDF byte stream :func:`extract` can open. Borrowed from the
    existing smoke fixture so we never duplicate a binary in the repo."""
    return (Path(__file__).parent / "fixtures" / "sample.pdf").read_bytes()


def _stub_sections() -> list[SectionInstance]:
    return [
        SectionInstance(
            id="stub",
            type="profile",
            title="P",
            enabled=True,
            data={"name": "Stub"},
        ),
    ]


@pytest.fixture(autouse=True)
def _reset_provider_map():
    """Each test gets a fresh ``_PROVIDERS`` cache."""
    orch._PROVIDERS = None
    yield
    orch._PROVIDERS = None


# ---------------------------------------------------------------------------
# No key → regex path
# ---------------------------------------------------------------------------


async def test_no_key_selects_regex_path_unchanged():
    result = await parse_cv(_empty_pdf(), "application/pdf")
    assert result.meta.source == "regex"
    assert "llm_used" not in result.meta.warnings


async def test_blank_key_treated_as_no_key():
    result = await parse_cv(_empty_pdf(), "application/pdf", api_key="   ")
    assert result.meta.source == "regex"


async def test_provider_without_key_treated_as_no_key():
    result = await parse_cv(
        _empty_pdf(), "application/pdf", provider=LLMProvider.OPENAI
    )
    assert result.meta.source == "regex"


# ---------------------------------------------------------------------------
# Matching key + provider → LLM adapter called
# ---------------------------------------------------------------------------


async def test_matching_key_selects_openai_adapter():
    captured: dict = {}

    class _OpenAIStub:
        async def structure(self, *, plain_text, api_key, section_schema, hints=None):
            captured["api_key"] = api_key
            captured["schema"] = section_schema
            return _stub_sections()

    orch._PROVIDERS = {LLMProvider.OPENAI: _OpenAIStub}

    result = await parse_cv(
        _empty_pdf(),
        "application/pdf",
        provider=LLMProvider.OPENAI,
        api_key="sk-test-matching-key",
    )
    assert result.meta.source == "llm"
    assert "llm_used" in result.meta.warnings
    assert captured["api_key"] == "sk-test-matching-key"
    # Schema wrapper includes a "sections" array, whose items are the
    # SectionInstance JSON schema dict.
    assert captured["schema"]["properties"]["sections"]["type"] == "array"
    assert "required" in captured["schema"]


@pytest.mark.parametrize(
    "vendor_key, provider",
    [
        ("sk-test-mark", LLMProvider.OPENAI),
        ("sk-ant-test-mark", LLMProvider.ANTHROPIC),
        ("AIza-test-mark", LLMProvider.GEMINI),
        ("gsk_test-mark", LLMProvider.GROQ),
    ],
)
async def test_each_provider_round_trips_through_orchestrator(vendor_key, provider):
    class _Stub:
        async def structure(self, *, plain_text, api_key, section_schema, hints=None):
            return _stub_sections()

    orch._PROVIDERS = {provider: _Stub}
    result = await parse_cv(
        _empty_pdf(),
        "application/pdf",
        provider=provider,
        api_key=vendor_key,
    )
    assert result.meta.source == "llm", f"failed for {provider}"


# ---------------------------------------------------------------------------
# Invalid key → orchestrator re-raises (route maps to 401)
# ---------------------------------------------------------------------------


async def test_invalid_api_key_propagates_without_fallback():
    class _AuthFail:
        async def structure(self, **_):
            raise InvalidAPIKeyError("auth rejected sk-bogus-key-marker")

    orch._PROVIDERS = {LLMProvider.OPENAI: _AuthFail}

    with pytest.raises(InvalidAPIKeyError, match="auth rejected"):
        await parse_cv(
            _empty_pdf(),
            "application/pdf",
            provider=LLMProvider.OPENAI,
            api_key="sk-bogus-key-marker",
        )


# ---------------------------------------------------------------------------
# Rate-limit / transport → orchestrator falls back to regex with warning pair
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        RateLimitError("429 retry-after"),
        ProviderTransportError("connection reset"),
    ],
    ids=["rate-limit", "transport"],
)
async def test_non_auth_failure_falls_back_to_regex(exc):
    class _FailAdapter:
        async def structure(self, **_):
            raise exc

    orch._PROVIDERS = {LLMProvider.OPENAI: _FailAdapter}

    result = await parse_cv(
        _empty_pdf(),
        "application/pdf",
        provider=LLMProvider.OPENAI,
        api_key="sk-bogus-key-marker",
    )
    assert result.meta.source == "regex"
    assert "llm_failed_fallback_to_regex" in result.meta.warnings
    assert any(
        w.startswith("llm_failed:") and type(exc).__name__ in w
        for w in result.meta.warnings
    )


# ---------------------------------------------------------------------------
# Provider-key mismatch → ValueError surfaces as 400
# ---------------------------------------------------------------------------


async def test_key_prefix_mismatch_raises_valueerror():
    with pytest.raises(ValueError, match="looks like"):
        await parse_cv(
            _empty_pdf(),
            "application/pdf",
            provider=LLMProvider.ANTHROPIC,
            api_key="sk-bogus-key-marker",
        )


async def test_unknown_key_prefix_raises_unknown_provider_error():
    with pytest.raises(UnknownProviderError):
        await parse_cv(
            _empty_pdf(),
            "application/pdf",
            provider=LLMProvider.OPENAI,
            api_key="totally-not-a-key",
        )


# ---------------------------------------------------------------------------
# Adapter errors must be redacted before reaching the orchestrator
# ---------------------------------------------------------------------------


async def test_adapter_error_message_does_not_surface_raw_key():
    class _LeakyAdapter:
        async def structure(self, **_):
            # Simulate a vendor echoing the key back in the error message.
            raise ProviderTransportError(
                "vendor said: key sk-bogus-key-marker was rejected by upstream"
            )

    orch._PROVIDERS = {LLMProvider.OPENAI: _LeakyAdapter}

    result = await parse_cv(
        _empty_pdf(),
        "application/pdf",
        provider=LLMProvider.OPENAI,
        api_key="sk-bogus-key-marker",
    )
    joined = "\n".join(result.meta.warnings)
    # The fallback warning pair only carries the exception class name
    # ("llm_failed:ProviderTransportError"); no key fragment must be
    # part of any warning.
    assert "sk-bogus-key-marker" not in joined
    assert "sk-***REDACTED***" not in joined
