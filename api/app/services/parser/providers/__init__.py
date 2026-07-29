"""LLM provider adapters — one per vendor.

Public surface (private to the parser package):

- :class:`LLMProvider` — protocol definition (see ``base.py``).
- :class:`OpenAIProvider` — OpenAI Chat Completions adapter.
- :class:`AnthropicProvider` — Anthropic Messages adapter.
- :class:`GeminiProvider` — Google Gemini generateContent adapter.
- :class:`GroqProvider` — Groq OpenAI-compatible Chat Completions adapter.

Adapter discipline (one key per call, dropped at client.close()):

    The adapter is the ONLY place the API key ever exists in memory.
    See ``base.py`` for the five-rule contract.
"""

from __future__ import annotations

from .base import LLMProvider, redact_payload


def _ensure_adapters() -> dict[str, type]:
    """Lazy import so unused adapters don't cost import-time.

    Returns ``{LLMProvider: adapter_cls}`` — populated only after
    the first call so import of ``openai`` / ``anthropic`` /
    ``google-genai`` / ``groq`` is deferred until a request actually
    routes through that path. The orchestrator uses this map to
    resolve the right adapter by enum value.
    """
    from .anthropic import AnthropicProvider
    from .gemini import GeminiProvider
    from .groq import GroqProvider
    from .openai import OpenAIProvider

    from ..keys import LLMProvider as ProviderEnum

    return {
        ProviderEnum.OPENAI: OpenAIProvider,
        ProviderEnum.ANTHROPIC: AnthropicProvider,
        ProviderEnum.GEMINI: GeminiProvider,
        ProviderEnum.GROQ: GroqProvider,
    }


__all__ = ["LLMProvider", "redact_payload", "_ensure_adapters"]
