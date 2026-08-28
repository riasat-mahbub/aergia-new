import { useEffect, useRef, useState } from "react";
import type { SectionInstance } from "../../lib/sections/types";
import client from "../../lib/api/client";
import { applyPreviewPagination } from "./pagePagination";
import { A4_PAGE_GEOMETRY, PAGE_HEIGHT_PX, PAGE_WIDTH_PX, scaleForAvailableWidth } from "./pageGeometry";

interface Props {
  instances: SectionInstance[];
  customizations?: {
    layout?: { zones?: unknown[]; placement?: Record<string, string> };
    [key: string]: unknown;
  };
  manifest?: Record<string, unknown>;
}

export default function UserTemplateRenderer({ instances, customizations, manifest }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  const [html, setHtml] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [iframeHeight, setIframeHeight] = useState<number>(A4_PAGE_GEOMETRY.pageHeightPx);
  const [pageCount, setPageCount] = useState(1);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const updateScale = () => setScale(scaleForAvailableWidth(viewport.clientWidth));
    updateScale();

    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(updateScale);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    // The CV layout rides in `customizations.layout` (the canonical wire
    // shape the resolver merges over the manifest). Do NOT inject a legacy
    // `layout_config` key into the manifest — the v2 schema ignores it and a
    // manifest-less object fails TemplateManifest validation. Pass
    // customizations through unchanged so the user's zone styles (width,
    // background, padding) and instance-keyed placement reach the resolver.
    if (!customizations?.layout?.zones?.length) return;

    const customizationsPayload = customizations;
    let cancelled = false;
    async function renderTemplate() {
      try {
        setError(null);
        const response = await client.post("/render/html", {
          manifest: manifest || null,
          cv_sections: instances,
          customizations: customizationsPayload,
          preview: true,
        });
        if (!cancelled) setHtml(response.data.html);
      } catch {
        if (cancelled) return;
        setError("Failed to render template");
        setHtml("");
      }
    }
    renderTemplate();
    return () => { cancelled = true; };
  }, [manifest, instances, customizations]);

  useEffect(() => {
    if (!html || !iframeRef.current) return;

    const iframe = iframeRef.current;
    const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!iframeDoc) return;

    iframeDoc.open();
    iframeDoc.write(html);
    iframeDoc.close();

    let cancelled = false;
    let frameId: number | null = null;
    let observer: ResizeObserver | null = null;

    const nextFrame = () => new Promise<void>((resolve) => {
      const frameWindow = iframeDoc.defaultView;
      if (frameWindow?.requestAnimationFrame) {
        frameWindow.requestAnimationFrame(() => resolve());
      } else {
        window.requestAnimationFrame(() => resolve());
      }
    });

    const waitForImages = async () => {
      const images = Array.from(iframeDoc.images);
      await Promise.all(images.map((image) => {
        if (image.complete) return Promise.resolve();
        return new Promise<void>((resolve) => {
          image.addEventListener("load", () => resolve(), { once: true });
          image.addEventListener("error", () => resolve(), { once: true });
        });
      }));
    };

    const paginate = () => {
      if (cancelled || !iframeDoc.body) return;
      observer?.disconnect();
      const result = applyPreviewPagination(iframeDoc, A4_PAGE_GEOMETRY);
      setIframeHeight(result.height);
      setPageCount(result.pageCount);
      if (!cancelled && observer && iframeDoc.body) observer.observe(iframeDoc.body);
    };

    const settle = async () => {
      if (iframeDoc.fonts) await iframeDoc.fonts.ready;
      await waitForImages();
      await nextFrame();
      await nextFrame();
      if (cancelled) return;
      paginate();

      if (typeof ResizeObserver === "undefined" || !iframeDoc.body) return;
      observer = new ResizeObserver(() => {
        if (frameId !== null) return;
        frameId = window.requestAnimationFrame(() => {
          frameId = null;
          paginate();
        });
      });
      observer.observe(iframeDoc.body);
    };
    void settle();

    return () => {
      cancelled = true;
      observer?.disconnect();
      if (frameId !== null) window.cancelAnimationFrame(frameId);
    };
  }, [html]);

  const breakRules = Array.from({ length: Math.max(0, pageCount - 1) }, (_, i) => i + 1);

  if (error) {
    return (
      <div className="flex items-center justify-center rounded border border-app-danger bg-app-danger-soft p-6 text-sm text-app-danger">
        {error}
      </div>
    );
  }

  return (
    <div ref={viewportRef} className="w-full overflow-x-auto">
      <div
        className="mx-auto"
        style={{
          width: `${PAGE_WIDTH_PX * scale}px`,
          height: `${iframeHeight * scale}px`,
        }}
      >
        <div
          className="relative rounded bg-app-surface shadow-sm"
          style={{
            width: `${PAGE_WIDTH_PX}px`,
            height: `${iframeHeight}px`,
            transform: `scale(${scale})`,
            transformOrigin: "top left",
          }}
        >
          <iframe
            ref={iframeRef}
            title="User Template Preview"
            className="block border-0"
            style={{ width: `${PAGE_WIDTH_PX}px`, height: `${iframeHeight}px` }}
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
      </div>
    </div>
  );
}
