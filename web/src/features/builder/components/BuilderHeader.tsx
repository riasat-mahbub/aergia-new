import type { CVDetail } from "@/features/cvs";
import type { Application } from "@/features/applications";
import { ScannerJobFitBadge } from "@/features/applications";
import ExportPDFButton from "./ExportPDFButton";
import PromoteToLibraryButton from "./PromoteToLibraryButton";

interface BuilderHeaderProps {
  cv: CVDetail;
  cvId: string;
  applicationContext: Application | null;
  hasUnsavedChanges: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  showSavedFeedback: boolean;
  onBack: () => void;
  onOpenScanner: () => void;
  onSave: () => Promise<void>;
  formatLastSaved: (date: Date) => string;
}

export default function BuilderHeader({
  cv,
  cvId,
  applicationContext,
  hasUnsavedChanges,
  isSaving,
  lastSaved,
  showSavedFeedback,
  onBack,
  onOpenScanner,
  onSave,
  formatLastSaved,
}: BuilderHeaderProps) {
  return (
    <header className="flex items-center justify-between border-b bg-app-surface px-4 py-3">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-sm text-app-ink-3 hover:text-app-ink-2">
          &larr; Back
        </button>
        <h1 className="text-lg font-semibold text-app-ink">{cv.title}</h1>
        {applicationContext && (
          <ScannerJobFitBadge application={applicationContext} onClick={onOpenScanner} />
        )}
      </div>
      <div className="flex items-center gap-3">
        {hasUnsavedChanges && (
          <>
            <span className="h-2 w-2 rounded-full bg-app-warning" aria-label="Unsaved changes" />
            <span className="text-sm text-app-warning">Unsaved</span>
          </>
        )}
        {lastSaved && !isSaving && !showSavedFeedback && (
          <span className="text-xs text-app-ink-3">Saved {formatLastSaved(lastSaved)}</span>
        )}
        <button
          onClick={onSave}
          disabled={(!hasUnsavedChanges && !showSavedFeedback) || isSaving}
          className="rounded-md bg-app-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSaving ? "Saving..." : showSavedFeedback ? "Saved!" : "Save"}
        </button>
        <ExportPDFButton cvId={cvId} cvTitle={cv.title} onBeforeExport={onSave} />
        <PromoteToLibraryButton cvId={cvId} />
      </div>
    </header>
  );
}
