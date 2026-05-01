import UserTemplateRenderer from "./UserTemplateRenderer";
import type { SectionInstance } from "../../lib/sections/types";
import type { LayoutConfig } from "../../lib/sections/types";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
  layoutConfig?: LayoutConfig;
  defaultCustomizations?: Record<string, unknown>;
  manifest?: Record<string, any>;
}

export default function TemplateSwitcher({ templateId, instances, customizations, templateContent, layoutConfig, defaultCustomizations, manifest }: Props) {
  return <UserTemplateRenderer 
    templateId={templateId} 
    instances={instances} 
    templateContent={templateContent} 
    layoutConfig={layoutConfig} 
    defaultCustomizations={defaultCustomizations}
    customizations={customizations}
    manifest={manifest}
  />;
}
