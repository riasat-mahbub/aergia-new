from functools import wraps
from slowapi import Limiter
from slowapi.util import get_remote_address
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


# Disable rate limiting in test mode (per-route limits interfere with testing)
if settings.environment == "test":
    limiter = TestLimiter()  # type: ignore
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
