import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { CVListItem } from "@/features/cvs";
import type { Application } from "../../types";
import ScannerAnalysisDrawer from "../ScannerAnalysisDrawer";
import ScannerJobFitBadge from "../ScannerJobFitBadge";
import { buildScannerReportViewModel, scannerStatusLabel } from "../../domain/scannerReport";

interface ApplicationScannerPanelProps {
  application: Application;
  availableCVs: CVListItem[];
  cvListLoading: boolean;
  onLinkCV: (cvId: string | null) => Promise<unknown>;
  onScan: () => Promise<unknown>;
  analysisOpen: boolean;
  onOpenAnalysis: () => void;
  onCloseAnalysis: () => void;
  onTailor?: () => void;
}

export default function ApplicationScannerPanel({
  application,
  availableCVs,
  cvListLoading,
  onLinkCV,
  onScan,
  analysisOpen,
  onOpenAnalysis,
  onCloseAnalysis,
  onTailor,
}: ApplicationScannerPanelProps) {
  const [isScanning, setIsScanning] = useState(false);
  const [isLinkingCV, setIsLinkingCV] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const result = application.scanner_result ?? null;
  const scannerStatus = application.scanner_status ?? (result ? "current" : "not_scanned");
  const report = result ? buildScannerReportViewModel(result, application) : null;
  const linkableCVs = availableCVs.filter(
    (cv) => cv.id === application.cv_id || !cv.application || cv.application.id === application.id,
  );

  const handleScan = async () => {
    setIsScanning(true);
    setError(null);
    try {
      await onScan();
    } catch {
      setError("Unable to run the scanner. Please try again.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleCVChange = async (cvId: string) => {
    setIsLinkingCV(true);
    setLinkError(null);
    try {
      await onLinkCV(cvId || null);
    } catch {
      setLinkError("Unable to update the linked CV.");
    } finally {
      setIsLinkingCV(false);
    }
  };

  return (
    <>
      <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Scanner analysis</h2>
              <span className="text-xs text-app-ink-3">{scannerStatusLabel(scannerStatus)}</span>
            </div>
            <p className="mt-1 max-w-xl text-sm leading-6 text-app-ink-2">Job Fit, keyword wording, ATS readiness, resume quality, and PDF recovery are reported separately.</p>
            {result && <p className="mt-1 text-xs text-app-ink-3">Last analyzed {new Date(result.created_at).toLocaleString()}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ScannerJobFitBadge application={application} onClick={onOpenAnalysis} />
            <button type="button" onClick={onOpenAnalysis} className="rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">Open analysis</button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1">
            <label htmlFor="application-scanner-cv" className="text-sm font-medium text-app-ink-2">CV used for this scan</label>
            <select id="application-scanner-cv" value={application.cv_id ?? ""} disabled={cvListLoading || isLinkingCV} onChange={(event) => handleCVChange(event.target.value)} className="mt-1 block w-full rounded-md border border-app-rule-strong bg-app-surface px-3 py-2 text-sm disabled:opacity-50">
              <option value="">No CV linked</option>
              {linkableCVs.map((cv) => <option key={cv.id} value={cv.id}>{cv.title}</option>)}
            </select>
          </div>
          <button type="button" onClick={handleScan} disabled={!application.cv_id || isScanning} className="inline-flex items-center gap-2 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:cursor-not-allowed disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${isScanning ? "animate-spin" : ""}`} aria-hidden="true" />
            {isScanning ? "Analyzing…" : scannerStatus === "current" ? "Run again" : "Analyze CV"}
          </button>
        </div>
        {isLinkingCV && <p className="mt-2 text-xs text-app-ink-3" role="status">Updating CV link…</p>}
        {!cvListLoading && linkableCVs.length === 0 && <p className="mt-2 text-xs text-app-ink-3">No unassigned CVs are available to link.</p>}
        {linkError && <p role="alert" className="mt-2 text-sm text-app-danger">{linkError}</p>}
        {error && <p role="alert" className="mt-3 rounded-md bg-app-danger-soft px-3 py-2 text-sm text-app-danger">{error}</p>}
        {!application.cv_id && <p className="mt-3 text-sm text-app-ink-2">Link a CV to this application before running the scanner.</p>}
        {(scannerStatus === "needs_rescan" || scannerStatus === "stale") && <p className="mt-3 text-sm text-app-warning">This analysis is out of date because the CV, job, or scanner contract changed. Analyze again to refresh it.</p>}
        {report && (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-app-primary-soft px-3 py-3"><p className="text-xs text-app-ink-3">Job Fit</p><p className="mt-1 text-xl font-semibold text-app-ink">{report.score.jobFit === null ? "—" : `${Math.round(report.score.jobFit * 100)}%`}</p></div>
            <div className="rounded-lg bg-app-canvas px-3 py-3"><p className="text-xs text-app-ink-3">Requirements</p><p className="mt-1 text-sm font-semibold text-app-ink">{report.score.coveredCount} covered · {report.score.partialCount} partial</p></div>
            <div className="rounded-lg bg-app-canvas px-3 py-3"><p className="text-xs text-app-ink-3">Term Visibility</p><p className="mt-1 text-sm font-semibold text-app-ink">{report.keywords.visibilityScore === null ? "—" : `${Math.round(report.keywords.visibilityScore * 100)}%`}</p></div>
          </div>
        )}
      </section>
      <ScannerAnalysisDrawer open={analysisOpen} application={application} onClose={onCloseAnalysis} onScan={handleScan} onTailor={onTailor} scanning={isScanning} scanError={error} />
    </>
  );
}
