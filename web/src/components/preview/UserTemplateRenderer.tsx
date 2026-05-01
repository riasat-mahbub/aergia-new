import { useEffect, useRef, useState } from "react";
import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import client from "../../lib/api/client";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
  layoutConfig?: LayoutConfig;
  defaultCustomizations?: Record<string, unknown>;
  manifest?: Record<string, any>;
}

export default function UserTemplateRenderer({ instances, customizations, templateContent, layoutConfig, defaultCustomizations, manifest }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [html, setHtml] = useState<string>("");

  useEffect(() => {
    // Use manifest if available, otherwise fall back to layoutConfig
    const renderManifest = manifest || {
      zones: layoutConfig?.zones || [],
      placement: layoutConfig?.placement || {},
      globalStyleSchema: [],
      default_customizations: defaultCustomizations || {},
    };

    async function renderTemplate() {
      try {
        const response = await client.post("/api/v1/render/html", {
          manifest: renderManifest,
          cv_data: { instances },
          customizations: customizations || {},
        });
        setHtml(response.data.html);
      } catch (error) {
        console.error("Failed to render template:", error);
      }
    }
    renderTemplate();
  }, [manifest, templateContent, instances, customizations, layoutConfig, defaultCustomizations]);

  useEffect(() => {
    if (!html || !iframeRef.current) return;

    const iframe = iframeRef.current;
    const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!iframeDoc) return;

    iframeDoc.open();
    iframeDoc.write(html);
    iframeDoc.close();
  }, [html]);

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
