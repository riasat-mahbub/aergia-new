import { useRef, useState, type KeyboardEvent } from "react";
import { ChevronDown, Download, Loader2 } from "lucide-react";
import { exportDOCX, exportPDF } from "../api/cvs";
import { downloadBlob } from "@/shared/browser/downloadBlob";
import { useToastStore } from "@/shared/state/uiStore";

type ExportFormat = "pdf" | "docx";

interface CVExportControlProps {
  cvId: string;
  pdfFilename: string;
  filenameBase?: string;
  onBeforeExport?: () => Promise<boolean | void>;
}

function safeWordFilename(filenameBase?: string): string {
  const cleaned = (filenameBase ?? "")
    .normalize("NFKC")
    .replace(/[\u0000-\u001f\u007f-\u009f<>:"/\\|?*]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/[. ]+$/g, "")
    .trim()
    .slice(0, 120);
  if (!cleaned) return "cv.docx";

  const safeBase = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(cleaned)
    ? `_${cleaned}`
    : cleaned;
  return `${safeBase}.docx`;
}

const FORMAT_LABELS: Record<ExportFormat, string> = {
  pdf: "PDF",
  docx: "Word document",
};

export function CVExportControl({
  cvId,
  pdfFilename,
  filenameBase,
  onBeforeExport,
}: CVExportControlProps) {
  const menuRef = useRef<HTMLDetailsElement>(null);
  const activeExportRef = useRef<ExportFormat | null>(null);
  const [activeExport, setActiveExport] = useState<ExportFormat | null>(null);
  const [failedExport, setFailedExport] = useState<ExportFormat | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const addToast = useToastStore((state) => state.addToast);

  const closeMenu = (restoreFocus: boolean) => {
    const menu = menuRef.current;
    if (!menu) return;

    const focusIsInside = menu.contains(document.activeElement);
    menu.open = false;
    if (restoreFocus && focusIsInside) menu.querySelector("summary")?.focus();
  };

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDetailsElement>) => {
    const menu = menuRef.current;
    if (event.key !== "Escape" || !menu?.open || !menu.contains(document.activeElement)) return;

    event.preventDefault();
    event.stopPropagation();
    closeMenu(true);
  };

  const runExport = async (format: ExportFormat) => {
    if (activeExportRef.current) return;

    activeExportRef.current = format;
    setActiveExport(format);
    setFailedExport(null);
    setAnnouncement(`Preparing ${FORMAT_LABELS[format]} download.`);
    closeMenu(true);

    let exportRequestStarted = false;
    try {
      const mayContinue = await onBeforeExport?.();
      if (mayContinue === false) {
        setAnnouncement("Export stopped because the selected CV changed while it was being saved.");
        return;
      }

      exportRequestStarted = true;
      const blob = format === "pdf" ? await exportPDF(cvId) : await exportDOCX(cvId);
      const filename = format === "pdf" ? pdfFilename : safeWordFilename(filenameBase);
      downloadBlob(blob, filename);
      setAnnouncement(`${FORMAT_LABELS[format]} download started.`);
      addToast(
        format === "pdf" ? "PDF exported successfully" : "Word document exported successfully",
        "success",
      );
    } catch {
      if (exportRequestStarted) setFailedExport(format);
      setAnnouncement("");
    } finally {
      activeExportRef.current = null;
      setActiveExport(null);
    }
  };

  const activeLabel = activeExport
    ? `Exporting ${activeExport === "pdf" ? "PDF" : "Word"}…`
    : "Export";

  return (
    <div className="relative inline-flex flex-col items-end">
      <details ref={menuRef} onKeyDown={handleMenuKeyDown}>
        <summary className="inline-flex min-h-9 cursor-pointer list-none items-center gap-1.5 rounded-md border border-app-rule-strong bg-app-surface px-3 py-1.5 text-xs font-medium text-app-ink-2 transition-colors hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 [&::-webkit-details-marker]:hidden">
          {activeExport ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span>{activeLabel}</span>
          {!activeExport && <ChevronDown className="h-3 w-3" aria-hidden="true" />}
        </summary>
        <div className="absolute right-0 top-full z-30 mt-2 w-56 max-w-[calc(100vw-2rem)] rounded-md border border-app-rule bg-app-surface p-1 shadow-md">
          <button
            type="button"
            onClick={() => { void runExport("pdf"); }}
            disabled={activeExport !== null}
            className="flex w-full flex-col items-start rounded px-3 py-2 text-left text-sm font-medium text-app-ink hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span>PDF</span>
            <span className="text-xs font-normal text-app-ink-3">Print-ready document</span>
          </button>
          <button
            type="button"
            onClick={() => { void runExport("docx"); }}
            disabled={activeExport !== null}
            className="flex w-full flex-col items-start rounded px-3 py-2 text-left text-sm font-medium text-app-ink hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span>Word (.docx)</span>
            <span className="text-xs font-normal text-app-ink-3">Editable single-column document</span>
          </button>
        </div>
      </details>
      {failedExport && (
        <p className="absolute right-0 top-full z-20 mt-1 w-56 rounded-md border border-app-danger/30 bg-app-surface px-3 py-2 text-xs leading-5 text-app-danger shadow-sm" role="alert">
          {FORMAT_LABELS[failedExport]} download failed.{" "}
          <button
            type="button"
            onClick={() => { void runExport(failedExport); }}
            className="font-semibold underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary"
          >
            Try again
          </button>
        </p>
      )}
      <span className="sr-only" role="status" aria-live="polite" aria-atomic="true">{announcement}</span>
    </div>
  );
}
