import { useEffect, useRef } from "react";
import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import { renderUserTemplateHTML } from "../../lib/sections/renderHTML";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
  layoutConfig?: LayoutConfig;
  defaultCustomizations?: Record<string, unknown>;
}

export default function UserTemplateRenderer({ instances, customizations, templateContent, layoutConfig, defaultCustomizations }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!templateContent || !iframeRef.current) return;

    const html = renderUserTemplateHTML(
      instances,
      customizations || {},
      templateContent,
      defaultCustomizations,
      layoutConfig,
    );

    const iframe = iframeRef.current;
    const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!iframeDoc) return;

    iframeDoc.open();
    iframeDoc.write(html);
    iframeDoc.close();
  }, [templateContent, instances, customizations, layoutConfig, defaultCustomizations]);

  return (
    <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
      <iframe
        ref={iframeRef}
        title="User Template Preview"
        className="h-[297mm] w-full"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}
