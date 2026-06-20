"""Legacy customizations migration.

Phase 1 silently dropped the legacy ``{colors, fonts, spacing, flags}``
shape from per-CV writes because ``Customizations`` only declared
``accent_color, body_font, heading_font, ...``. The customize panel and
the template wizard both kept writing the legacy shape, so user edits
to accent / body font / heading font were silently lost.

Phase 2 cuts over: ``Customizations`` rejects those top-level keys at
the boundary via ``model_validator(mode="before")``. Legacy rows still
live in the DB; this module provides a one-shot migrator so legacy
reads still produce a working CSS cascade.
"""

from __future__ import annotations


_SPACING_LEGACY_TO_PRESET: dict[str, str] = {
    "16px": "compact",
    "20px": "compact",
    "8px": "minimal",
}

_LEGACY_TOP_LEVEL_KEYS = frozenset({"colors", "fonts", "spacing", "flags"})


def migrate_legacy_customizations(raw: dict | None) -> dict:
    """Convert the v1 per-CV customizations shape into v2 canonical fields.

    Strips ``colors / fonts / spacing / flags`` top-level keys and
    re-emits them as canonical ``accent_color / body_font / heading_font /
    spacing`` where present. ``per_section`` and any other top-level
    keys pass through unchanged so per-instance three-axis overrides
    survive.

    Already-canonical input is returned as-is so callers don't pay for a
    copy on the hot path.
    """
    if not isinstance(raw, dict):
        return raw or {}
    if not (_LEGACY_TOP_LEVEL_KEYS & set(raw.keys())):
        return raw

    colors = raw.get("colors") or {}
    fonts = raw.get("fonts") or {}
    legacy_spacing = (raw.get("spacing") or {}).get("section_gap")

    if legacy_spacing is None:
        spacing_preset = None
    elif legacy_spacing in _SPACING_LEGACY_TO_PRESET:
        spacing_preset = _SPACING_LEGACY_TO_PRESET[legacy_spacing]
    else:
        spacing_preset = "comfortable"

    canonical: dict = {
        k: v for k, v in raw.items() if k not in _LEGACY_TOP_LEVEL_KEYS
    }

    accent = (
        colors.get("accent")
        or colors.get("header")
        or colors.get("heading")
        or colors.get("text")
    )
    if accent is not None:
        canonical["accent_color"] = accent
    if fonts.get("body"):
        canonical["body_font"] = fonts["body"]
    if fonts.get("heading"):
        canonical["heading_font"] = fonts["heading"]
    if spacing_preset:
        canonical["spacing"] = spacing_preset

    return canonical
