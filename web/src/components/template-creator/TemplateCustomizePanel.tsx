import type { LayoutConfig } from "../../lib/sections/types";
import StyleEditor from "../customization/StyleEditor";
import ZonesSection from "../customization/ZonesSection";

interface Props {
  layoutConfig: LayoutConfig;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  customizations: Record<string, any>;
  onCustomizationsChange: (customizations: Record<string, any>) => void;
  assets?: Record<string, string>;
}

export default function TemplateCustomizePanel({
  layoutConfig,
  onLayoutConfigChange,
  customizations,
  onCustomizationsChange,
  assets,
}: Props) {
  return (
    <div>
      <ZonesSection
        layoutConfig={layoutConfig}
        onChange={onLayoutConfigChange}
        title="Zones & Layout"
        assets={assets}
      />
      <StyleEditor
        customizations={customizations}
        onChange={onCustomizationsChange}
        title="Colors & Fonts"
      />
    </div>
  );
}
