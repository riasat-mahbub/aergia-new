import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { exportPDF, downloadPDF } from "../../lib/api/cvs";
import { useToastStore } from "../../lib/store/uiStore";

interface ExportPDFButtonProps {
  cvId: string;
  cvTitle?: string;
}

export default function ExportPDFButton({ cvId, cvTitle }: ExportPDFButtonProps) {
  const [loading, setLoading] = useState(false);
  const addToast = useToastStore((s) => s.addToast);

  const handleExport = async () => {
    setLoading(true);
    try {
      const blob = await exportPDF(cvId);
      const filename = cvTitle
        ? `${cvTitle.replace(/[^a-zA-Z0-9]/g, "_")}.pdf`
        : "cv.pdf";
      downloadPDF(blob, filename);
      addToast("PDF exported successfully", "success");
    } catch {
      addToast("Failed to export PDF", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={loading}
      className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
      title="Export PDF"
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <FileDown className="h-3.5 w-3.5" />
      )}
      {loading ? "Exporting..." : "PDF"}
    </button>
  );
}
