import UserTemplateRenderer from "./UserTemplateRenderer";
import type { SectionInstance } from "../../lib/sections/types";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
  manifest?: Record<string, any>;
}

export default function TemplateSwitcher({ templateId, instances, customizations, templateContent, manifest }: Props) {
  return <UserTemplateRenderer
    templateId={templateId}
    instances={instances}
    templateContent={templateContent}
    customizations={customizations}
    manifest={manifest}
  />;
}
