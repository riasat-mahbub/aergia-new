"""HTML backend — renders DocumentIR to HTML5."""

from ..ir import AbstractRenderer
from ..types import DocumentIR


class HTMLBackend(AbstractRenderer):
    """Renders DocumentIR to a complete HTML5 document."""

    def _format(self, ir: DocumentIR) -> str:
        zones_html_parts = []
        for row in ir.rows:
            zone_html_parts = []
            for zone in row.zones:
                style_attrs = []
                for k, v in zone.styles.items():
                    if v:
                        style_attrs.append(f"{k}:{v}")
                style_str = ";".join(style_attrs) if style_attrs else ""

                panels_html = []
                for panel in zone.panels:
                    panels_html.append(
                        f'<div style="{panel.wrapper_style}">'
                        f'<h2 style="{panel.heading_style}">{panel.title}</h2>'
                        f'{panel.html}'
                        f'</div>'
                    )
                zone_content = "".join(panels_html)
                zone_html_parts.append(f'<div style="{style_str}">{zone_content}</div>')

            row_html = f'<div style="display:flex;flex:1 0 auto;">{"".join(zone_html_parts)}</div>'
            zones_html_parts.append(row_html)

        zones_html = "".join(zones_html_parts)

        css_var_lines = []
        for var, value in ir.css_vars.items():
            if value:
                css_var_lines.append(f"  {var}: {value};")
        css_vars_block = "\n".join(css_var_lines) if css_var_lines else ""

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
