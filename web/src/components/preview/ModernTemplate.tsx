import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  layoutConfig?: LayoutConfig;
}

function getHeaderInstances(instances: SectionInstance[], layoutConfig: LayoutConfig | undefined): SectionInstance[] {
  if (!layoutConfig?.header?.enabled || !layoutConfig.header.sections.length) return [];
  const headerSet = new Set(layoutConfig.header.sections);
  return instances.filter((i) => i.enabled && headerSet.has(i.type));
}

function groupByZone(instances: SectionInstance[], layoutConfig: LayoutConfig | undefined): Map<string, SectionInstance[]> {
  const groups = new Map<string, SectionInstance[]>();
  const headerTypes = new Set(layoutConfig?.header?.enabled ? layoutConfig.header.sections : []);
  if (!layoutConfig || !layoutConfig.placement) {
    const filtered = instances.filter((i) => i.enabled && !headerTypes.has(i.type));
    groups.set("main", filtered);
    return groups;
  }
  for (const instance of instances) {
    if (!instance.enabled) continue;
    if (headerTypes.has(instance.type)) continue;
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
  const headerInstances = getHeaderInstances(instances, layoutConfig);

  // If layoutConfig is provided with zones, render zone-by-zone
  if (layoutConfig && layoutConfig.zones) {
    const headerStyles: React.CSSProperties = {};
    if (layoutConfig.header?.styles) {
      Object.entries(layoutConfig.header.styles).forEach(([k, v]) => {
        const camelKey = k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        (headerStyles as Record<string, string>)[camelKey] = v;
      });
    }

    return (
      <div style={style} className="min-h-[297mm]">
        {headerInstances.length > 0 && (
          <div style={headerStyles}>
            {headerInstances.map((instance) => (
              <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
                <SectionPreviewPanel instance={instance} />
              </div>
            ))}
          </div>
        )}
        <div className="flex">
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
