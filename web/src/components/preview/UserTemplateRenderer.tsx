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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const zones = layoutConfig?.zones?.length ? layoutConfig.zones : (manifest?.zones || []);
    const placement = (layoutConfig?.placement && Object.keys(layoutConfig.placement).length > 0) ? layoutConfig.placement : (manifest?.placement || {});
    if (!zones.length || !Object.keys(placement).length) return;

    const renderManifest = {
      ...manifest,
      layout_config: { zones, placement },
    };

    async function renderTemplate() {
      try {
        setError(null);
        const response = await client.post("/render/html", {
          manifest: renderManifest,
          cv_data: { instances },
          customizations: customizations || {},
        });
        setHtml(response.data.html);
      } catch (err) {
        const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          || (err as Error)?.message
          || "Failed to render template";
        setError(message);
        setHtml("");
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

  if (error) {
    return (
      <div className="flex items-center justify-center rounded border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {error}
      </div>
    );
  }

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
