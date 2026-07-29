"""Per-provider adapter tests using fake transport.

Each adapter's SDK client is monkey-patched before each test so the
adapter runs against an inline fake, not a real HTTP call. Failure
mapping matrix per provider:

- Success: adapter returns two validated ``SectionInstance``.
- Auth failure → ``InvalidAPIKeyError``.
- Rate-limit failure → ``RateLimitError``.
- Malformed payload → ``ProviderTransportError``.

The transport fakes are deliberately minimal — they exist to verify
that the adapter routes the right exception through the right helper
and that key bytes never reach an exception message.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.schema.models import SectionInstance
from app.services.parser.keys import (
    InvalidAPIKeyError,
    ProviderTransportError,
    RateLimitError,
)
from app.services.parser.providers.anthropic import AnthropicProvider
from app.services.parser.providers.gemini import GeminiProvider
from app.services.parser.providers.groq import GroqProvider
from app.services.parser.providers.openai import OpenAIProvider


SCHEMA_HINT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sections": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["sections"],
}


def _two_sections_dict() -> list[dict[str, Any]]:
    return [
        {
            "id": "imp_one",
            "type": "profile",
            "title": "One",
            "enabled": True,
            "data": {"name": "One", "title": "", "email": "", "phone": "",
                     "location": "", "site_text": "", "site_url": "",
                     "summary": "", "photo_url": "", "social_links": []},
        },
        {
            "id": "imp_two",
            "type": "profile",
            "title": "Two",
            "enabled": True,
            "data": {"name": "Two", "title": "", "email": "", "phone": "",
                     "location": "", "site_text": "", "site_url": "",
                     "summary": "", "photo_url": "", "social_links": []},
        },
    ]


def _two_sections_payload() -> dict[str, Any]:
    return {"sections": _two_sections_dict()}


def _json_bytes() -> str:
    return json.dumps(_two_sections_payload())


# ---------------------------------------------------------------------------
# Fake SDK client factory helpers
# ---------------------------------------------------------------------------


class _NoRequest:
    """Stand-in httpx.Response for SDK exception ctors."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.headers: dict[str, str] = {}
        self.text = ""
        self.request = self  # some SDK errors access .request
        self.body = None


def _make_openai_resp(content: str):
    """Fake the OpenAI response shape:

    ``resp.choices[0].message.content``
    """
    msg = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice])


def _patch_openai_client(monkeypatch, *, raise_exc=None, response=None):
    """Install an AsyncOpenAI stub. Either ``raise_exc`` (an exception
    instance) or ``response`` (a response-like object) is used."""
    captured: dict[str, Any] = {}

    class _FakeOpenAI:
        def __init__(self, *, api_key=None, **kwargs):
            captured["api_key"] = api_key

        @property
        def chat(self):
            class _Completions:
                async def create(self, **_):
                    if raise_exc is not None:
                        raise raise_exc
                    return response

            return SimpleNamespace(completions=_Completions())

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "app.services.parser.providers.openai.AsyncOpenAI", _FakeOpenAI
    )
    return captured


def _patch_groq_client(monkeypatch, *, raise_exc=None, response=None):
    captured: dict[str, Any] = {}

    class _FakeGroq:
        def __init__(self, *, api_key=None, **kwargs):
            captured["api_key"] = api_key

        @property
        def chat(self):
            class _Completions:
                async def create(self, **_):
                    if raise_exc is not None:
                        raise raise_exc
                    return response

            return SimpleNamespace(completions=_Completions())

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "app.services.parser.providers.groq.AsyncGroq", _FakeGroq
    )
    return captured


def _patch_anthropic_client(monkeypatch, *, raise_exc=None, response=None):
    captured: dict[str, Any] = {}

    class _FakeAnthropic:
        def __init__(self, *, api_key=None, **kwargs):
            captured["api_key"] = api_key

        @property
        def messages(self):
            class _Messages:
                async def create(self, **_):
                    if raise_exc is not None:
                        raise raise_exc
                    return response

            return _Messages()

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr(
        "app.services.parser.providers.anthropic.AsyncAnthropic", _FakeAnthropic
    )
    return captured


def _patch_gemini_client(monkeypatch, *, raise_exc=None, response=None):
    captured: dict[str, Any] = {}

    class _FakeGeminiClient:
        def __init__(self, *, api_key=None, **kwargs):
            captured["api_key"] = api_key

        @property
        def aio(self):
            class _AIO:
                @property
                def models(self):
                    class _Models:
                        async def generate_content(self, **_):
                            if raise_exc is not None:
                                raise raise_exc
                            return response

                    return _Models()

            return _AIO()

    monkeypatch.setattr(
        "app.services.parser.providers.gemini.genai.Client", _FakeGeminiClient
    )
    return captured


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


async def test_openai_success(monkeypatch):
    captured = _patch_openai_client(
        monkeypatch, response=_make_openai_resp(_json_bytes())
    )

    sections = await OpenAIProvider().structure(
        plain_text="x", api_key="sk-bogus-key-marker", section_schema=SCHEMA_HINT
    )

    assert len(sections) == 2
    assert all(isinstance(s, SectionInstance) for s in sections)
    assert captured["closed"] is True
    assert captured["api_key"] == "sk-bogus-key-marker"


async def test_openai_auth_failure(monkeypatch):
    from openai import AuthenticationError as OpenAIAuth

    _patch_openai_client(
        monkeypatch,
        raise_exc=OpenAIAuth(
            "sk-bogus-key-marker rejected",
            response=_NoRequest(401),
            body=None,
        ),
    )

    with pytest.raises(InvalidAPIKeyError):
        await OpenAIProvider().structure(
            plain_text="x", api_key="sk-bogus-key-marker", section_schema=SCHEMA_HINT
        )


async def test_openai_rate_limit(monkeypatch):
    from openai import RateLimitError as OpenAIRateLimit

    _patch_openai_client(
        monkeypatch,
        raise_exc=OpenAIRateLimit(
            "429",
            response=_NoRequest(429),
            body=None,
        ),
    )

    with pytest.raises(RateLimitError):
        await OpenAIProvider().structure(
            plain_text="x", api_key="sk-bogus-key-marker", section_schema=SCHEMA_HINT
        )


async def test_openai_malformed_payload(monkeypatch):
    _patch_openai_client(
        monkeypatch, response=_make_openai_resp("{not-json")
    )

    with pytest.raises(ProviderTransportError, match="non-JSON"):
        await OpenAIProvider().structure(
            plain_text="x", api_key="sk-bogus-key-marker", section_schema=SCHEMA_HINT
        )


# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------


async def test_groq_success(monkeypatch):
    captured = _patch_groq_client(
        monkeypatch, response=_make_openai_resp(_json_bytes())
    )

    sections = await GroqProvider().structure(
        plain_text="x", api_key="gsk_bogus-key-marker", section_schema=SCHEMA_HINT
    )
    assert len(sections) == 2
    assert captured["closed"] is True


async def test_groq_auth_failure(monkeypatch):
    from groq import AuthenticationError as GroqAuth

    _patch_groq_client(
        monkeypatch,
        raise_exc=GroqAuth(
            "gsk_bogus-key-marker rejected",
            response=_NoRequest(401),
            body=None,
        ),
    )

    with pytest.raises(InvalidAPIKeyError):
        await GroqProvider().structure(
            plain_text="x",
            api_key="gsk_bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


async def test_groq_rate_limit(monkeypatch):
    from groq import RateLimitError as GroqRateLimit

    _patch_groq_client(
        monkeypatch,
        raise_exc=GroqRateLimit("429", response=_NoRequest(429), body=None),
    )

    with pytest.raises(RateLimitError):
        await GroqProvider().structure(
            plain_text="x",
            api_key="gsk_bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


async def test_groq_malformed_payload(monkeypatch):
    _patch_groq_client(monkeypatch, response=_make_openai_resp("{not-json"))

    with pytest.raises(ProviderTransportError, match="non-JSON"):
        await GroqProvider().structure(
            plain_text="x",
            api_key="gsk_bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


def _anthropic_tool_resp(payload: dict[str, Any]):
    block = SimpleNamespace(type="tool_use", input=payload)
    return SimpleNamespace(content=[block])


async def test_anthropic_success(monkeypatch):
    captured = _patch_anthropic_client(
        monkeypatch, response=_anthropic_tool_resp(_two_sections_payload())
    )

    sections = await AnthropicProvider().structure(
        plain_text="x",
        api_key="sk-ant-bogus-key-marker",
        section_schema=SCHEMA_HINT,
    )
    assert len(sections) == 2
    assert captured["closed"] is True


async def test_anthropic_auth_failure(monkeypatch):
    from anthropic import AuthenticationError as AntAuth

    _patch_anthropic_client(
        monkeypatch,
        raise_exc=AntAuth(
            "sk-ant-bogus-key-marker rejected",
            response=_NoRequest(401),
            body=None,
        ),
    )

    with pytest.raises(InvalidAPIKeyError):
        await AnthropicProvider().structure(
            plain_text="x",
            api_key="sk-ant-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


async def test_anthropic_rate_limit(monkeypatch):
    from anthropic import RateLimitError as AntRateLimit

    _patch_anthropic_client(
        monkeypatch,
        raise_exc=AntRateLimit("429", response=_NoRequest(429), body=None),
    )

    with pytest.raises(RateLimitError):
        await AnthropicProvider().structure(
            plain_text="x",
            api_key="sk-ant-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


async def test_anthropic_empty_tool_use(monkeypatch):
    text_only = SimpleNamespace(content=[SimpleNamespace(type="text")])
    _patch_anthropic_client(monkeypatch, response=text_only)

    with pytest.raises(ProviderTransportError, match="no tool_use"):
        await AnthropicProvider().structure(
            plain_text="x",
            api_key="sk-ant-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def _gemini_resp(payload: dict[str, Any] | None, *, text: str = ""):
    return SimpleNamespace(parsed=payload, text=text)


async def test_gemini_success(monkeypatch):
    captured = _patch_gemini_client(
        monkeypatch, response=_gemini_resp(_two_sections_payload())
    )

    sections = await GeminiProvider().structure(
        plain_text="x",
        api_key="AIza-bogus-key-marker",
        section_schema=SCHEMA_HINT,
    )
    assert len(sections) == 2
    assert captured["api_key"] == "AIza-bogus-key-marker"


async def test_gemini_auth_failure(monkeypatch):
    from google.api_core.exceptions import Unauthenticated

    _patch_gemini_client(monkeypatch, raise_exc=Unauthenticated("AIza bad key"))

    with pytest.raises(InvalidAPIKeyError):
        await GeminiProvider().structure(
            plain_text="x",
            api_key="AIza-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


async def test_gemini_rate_limit(monkeypatch):
    from google.api_core.exceptions import ResourceExhausted

    _patch_gemini_client(monkeypatch, raise_exc=ResourceExhausted("429"))

    with pytest.raises(RateLimitError):
        await GeminiProvider().structure(
            plain_text="x",
            api_key="AIza-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


async def test_gemini_malformed_payload(monkeypatch):
    _patch_gemini_client(monkeypatch, response=_gemini_resp(None, text="{not-json"))

    with pytest.raises(ProviderTransportError, match="no parsed content"):
        await GeminiProvider().structure(
            plain_text="x",
            api_key="AIza-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )


# ---------------------------------------------------------------------------
# Redaction safety
# ---------------------------------------------------------------------------


async def test_openai_status_error_message_has_no_raw_key(monkeypatch):
    from openai import APIStatusError

    _patch_openai_client(
        monkeypatch,
        raise_exc=APIStatusError(
            "sk-bogus-key-marker upstream refused",
            response=_NoRequest(502),
            body=None,
        ),
    )

    with pytest.raises(ProviderTransportError) as exc_info:
        await OpenAIProvider().structure(
            plain_text="x",
            api_key="sk-bogus-key-marker",
            section_schema=SCHEMA_HINT,
        )

    assert "sk-bogus-key-marker" not in str(exc_info.value)
