import { useEffect, useRef, useState } from "react";
import type { SectionInstance } from "../../lib/sections/types";
import client from "../../lib/api/client";

interface Props {
  instances: SectionInstance[];
  customizations?: {
    layout?: { zones?: unknown[]; placement?: Record<string, string> };
    [key: string]: unknown;
  };
  manifest?: Record<string, unknown>;
}

// 297mm at 96dpi (1mm = 96/25.4 ≈ 3.78px). Matches the A4 page size
// in `api/app/services/renderer/resolve.py`'s `PRINT_STYLES`.
const PAGE_HEIGHT_PX = 1122;

export default function UserTemplateRenderer({ instances, customizations, manifest }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [html, setHtml] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [iframeHeight, setIframeHeight] = useState<number>(PAGE_HEIGHT_PX);

  useEffect(() => {
    // The CV layout rides in `customizations.layout` (the canonical wire
    // shape the resolver merges over the manifest). Do NOT inject a legacy
    // `layout_config` key into the manifest — the v2 schema ignores it and a
    // manifest-less object fails TemplateManifest validation. Pass
    // customizations through unchanged so the user's zone styles (width,
    // background, padding) and instance-keyed placement reach the resolver.
    if (!customizations?.layout?.zones?.length) return;

    const customizationsPayload = customizations;
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
      } catch {
        setError("Failed to render template");
        setHtml("");
      }
    }
    renderTemplate();
  }, [manifest, instances, customizations]);

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
        sandbox="allow-same-origin"
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
