import ModernTemplate from "./ModernTemplate";
import ClassicTemplate from "./ClassicTemplate";
import MinimalTemplate from "./MinimalTemplate";
import type { SectionInstance } from "../../lib/sections/types";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
}

export default function TemplateSwitcher({ templateId, instances, customizations }: Props) {
  const shared = { instances, customizations };

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
