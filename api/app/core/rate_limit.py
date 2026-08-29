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
    # The supported deployment currently runs one API process. Keep the
    # storage choice explicit so a later multi-worker deployment must make the
    # shared-storage decision deliberately instead of silently relying on the
    # process-local default.
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],
        headers_enabled=True,
        storage_uri="memory://",
        key_style="url",
    )
