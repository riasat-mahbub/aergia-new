"""Default palette registry.

A template manifest can carry color values as either a hex literal
(``#RRGGBB``) or a named palette reference (``palette.<name>``). The
palette itself is renderer-defined: the HTML renderer ships this default
palette, but a future DOCX renderer can register its own palette. The
schema carries only the reference, not the resolved color value.

The shared palette file is the keystone: both the schema validators and
the renderer read from the same vocabulary, so a template authored for
the HTML renderer renders correctly in DOCX.
"""

# The default palette: a small, restrained set of named color slots.
# A template author picks ``palette.accent`` etc.; the renderer resolves
# the reference to a concrete hex value.
DEFAULT_PALETTE: dict[str, str] = {
    "accent": "#2563eb",
    "surface": "#ffffff",
    "surface-2": "#f8fafc",
    "text": "#111827",
    "text-muted": "#6b7280",
    "divider": "#e5e7eb",
}


def resolve_palette_ref(value: str, palette: dict[str, str] | None = None) -> str:
    """Resolve a color ref to a concrete color value.

    A hex literal is returned as-is. A ``palette.<name>`` reference is
    resolved against the given palette (defaults to
    :data:`DEFAULT_PALETTE`); unknown palette names fall back to the
    literal string so the renderer can fail loudly downstream.
    """
    p = palette if palette is not None else DEFAULT_PALETTE
    if value.startswith("#"):
        return value
    if value.startswith("palette."):
        name = value[len("palette."):]
        return p.get(name, value)
    return value
