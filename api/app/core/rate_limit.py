import hashlib
import hmac
from ipaddress import ip_address, ip_network

from slowapi import Limiter
from starlette.requests import Request

from app.config import get_settings

settings = get_settings()


def _noop_decorator(func):
    """Pass-through decorator that does nothing."""
    return func


class TestLimiter:
    """No-op limiter replacement for test mode — disables all rate limiting."""

    def limit(self, *args, **kwargs):
        return _noop_decorator

    @property
    def enabled(self):
        return False


def _peer_address(request: Request) -> str:
    client = request.scope.get("client")
    if isinstance(client, (tuple, list)) and client:
        return str(client[0])
    return "unknown"


def _trusted_networks():
    return tuple(
        ip_network(item)
        for item in settings.trusted_proxy_ips.split(",")
        if item
    )


def _is_trusted_proxy(host: str) -> bool:
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return any(address in network for network in _trusted_networks())


def get_client_address(request: Request) -> str:
    """Return a client address while accepting forwarded headers only from configured peers.

    The application does not trust an ``X-Forwarded-For`` header from a direct
    client. When the immediate ASGI peer is configured in ``TRUSTED_PROXY_IPS``,
    the chain is walked from right to left and the first non-trusted address is
    used. The setting is empty by default, matching the repository's direct
    single-process topology.
    """

    peer = _peer_address(request)
    if not _is_trusted_proxy(peer):
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer
    candidates = [item.strip() for item in forwarded.split(",")]
    for candidate in reversed(candidates):
        if candidate and not _is_trusted_proxy(candidate):
            try:
                ip_address(candidate)
            except ValueError:
                continue
            return candidate
    return peer


def get_rate_limit_key(request: Request) -> str:
    """Return a stable, non-reversible key for the resolved client address."""

    address = get_client_address(request).encode("utf-8")
    digest = hmac.new(settings.secret_key.encode("utf-8"), address, hashlib.sha256).hexdigest()[:16]
    return f"ip:{digest}"


# Disable rate limiting in test mode (per-route limits interfere with testing)
if settings.environment == "test":
    limiter = TestLimiter()  # type: ignore
else:
    # The supported deployment currently runs one API process. Keep the
    # storage choice explicit so a later multi-worker deployment must make the
    # shared-storage decision deliberately instead of silently relying on the
    # process-local default.
    limiter = Limiter(
        key_func=get_rate_limit_key,
        default_limits=["100/minute"],
        headers_enabled=True,
        storage_uri="memory://",
        key_style="url",
    )


__all__ = ["TestLimiter", "get_client_address", "get_rate_limit_key", "limiter"]
