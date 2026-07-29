"""LLM provider key detection + redactor.

The user-supplied API key for one of the four supported vendors
(OpenAI / Anthropic / Gemini / Groq) is matched on its well-known
prefix to determine which provider to dispatch to. The key itself
never reaches the orchestrator's persistence layer — the route reads
it from the multipart form, hands it to the adapter, and the adapter
drops it the moment the call completes.

Redaction contract:
    Every value that might end up in a log line, error message, or
    response detail MUST be passed through :func:`redact` first. The
    redactor walks each known prefix greedily and replaces the body
    (prefix → next whitespace / quote / EOL) with ``***REDACTED***``.
    The previous generic regex leaked Gemini's 39-char keys because
    the visible prefix is shorter than 6 chars; the per-prefix
    encoding below is the spec-correct rule from the prior review.

This module owns no state. Pure functions only. No globals. No env
vars read at import time.
"""

from __future__ import annotations

from enum import Enum
import re
from typing import Final


class LLMProvider(str, Enum):
    """Vendor identifier for the LLM parser path."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"


# Known prefix shapes per vendor. Order matters — the matcher returns
# on the first prefix hit, so the longest/most-specific prefix for
# each vendor MUST be listed before any shorter-but-overlapping
# prefix for a different vendor. Anthropic's `sk-ant-` is a subset
# of OpenAI's `sk-`; placing Anthropic first keeps the matcher
# correct.
PROVIDER_PREFIXES: Final[dict[LLMProvider, tuple[str, ...]]] = {
    LLMProvider.ANTHROPIC: ("sk-ant-",),
    LLMProvider.OPENAI: ("sk-",),
    LLMProvider.GEMINI: ("AIza",),
    LLMProvider.GROQ: ("gsk_",),
}


# Pre-compile ONE combined pattern covering every prefix so we walk
# the input once. The body-run is replaced with `***REDACTED***`.
_REDACT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?P<prefix>(?:sk-ant-|sk-|AIza|gsk_))(?P<body>[^\s\"'<>]{1,256})"
)


class ProviderError(Exception):
    """Base class for everything the LLM adapters may raise.

    The orchestrator distinguishes auth failures
    (:class:`InvalidAPIKeyError`) from rate-limit
    (:class:`RateLimitError`) and everything else
    (:class:`ProviderTransportError`).
    """


class InvalidAPIKeyError(ProviderError):
    """The provider rejected the key (HTTP 401 / 403)."""


class RateLimitError(ProviderError):
    """The provider returned 429 + ``retry-after``.

    The orchestrator may fall back to the regex path with an explicit
    warning pair.
    """


class ProviderTransportError(ProviderError):
    """Non-auth, non-rate-limit transport failure.

    Includes timeouts, malformed payloads, and 5xx responses.
    Orchestrator falls back to regex with an explicit warning.
    """


class UnknownProviderError(ValueError):
    """No known prefix matched the supplied API key.

    The route layer maps this to HTTP 400.
    """


def detect_provider(api_key: str) -> LLMProvider:
    """Return the :class:`LLMProvider` whose prefix matches ``api_key``.

    :raises UnknownProviderError: when no known prefix matches.
    """
    if not api_key:
        raise UnknownProviderError("API key is empty")

    for provider, prefixes in PROVIDER_PREFIXES.items():
        for prefix in prefixes:
            if api_key.startswith(prefix):
                return provider

    raise UnknownProviderError(
        "Unrecognised API key prefix. Supported prefixes: "
        "sk- (OpenAI), sk-ant- (Anthropic), AIza (Gemini), gsk_ (Groq)."
    )


def redact(message: str) -> str:
    """Replace the body of every recognised API key with ``***REDACTED***``.

    Used BEFORE any logging statement or error-message formatting that
    might receive a value containing a user-supplied key. The
    replacement preserves the leading prefix so a log reader can still
    see "we got a Gemini-shaped key" without the key itself.

    Never raises — given any input it returns a string of the same
    shape, with key bodies scrubbed.
    """
    if not message:
        return message

    return _REDACT_PATTERN.sub(
        lambda m: f"{m.group('prefix')}***REDACTED***",
        message,
    )


__all__ = [
    "LLMProvider",
    "PROVIDER_PREFIXES",
    "ProviderError",
    "InvalidAPIKeyError",
    "RateLimitError",
    "ProviderTransportError",
    "UnknownProviderError",
    "detect_provider",
    "redact",
]
