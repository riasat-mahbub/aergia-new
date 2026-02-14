import ModernTemplate from "./ModernTemplate";
import ClassicTemplate from "./ClassicTemplate";
import MinimalTemplate from "./MinimalTemplate";
import type { SectionData } from "../../lib/sections/types";

interface Props {
  templateId: string;
  sections: SectionData;
  order: string[];
  enabled: string[];
  customizations?: Record<string, any>;
}

export default function TemplateSwitcher({ templateId, sections, order, enabled, customizations }: Props) {
  const shared = { sections, order, enabled, customizations };

  switch (templateId) {
    case "generic-classic":
      return <ClassicTemplate {...shared} />;
    case "generic-minimal":
      return <MinimalTemplate {...shared} />;
    case "generic-modern":
    default:
      return <ModernTemplate {...shared} />;
  }
}
