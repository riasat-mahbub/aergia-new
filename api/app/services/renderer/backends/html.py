"""HTML backend — renders DocumentIR to HTML5."""

from ..ir import AbstractRenderer
from ..types import DocumentIR, ZoneIR


def _format_zone_styles(zone: ZoneIR) -> str:
    """Format zone style dict into inline CSS string."""
    parts = [f"{k}:{v}" for k, v in zone.styles.items() if v]
    return ";".join(parts)


def _format_zone_panels(zone: ZoneIR) -> str:
    """Render all panels within a zone as HTML."""
    panels = []
    for panel in zone.panels:
        panels.append(
            f'<div style="{panel.wrapper_style}">'
            f'<h2 style="{panel.heading_style}">{panel.title}</h2>'
            f'{panel.html}'
            f'</div>'
        )
    return "".join(panels)


def _format_single_zone(zone: ZoneIR) -> str:
    """Render a single zone div with its panels."""
    style_str = _format_zone_styles(zone)
    content = _format_zone_panels(zone)
    return f'<div class="zone" style="{style_str}">{content}</div>'


def _format_css_vars_block(css_vars: dict[str, str]) -> str:
    """Render CSS custom properties block."""
    lines = [f"  {k}: {v};" for k, v in css_vars.items() if v]
    return "\n".join(lines)


class HTMLBackend(AbstractRenderer):
    """Renders DocumentIR to a complete HTML5 document."""

    def _format(self, ir: DocumentIR) -> str:
        zones_html = "".join(_format_single_zone(zone) for zone in ir.zones)
        css_vars_block = _format_css_vars_block(ir.css_vars)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: {ir.body_font};
      {css_vars_block}
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: {ir.heading_font};
    }}
    {ir.print_styles}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
{zones_html}
</div>
</body>
</html>"""
