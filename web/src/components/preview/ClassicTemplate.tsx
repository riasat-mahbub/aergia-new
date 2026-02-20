import type { SectionInstance } from "../../lib/sections/types";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  instances: SectionInstance[];
  customizations?: Record<string, any>;
}

export default function ClassicTemplate({ instances, customizations }: Props) {
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

  return (
    <div style={style} className="p-8">
      {instances.map((instance, i) => (
        <div key={instance.id}>
          <div style={{ marginBottom: "var(--section-gap)" }}>
            <SectionPreviewPanel instance={instance} />
          </div>
          {i < instances.length - 1 && (
            <hr className="my-4" style={{ borderColor: "var(--divider-color)" }} />
          )}
        </div>
      ))}
    </div>
  );
}
