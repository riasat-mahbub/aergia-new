import { useEffect, useRef, useState } from "react";
import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";
import client from "../../lib/api/client";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
  layoutConfig?: LayoutConfig;
  manifest?: Record<string, any>;
}

// 297mm at 96dpi (1mm = 96/25.4 ≈ 3.78px). Matches `@page { size: A4; margin: 0 }`
// in api/app/services/renderer/ir.py, which is what Chromium's print engine cuts on.
const PAGE_HEIGHT_PX = 1122;

export default function UserTemplateRenderer({ instances, customizations, templateContent, layoutConfig, manifest }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [html, setHtml] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [iframeHeight, setIframeHeight] = useState<number>(PAGE_HEIGHT_PX);

  useEffect(() => {
    const zones = layoutConfig?.zones?.length ? layoutConfig.zones : (manifest?.zones || []);
    const placement = (layoutConfig?.placement && Object.keys(layoutConfig.placement).length > 0) ? layoutConfig.placement : (manifest?.placement || {});
    if (!zones.length || !Object.keys(placement).length) return;

    // The CV layout rides in `customizations.layout` (the canonical wire
    // shape the resolver merges over the manifest). Do NOT inject a legacy
    // `layout_config` key into the manifest — the v2 schema ignores it and a
    // manifest-less object fails TemplateManifest validation.
    const customizationsPayload = {
      ...(customizations || {}),
      layout: { zones, placement },
    };

    async function renderTemplate() {
      try {
        setError(null);
        const response = await client.post("/render/html", {
          manifest: manifest || null,
          cv_sections: instances,
          customizations: customizationsPayload,
          preview: true,
        });
        setHtml(response.data.html);
      } catch (err) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          || (err as Error)?.message
          || "Failed to render template";
        setError(detail);
        setHtml("");
      }
    }
    renderTemplate();
  }, [manifest, templateContent, instances, customizations, layoutConfig]);

  useEffect(() => {
    if (!html || !iframeRef.current) return;

    const iframe = iframeRef.current;
    const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!iframeDoc) return;

    iframeDoc.open();
    iframeDoc.write(html);
    iframeDoc.close();
    // Measure the rendered document so the iframe can grow past one A4 page.
    // Read body.scrollHeight — not documentElement.scrollHeight — because the
    // html element fills the iframe viewport and reports the iframe's own
    // height once the iframe has been grown past the content, which would
    // freeze the measurement in a positive feedback loop.
    const fit = () => {
      const body = iframeDoc.body;
      if (!body) return;
      const h = body.scrollHeight;
      if (h) setIframeHeight(h);
    };
    requestAnimationFrame(fit);
  }, [html]);

  const pageCount = Math.max(1, Math.ceil(iframeHeight / PAGE_HEIGHT_PX));
  const breakRules = Array.from({ length: Math.max(0, pageCount - 1) }, (_, i) => i + 1);

  if (error) {
    return (
      <div className="flex items-center justify-center rounded border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="relative mx-auto max-w-[210mm] rounded bg-white shadow-sm">
      <iframe
        ref={iframeRef}
        title="User Template Preview"
        className="w-full"
        style={{ height: `${iframeHeight}px` }}
        sandbox="allow-scripts allow-same-origin allow-popups"
      />
      {breakRules.map((n) => (
        <div
          key={n}
          aria-hidden="true"
          className="pointer-events-none absolute left-0 right-0"
          style={{ top: `${n * PAGE_HEIGHT_PX}px` }}
        >
          <div className="border-t border-dashed border-rose-400" />
          <div className="absolute -top-2 right-2 rounded bg-rose-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-700">
            Page {n + 1} starts
          </div>
        </div>
      ))}
    </div>
  );
}
