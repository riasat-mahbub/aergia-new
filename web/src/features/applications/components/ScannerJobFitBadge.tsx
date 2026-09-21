import { RefreshCw } from "lucide-react";
import type { Application } from "../types";
import { scannerBadgeState } from "../domain/scannerReport";

interface ScannerJobFitBadgeProps {
  application: Application;
  onClick: () => void;
  disabled?: boolean;
}

export default function ScannerJobFitBadge({ application, onClick, disabled = false }: ScannerJobFitBadgeProps) {
  const badge = scannerBadgeState(application);
  const isAttention = badge.state === "stale" || badge.state === "needs_rescan";
  const isNotScanned = badge.state === "not_scanned";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={badge.label}
      title={isNotScanned ? "Run the scanner to analyze this CV" : "Open resume analysis"}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary focus-visible:ring-offset-2 ${
        isAttention
          ? "border-app-warning/40 bg-app-warning-soft text-app-warning hover:bg-app-warning/20"
          : isNotScanned
            ? "border-app-primary-soft bg-app-primary-soft text-app-primary hover:bg-app-primary/10"
            : "border-app-rule-strong bg-app-surface text-app-ink-2 hover:bg-app-surface-muted"
      } disabled:cursor-not-allowed disabled:opacity-50`}
    >
      {isAttention && <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
      <span>{badge.label}</span>
    </button>
  );
}

