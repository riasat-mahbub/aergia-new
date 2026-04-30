"""Placeholder replacement utilities for template rendering."""

import re
from typing import Any


ZONE_NAME_PATTERNS = {
    "main", "sidebar", "header", "left", "right", "center",
    "center", "col", "panel", "zone", "area", "top",
    "bottom", "nav", "footer", "foot", "aside",
    "primary", "secondary"
}

ZONE_SUFFIXES = ("-col", "-zone", "-panel")


def _extract_zone_placeholders(template: str) -> set[str]:
    """Extract all {{zone_id}} placeholders from a template string."""
    matches = re.findall(r'\{\{([a-zA-Z0-9_-]+)\}\}', template)
    return set(matches)


def _is_zone_like(zone_id: str) -> bool:
    """Check if a placeholder looks like a zone name."""
    if zone_id in ZONE_NAME_PATTERNS:
        return True
    return any(zone_id.endswith(suffix) for suffix in ZONE_SUFFIXES)


def replace_with_populated_zones(
    html: str,
    populated_zone_ids: set[str],
    all_placeholders: set[str] | None = None
) -> str:
    """Replace unknown zone placeholders when we have populated zone info.

    Keeps placeholders that were populated, defined in layout_config, or are data variables.
    Replaces zone-like unknown placeholders with empty string.
    """
    placeholder_pattern = r'\{\{([a-zA-Z0-9_-]+)\}\}'

    def replace_placeholder(match: re.Match) -> str:
        zone_id = match.group(1)
        # Keep if it was populated
        if zone_id in populated_zone_ids:
            return match.group(0)
        # Keep if it's a data variable (not a zone-like name)
        if all_placeholders and zone_id not in all_placeholders:
            return match.group(0)
        # Replace zone-like names with empty string
        if _is_zone_like(zone_id):
            return ""
        # Otherwise leave it (likely a data variable like {{name}})
        return match.group(0)

    return re.sub(placeholder_pattern, replace_placeholder, html)


def replace_with_defined_zones(
    html: str,
    defined_zone_ids: set[str]
) -> str:
    """Legacy path: replace placeholders not in defined zones with empty string."""
    placeholder_pattern = r'\{\{([a-zA-Z0-9_-]+)\}\}'

    def replace_placeholder(match: re.Match) -> str:
        zone_id = match.group(1)
        return "" if zone_id not in defined_zone_ids else match.group(0)

    return re.sub(placeholder_pattern, replace_placeholder, html)


def replace_noop(html: str) -> str:
    """No-op: leave all placeholders as-is."""
    return html