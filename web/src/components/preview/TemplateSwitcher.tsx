import ModernTemplate from "./ModernTemplate";
import ClassicTemplate from "./ClassicTemplate";
import MinimalTemplate from "./MinimalTemplate";
import UserTemplateRenderer from "./UserTemplateRenderer";
import type { SectionInstance } from "../../lib/sections/types";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
}

export default function TemplateSwitcher({ templateId, instances, customizations, templateContent }: Props) {
  if (templateId.startsWith("user_")) {
    return <UserTemplateRenderer templateId={templateId} instances={instances} templateContent={templateContent} />;
  }

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
