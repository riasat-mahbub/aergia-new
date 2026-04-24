import { useState } from "react";
import type { LayoutConfig } from "../../lib/sections/types";
import StyleEditor from "../customization/StyleEditor";
import ZonesSection from "../customization/ZonesSection";

interface Props {
  layoutConfig: LayoutConfig;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  customizations: Record<string, any>;
  onCustomizationsChange: (customizations: Record<string, any>) => void;
}

const FONT_OPTIONS = [
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

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
