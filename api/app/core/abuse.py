"""Small, privacy-conscious hooks for security-relevant abuse events."""

from __future__ import annotations

import logging

logger = logging.getLogger("aergia.abuse")


def log_abuse_event(event: str, **fields: object) -> None:
    """Emit a structured event without putting request data in the log line.

    Callers intentionally pass only bounded, non-sensitive fields such as a
    route, a fixed rejection reason, or a configured quota value. In
    particular, this helper does not accept or derive request bodies, tokens,
    passwords, or raw client IPs.
    """

    logger.warning(event, extra={"abuse_event": event, **fields})
