import type { SectionData } from "../../lib/sections/types";
import SectionPreviewPanel from "../sections/SectionPreviewPanel";

interface Props {
  sections: SectionData;
  order: string[];
  enabled: string[];
  customizations?: Record<string, any>;
}

export default function ClassicTemplate({ sections, order, enabled, customizations }: Props) {
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
      {order.map((s, i) => (
        <div key={s}>
          <div style={{ marginBottom: "var(--section-gap)" }}>
            <SectionPreviewPanel sectionType={s} data={sections} enabled={enabled.includes(s)} />
          </div>
          {i < order.length - 1 && (
            <hr className="my-4" style={{ borderColor: "var(--divider-color)" }} />
          )}
        </div>
      ))}
    </div>
  );
}
