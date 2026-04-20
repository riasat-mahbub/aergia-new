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

  let html = '<div class="template-layout" style="min-height:297mm;display:flex;flex-direction:column;">\n';

  for (const [rowNum, rowZones] of sortedRows) {
    const rowHeight = rowHeights?.[rowNum];
    if (rowHeight) {
      html += `  <div style="display:flex;flex:${parseInt(rowHeight)} 0 0%;">\n`;
    } else {
      html += `  <div style="display:flex;flex:1 0 auto;">\n`;
    }

    for (const zone of rowZones) {
      const styles = zone.styles || {};
      const width = styles.width || "100%";
      const padding = styles.padding || "24px";
      const bg = styles["background-color"] ? `;background-color:${styles["background-color"]}` : "";
      html += `    <div id="{{${zone.id}}}" style="width:${width};padding:${padding}${bg};"></div>\n`;
    }

    html += `  </div>\n`;
  }

  html += "</div>";
  return html;
}
