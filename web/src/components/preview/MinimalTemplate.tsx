import type { SectionInstance } from "../../lib/sections/types";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  instances: SectionInstance[];
  customizations?: Record<string, any>;
}

export default function MinimalTemplate({ instances, customizations }: Props) {
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

  return (
    <div style={style} className="p-8 text-gray-700">
      {instances.map((instance) => (
        <div key={instance.id} style={{ marginBottom: "var(--section-gap)" }}>
          <SectionPreviewPanel instance={instance} />
        </div>
      ))}
    </div>
  );
}
