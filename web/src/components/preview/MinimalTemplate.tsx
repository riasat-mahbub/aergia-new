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
      <div style={style} className="text-gray-700">
        {headerInstances.length > 0 && (
          <div style={headerStyles}>
            {headerInstances.map((instance) => (
              <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
                <SectionPreviewPanel instance={instance} />
              </div>
            ))}
          </div>
        )}
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
