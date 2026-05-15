"""Shared type definitions for the renderer."""

from dataclasses import dataclass, field


@dataclass
class SectionPanelIR:
    """A rendered section panel ready for insertion into a zone."""
    type: str
    title: str
    html: str
    wrapper_style: str
    heading_style: str


@dataclass
class ZoneIR:
    """A zone with its resolved styles and panels."""
    id: str
    styles: dict[str, str]
    panels: list[SectionPanelIR] = field(default_factory=list)


@dataclass
class RowIR:
    """A row of zones (horizontal layout)."""
    index: int
    zones: list[ZoneIR]
    flex_value: str = "0 0 auto"


@dataclass
class DocumentIR:
    """Complete intermediate representation for rendering."""
    rows: list[RowIR]
    css_vars: dict[str, str]
    print_styles: str
    body_font: str
    heading_font: str