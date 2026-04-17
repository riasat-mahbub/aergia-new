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
    // Default: all in "main"
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

export default function ModernTemplate({ instances, customizations, layoutConfig }: Props) {
  const colors = customizations?.colors || { accent: "#2563eb", bg_sidebar: "#f8fafc" };
  const fonts = customizations?.fonts || { body: "Inter, system-ui, sans-serif", heading: "Inter, system-ui, sans-serif" };
  const spacing = customizations?.spacing || { section_gap: "24px" };

  const style = {
    fontFamily: fonts.body,
    "--heading-font": fonts.heading,
    "--accent": colors.accent,
    "--bg-sidebar": colors.bg_sidebar,
    "--section-gap": spacing.section_gap,
  } as React.CSSProperties;

  const groups = groupByZone(instances, layoutConfig);

  // If layoutConfig is provided with zones, render zone-by-zone
  if (layoutConfig && layoutConfig.zones) {
    return (
      <div style={style} className="flex min-h-[297mm]">
        {layoutConfig.zones.map((zone) => {
          const zoneInstances = groups.get(zone.id) || [];
          const zoneStyle: React.CSSProperties = {};
          if (zone.styles) {
            Object.entries(zone.styles).forEach(([k, v]) => {
              // Convert kebab-case to camelCase for React CSS properties
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

  // Fallback to hardcoded layout (backwards compatible)
  const sidebarInstances = instances.filter((i) => i.type === "profile");
  const mainInstances = instances.filter((i) => i.type !== "profile");

  return (
    <div style={style} className="flex min-h-[297mm]">
      <div className="w-[30%] p-6" style={{ backgroundColor: "var(--bg-sidebar)" }}>
        {sidebarInstances.map((instance) => (
          <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
            <SectionPreviewPanel instance={instance} />
          </div>
        ))}
      </div>
      <div className="w-[70%] p-6">
        <div className="mb-6 h-1 w-16" style={{ backgroundColor: "var(--accent)" }} />
        {mainInstances.map((instance) => (
          <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
            <SectionPreviewPanel instance={instance} />
          </div>
        ))}
      </div>
    </div>
  );
}
