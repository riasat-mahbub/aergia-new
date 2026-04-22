import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  layoutConfig?: LayoutConfig;
}

function groupByZone(instances: SectionInstance[], layoutConfig: LayoutConfig | undefined): Map<string, SectionInstance[]> {
  const groups = new Map<string, SectionInstance[]>();
  if (!layoutConfig || !layoutConfig.placement) {
    groups.set("main", instances.filter((i) => i.enabled));
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

export default function MinimalTemplate({ instances, customizations, layoutConfig }: Props) {
  const colors = customizations?.colors || { text: "#374151", heading: "#111827" };
  const fonts = customizations?.fonts || { body: "system-ui, sans-serif", heading: "system-ui, sans-serif" };
  const spacing = customizations?.spacing || { section_gap: "16px" };

  const style = {
    fontFamily: fonts.body,
    "--heading-font": fonts.heading,
    "--text-color": colors.text,
    "--heading-color": colors.heading,
    "--section-gap": spacing.section_gap,
  } as React.CSSProperties;

  const groups = groupByZone(instances, layoutConfig);

  // If layoutConfig is provided with zones, render zone-by-zone
  if (layoutConfig && layoutConfig.zones) {
    return (
      <div style={style} className="text-gray-700">
        {layoutConfig.zones.map((zone) => {
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
              {zoneInstances.map((instance) => (
                <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
                  <SectionPreviewPanel instance={instance} />
                </div>
              ))}
            </div>
          );
        })}
      </div>
    );
  }

  // Fallback to hardcoded layout
  return (
    <div style={style} className="p-8 text-gray-700">
      {instances.filter((i) => i.enabled).map((instance) => (
        <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
          <SectionPreviewPanel instance={instance} />
        </div>
      ))}
    </div>
  );
}
