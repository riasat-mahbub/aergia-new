"""Server-side Cloudflare Turnstile verification for account registration."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.core.abuse import log_abuse_event

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
logger = logging.getLogger("aergia.turnstile")


class TurnstileRejected(ValueError):
    """Raised when the Turnstile token cannot be trusted."""

    def __init__(self, reason: str, provider_codes: tuple[str, ...] = ()):
        self.reason = reason
        self.provider_codes = provider_codes
        super().__init__(reason)


def _provider_codes(payload: dict[str, Any]) -> tuple[str, ...]:
    """Keep only bounded provider error-code strings suitable for metadata."""

    raw_codes = payload.get("error-codes")
    if not isinstance(raw_codes, list):
        return ()
    return tuple(
        code[:64]
        for code in raw_codes[:8]
        if isinstance(code, str) and code
    )


async def verify_turnstile(
    token: str | None,
    *,
    settings: Settings | None = None,
) -> None:
    """Verify a registration token, failing closed on every provider error."""

    active_settings = settings or get_settings()
    if active_settings.turnstile_bypass and active_settings.environment in {"development", "test"}:
        return

    if not active_settings.turnstile_configured:
        _reject("configuration_missing")
    if not token or len(token) > 2048:
        _reject("token_missing")

    payload: dict[str, Any]
    try:
        timeout = httpx.Timeout(active_settings.turnstile_verification_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": active_settings.turnstile_secret_key,
                    "response": token,
                },
            )
        if response.status_code < 200 or response.status_code >= 300:
            _reject("provider_http_error")
        decoded = response.json()
        if not isinstance(decoded, dict):
            _reject("provider_invalid_response")
        payload = decoded
    except TurnstileRejected:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.info("turnstile_provider_unavailable", extra={"exception_type": type(exc).__name__})
        _reject("provider_unavailable")

    provider_codes = _provider_codes(payload)
    if payload.get("success") is not True:
        _reject("provider_rejected", provider_codes)
    if payload.get("action") != active_settings.turnstile_expected_action:
        _reject("action_mismatch", provider_codes)
    if payload.get("hostname") != active_settings.turnstile_expected_hostname:
        _reject("hostname_mismatch", provider_codes)


def _reject(reason: str, provider_codes: tuple[str, ...] = ()) -> None:
    log_abuse_event(
        "turnstile_rejected",
        reason=reason,
        provider_codes=provider_codes,
    )
    raise TurnstileRejected(reason, provider_codes)


__all__ = ["TURNSTILE_VERIFY_URL", "TurnstileRejected", "verify_turnstile"]
