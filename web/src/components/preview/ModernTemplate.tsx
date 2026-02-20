import type { SectionInstance } from "../../lib/sections/types";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  instances: SectionInstance[];
  customizations?: Record<string, any>;
}

export default function ModernTemplate({ instances, customizations }: Props) {
  const colors = customizations?.colors || { accent: "#2563eb", bg_sidebar: "#f8fafc" };
  const fonts = customizations?.fonts || { body: "Inter, system-ui, sans-serif", heading: "Inter, system-ui, sans-serif" };
  const spacing = customizations?.spacing || { section_gap: "24px" };

  const sidebarInstances = instances.filter((i) => i.type === "profile");
  const mainInstances = instances.filter((i) => i.type !== "profile");

  const style = {
    fontFamily: fonts.body,
    "--heading-font": fonts.heading,
    "--accent": colors.accent,
    "--bg-sidebar": colors.bg_sidebar,
    "--section-gap": spacing.section_gap,
  } as React.CSSProperties;

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
