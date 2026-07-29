import { type ChangeEvent, useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";

import { importPDF } from "../../lib/api/imports";
import { useToastStore } from "../../lib/store/uiStore";
import { useCVStore } from "../../lib/store/cvStore";
import type { SectionInstance } from "../../lib/sections/types";

interface ImportPDFButtonProps {
  /** When false, the button is disabled (used during save in flight). */
  enabled?: boolean;
}

export default function ImportPDFButton({ enabled = true }: ImportPDFButtonProps) {
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const addToast = useToastStore((s) => s.addToast);

  const handleClick = () => {
    if (!enabled) return;
    fileRef.current?.click();
  };

  const handleChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setLoading(true);
    try {
      const parsed = await importPDF(file);
      const apply = useCVStore.getState().patchCurrentCV;
      if (apply) {
        apply({ sections: parsed.sections as unknown as SectionInstance[] });
      }
      const heading = file.name && file.name.length > 0 ? file.name : "PDF";
      addToast(
        `${heading} parsed — ${parsed.sections.length} sections. Review and save.`,
        "success"
      );

      if (parsed.meta.warnings.length > 0) {
        const tail = parsed.meta.warnings.join(", ");
        addToast(`Parser notes: ${tail}`, "info");
      }
    } catch {
      addToast("Failed to import PDF", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={loading || !enabled}
        className="flex items-center gap-1.5 rounded-md border border-blue-600 bg-white px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50 disabled:opacity-50"
        title="Import a PDF and pre-fill the current CV"
        type="button"
      >
        {loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <FileUp className="h-3.5 w-3.5" />
        )}
        {loading ? "Parsing..." : "Import PDF"}
      </button>
      <input
        ref={fileRef}
        type="file"
        accept="application/pdf"
        onChange={handleChange}
        className="hidden"
      />
    </>
  );
}
