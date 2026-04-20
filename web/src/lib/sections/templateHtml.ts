import type { LayoutConfig, Zone } from "./types";

export function layoutConfigToHTML(config: LayoutConfig): string {
  const rows = new Map<number, Zone[]>();
  for (const zone of config.zones) {
    const r = zone.row ?? 0;
    if (!rows.has(r)) rows.set(r, []);
    rows.get(r)!.push(zone);
  }

  const sortedRows = [...rows.entries()].sort(([a], [b]) => a - b);
  const rowHeights = config.rowHeights;

  let bodyContent = "";

  for (const [rowNum, rowZones] of sortedRows) {
    const rowHeight = rowHeights?.[rowNum];
    let flexVal: string;
    if (rowHeight) {
      const pct = parseInt(rowHeight.replace("%", ""));
      if (!isNaN(pct) && pct > 0) {
        flexVal = `${pct} 0 0%`;
      } else {
        flexVal = "1 0 auto";
      }
    } else {
      flexVal = "1 0 auto";
    }
    bodyContent += `  <div style="display:flex;flex:${flexVal};">\n`;

    for (const zone of rowZones) {
      bodyContent += `    {{${zone.id}}}\n`;
    }

    bodyContent += `  </div>\n`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      margin: 0;
      padding: 0;
      font-family: {{body_font}};
      color: var(--text, #374151);
    }
    h1, h2, h3, h4, h5, h6 {
      font-family: {{heading_font}};
      color: var(--heading, #111827);
    }
    {{print_styles}}
  </style>
</head>
<body>
<div style="min-height:297mm;display:flex;flex-direction:column;">
${bodyContent}</div>
</body>
</html>`;
}