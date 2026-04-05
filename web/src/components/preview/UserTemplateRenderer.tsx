import { useEffect, useRef } from "react";
import type { SectionInstance } from "../../lib/sections/types";

interface Props {
  templateId: string;
  instances: SectionInstance[];
  customizations?: Record<string, any>;
  templateContent?: string;
}

export default function UserTemplateRenderer({ templateId, instances, customizations, templateContent }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!templateContent || !iframeRef.current) return;

    const iframe = iframeRef.current;
    const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (!iframeDoc) return;

    iframeDoc.open();
    iframeDoc.write(templateContent);
    iframeDoc.close();

    const script = iframeDoc.createElement("script");
    script.textContent = `window.__CV_DATA__ = ${JSON.stringify({ instances })}`;
    iframeDoc.body.appendChild(script);
  }, [templateContent, instances]);

  return (
    <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
      <iframe
        ref={iframeRef}
        title="User Template Preview"
        className="h-[297mm] w-full"
        sandbox="allow-scripts allow-same-origin"
        srcDoc={templateContent}
      />
    </div>
  );
}