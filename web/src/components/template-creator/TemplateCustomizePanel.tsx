import type { LayoutConfig } from "../../lib/sections/types";
import StyleEditor from "../customization/StyleEditor";
import ZonesSection from "../customization/ZonesSection";

interface Props {
  layoutConfig: LayoutConfig;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  customizations: Record<string, any>;
  onCustomizationsChange: (customizations: Record<string, any>) => void;
}

export default function TemplateCustomizePanel({
  layoutConfig,
  onLayoutConfigChange,
  customizations,
  onCustomizationsChange,
}: Props) {
  return (
    <div>
      <ZonesSection
        layoutConfig={layoutConfig}
        onChange={onLayoutConfigChange}
        title="Zones & Layout"
      />
      <StyleEditor
        customizations={customizations}
        onChange={onCustomizationsChange}
        title="Colors & Fonts"
      />
    </div>
  );
}
