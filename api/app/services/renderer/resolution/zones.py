"""Resolve manifest/editor zones and map their tokens to HTML CSS values."""

from __future__ import annotations

from collections.abc import Iterable

from app.document_schema.models import ResolvedZone, Section, Zone
from app.services.renderer.html_values import (
    PADDING_TOKEN_VALUES as PADDING_TOKENS,
    WIDTH_TOKEN_VALUES as WIDTH_TOKENS,
    resolve_color_ref,
)

from .context import ResolutionContext
from .errors import ManifestVersionError


def _resolve_zone_styles(zone: Zone) -> dict[str, str]:
    """Map a manifest zone's renderer-independent tokens to HTML CSS."""

    css: dict[str, str] = {}
    if zone.styles.width is not None:
        css["width"] = WIDTH_TOKENS.get(zone.styles.width, zone.styles.width)
    if zone.styles.background is not None:
        css["background-color"] = resolve_color_ref(zone.styles.background)
    if zone.styles.padding is not None:
        css["padding"] = PADDING_TOKENS.get(zone.styles.padding, zone.styles.padding)
    return css


def resolve_zones(
    sections: Iterable[Section],
    context: ResolutionContext,
) -> list[ResolvedZone]:
    """Resolve per-document zone placement with editor-over-manifest precedence."""

    sections = tuple(sections)
    layout = context.customizations.layout
    manifest = context.manifest
    zones = (
        layout.zones
        if layout is not None and layout.zones
        else (manifest.zones if manifest else [])
    )
    if not zones:
        return [ResolvedZone(
            id="main",
            styles={},
            section_ids=[section.id for section in sections],
        )]

    placement = (
        layout.placement
        if layout is not None and layout.placement
        else (manifest.placement if manifest else {})
    )
    fallback_zone = zones[0].id

    groups: dict[str, list[str]] = {zone.id: [] for zone in zones}
    for section in sections:
        zone_id = placement.get(section.id) or placement.get(section.type, fallback_zone)
        if zone_id is None:
            raise ManifestVersionError(
                f"No zone defined for section type '{section.type}' and no fallback zone available"
            )
        groups.setdefault(zone_id, []).append(section.id)

    return [
        ResolvedZone(
            id=zone.id,
            styles=_resolve_zone_styles(zone),
            section_ids=groups.get(zone.id, []),
        )
        for zone in zones
    ]


__all__ = ["resolve_zones"]
