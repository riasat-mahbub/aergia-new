import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import { normalizeWidths } from "../../lib/sections/zones";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  layoutConfig?: LayoutConfig;
}

function groupByZone(instances: SectionInstance[], layoutConfig: LayoutConfig | undefined): Map<string, SectionInstance[]> {
  const groups = new Map<string, SectionInstance[]>();
  if (!layoutConfig || !layoutConfig.placement) {
    const filtered = instances.filter((i) => i.enabled);
    groups.set("main", filtered);
    return groups;
  }
  for (const instance of instances) {
    if (!instance.enabled) continue;
    const zoneId = layoutConfig.placement[instance.type] || "main";
    if (!groups.has(zoneId)) {
      groups.set(zoneId, []);
    }
    groups.get(zoneId)!.push(instance);
  }
  return groups;
}

export default function ClassicTemplate({ instances, customizations, layoutConfig }: Props) {
  const colors = customizations?.colors || { header: "#000000", divider: "#d1d5db" };
  const fonts = customizations?.fonts || { body: "Georgia, Crimson, serif", heading: "Georgia, Crimson, serif" };
  const spacing = customizations?.spacing || { section_gap: "20px" };

  const style = {
    fontFamily: fonts.body,
    "--heading-font": fonts.heading,
    "--header-color": colors.header,
    "--divider-color": colors.divider,
    "--section-gap": spacing.section_gap,
  } as React.CSSProperties;

  const groups = groupByZone(instances, layoutConfig);

  // If layoutConfig is provided with zones, render zone-by-zone grouped by row
  if (layoutConfig && layoutConfig.zones) {
    // Group zones by row (default 0)
    const rows = new Map<number, typeof layoutConfig.zones>();
    for (const zone of layoutConfig.zones) {
      const r = zone.row ?? 0;
      if (!rows.has(r)) rows.set(r, []);
      rows.get(r)!.push(zone);
    }

    return (
      <div style={style} className="flex min-h-[297mm] flex-col">
        {[...rows.entries()]
          .sort(([a], [b]) => a - b)
          .map(([rowNum, rowZones]) => {
            const rowHeight = layoutConfig.rowHeights?.[rowNum];
            const rowFlex = rowHeight
              ? `${parseInt(rowHeight)} 0 0%`
              : "1 0 auto";
            const displayRowZones = normalizeWidths(rowZones);
            return (
              <div key={rowNum} className="flex" style={{ flex: rowFlex }}>
              {displayRowZones.map((zone) => {
                const zoneInstances = groups.get(zone.id) || [];
                const zoneStyle: React.CSSProperties = {};
                if (zone.styles) {
                  Object.entries(zone.styles).forEach(([k, v]) => {
                    const camelKey = k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
                    (zoneStyle as Record<string, string>)[camelKey] = v;
                  });
                }
                return (
                  <div key={zone.id} style={{ ...zoneStyle, flexShrink: 0 }}>
                    {zoneInstances.map((instance, i) => (
                      <div key={instance.id}>
                        <div style={{ marginBottom: "var(--section-gap)" }}>
                          <SectionPreviewPanel instance={instance} />
                        </div>
                        {i < zoneInstances.length - 1 && (
                          <hr className="my-4" style={{ borderColor: "var(--divider-color)" }} />
                        )}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          );
          })}
      </div>
    );
  }

  // Fallback to hardcoded layout
  const filtered = instances.filter((i) => i.enabled);
  return (
    <div style={style} className="p-8">
      {filtered.map((instance, i) => (
        <div key={instance.id}>
          <div style={{ marginBottom: "var(--section-gap)" }}>
            <SectionPreviewPanel instance={instance} />
          </div>
          {i < filtered.length - 1 && (
            <hr className="my-4" style={{ borderColor: "var(--divider-color)" }} />
          )}
        </div>
      ))}
    </div>
  );
}
