import type { CVDetail } from "@/features/cvs";
import { ScannerJobFitBadge } from "@/features/applications";
import type { Application, ScannerAnalysisContext } from "@/features/applications";
import type { TailoringDraftContextResponse } from "@/features/tailoring";
import ExportPDFButton from "./ExportPDFButton";
import PromoteToLibraryButton from "./PromoteToLibraryButton";

interface BuilderHeaderProps {
  cv: CVDetail;
  cvId: string;
  applicationContext: Application | null;
  pendingDraftScannerContext: ScannerAnalysisContext | null;
  pendingDraftContext: TailoringDraftContextResponse | null;
  pendingDraftUnavailable: boolean;
  applicationContextError: string | null;
  draftContextRefreshFailed: boolean;
  hasUnsavedChanges: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  showSavedFeedback: boolean;
  onBack: () => void;
  onOpenScanner: () => void;
  onSave: () => Promise<void>;
  onReevaluateDraft: () => Promise<void>;
  onRefreshDraftContext: () => Promise<void>;
  reevaluatingDraft: boolean;
  reevaluateDraftError: string | null;
  canReevaluateDraft: boolean;
  saveError: string | null;
  formatLastSaved: (date: Date) => string;
}

export default function BuilderHeader({
  cv,
  cvId,
  applicationContext,
  pendingDraftScannerContext,
  pendingDraftContext,
  pendingDraftUnavailable,
  applicationContextError,
  draftContextRefreshFailed,
  hasUnsavedChanges,
  isSaving,
  lastSaved,
  showSavedFeedback,
  onBack,
  onOpenScanner,
  onSave,
  onReevaluateDraft,
  onRefreshDraftContext,
  reevaluatingDraft,
  reevaluateDraftError,
  canReevaluateDraft,
  saveError,
  formatLastSaved,
}: BuilderHeaderProps) {
  const draftReview = pendingDraftContext?.draft_review;
  const draftReviewIsStale = Boolean(draftReview && (
    hasUnsavedChanges
    || isSaving
    || Boolean(saveError)
    || reevaluatingDraft
    || Boolean(reevaluateDraftError)
    || draftContextRefreshFailed
    || draftReview.state !== "current"
    || draftReview.cv_revision !== cv.revision
  ));
  const showReevaluateButton = Boolean(draftReview && (draftReviewIsStale || draftContextRefreshFailed));

  return (
    <>
      <header className="flex flex-col gap-3 border-b bg-app-surface px-3 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-4">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
          <button onClick={onBack} className="shrink-0 text-sm text-app-ink-3 hover:text-app-ink-2">
            &larr; Back
          </button>
          <h1 className="min-w-0 flex-[1_1_12rem] break-words text-lg font-semibold text-app-ink">{cv.title}</h1>
          {applicationContext && (
            <span className="shrink-0">
              <ScannerJobFitBadge application={applicationContext} onClick={onOpenScanner} />
            </span>
          )}
          {pendingDraftScannerContext && (
            <span className="shrink-0">
              <ScannerJobFitBadge application={pendingDraftScannerContext} onClick={onOpenScanner} />
            </span>
          )}
          {draftReview && (
            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${draftReviewIsStale
                ? "border-app-warning/40 bg-app-warning-soft text-app-warning"
                : "border-app-primary/30 bg-app-primary-soft text-app-primary"}`}
              role="status"
            >
              {draftReviewIsStale ? "Draft review needs an update" : "Draft review current"}
            </span>
          )}
        </div>
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-x-3 gap-y-2 sm:justify-end sm:gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            {hasUnsavedChanges && (
              <>
                <span className="h-2 w-2 shrink-0 rounded-full bg-app-warning" aria-label="Unsaved changes" />
                <span className="text-sm text-app-warning">Unsaved</span>
              </>
            )}
            {lastSaved && !isSaving && !showSavedFeedback && (
              <span className="text-xs text-app-ink-3">Saved {formatLastSaved(lastSaved)}</span>
            )}
          </div>
          <div className="ml-auto flex shrink-0 items-center gap-2 sm:ml-0 sm:gap-3">
            <button
              type="button"
              onClick={() => { void onSave().catch(() => {}); }}
              disabled={(!hasUnsavedChanges && !showSavedFeedback && !saveError) || isSaving}
              className="rounded-md bg-app-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? "Saving..." : showSavedFeedback ? "Saved!" : "Save"}
            </button>
            <ExportPDFButton cvId={cvId} cvTitle={cv.title} onBeforeExport={onSave} />
            <PromoteToLibraryButton cvId={cvId} />
          </div>
        </div>
      </header>
      {saveError && <p className="border-b border-app-rule bg-app-canvas px-4 py-2 text-sm text-app-danger" role="alert">{saveError}</p>}
      {(pendingDraftContext || pendingDraftUnavailable || applicationContextError) && (
        <section className="border-b border-app-rule bg-app-canvas px-4 py-3" aria-label="Tailoring draft review">
          {pendingDraftContext && draftReview ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-sm font-semibold text-app-ink">
                  Tailored draft for {pendingDraftContext.job.role} at {pendingDraftContext.job.company}
                </h2>
                <p className="mt-1 text-xs text-app-ink-2" role="status">
                  {reevaluatingDraft
                    ? "The saved draft is being reevaluated. Its review is not current yet."
                    : isSaving
                      ? "Saving draft edits. The saved review will need reevaluation."
                      : draftContextRefreshFailed
                        ? "The current saved review could not be confirmed."
                        : hasUnsavedChanges
                    ? "Unsaved edits. The current review applies to the previously saved draft."
                    : draftReview.state === "current" && draftReview.cv_revision === cv.revision
                      ? "Review current for saved draft."
                      : draftReview.state === "needs_reevaluation" || draftReview.state === "current"
                        ? "This saved draft needs reevaluation."
                        : "A current review is unavailable for this saved draft."}
                </p>
                {draftReview.fit_review_applicability === "earlier_version" && (
                  <p className="mt-1 text-xs text-app-ink-3">Fit feedback is for an earlier version.</p>
                )}
                {draftContextRefreshFailed && (
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-app-warning" role="alert">
                    <span>The saved draft review could not be refreshed.</span>
                    <button
                      type="button"
                      onClick={() => { void onRefreshDraftContext().catch(() => {}); }}
                      disabled={isSaving || reevaluatingDraft}
                      className="font-semibold underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Retry status refresh
                    </button>
                  </div>
                )}
                {reevaluateDraftError && <p className="mt-1 text-xs text-app-danger" role="alert">{reevaluateDraftError}</p>}
              </div>
              {showReevaluateButton && (
                <button
                  type="button"
                  onClick={() => { void onReevaluateDraft().catch(() => {}); }}
                  disabled={!canReevaluateDraft || isSaving || reevaluatingDraft || draftContextRefreshFailed}
                  className="rounded-md border border-app-primary px-3 py-1.5 text-sm font-medium text-app-primary transition-colors hover:bg-app-primary-soft disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {reevaluatingDraft
                    ? "Saving and reevaluating…"
                    : hasUnsavedChanges
                      ? "Save and reevaluate draft"
                      : "Reevaluate saved draft"}
                </button>
              )}
            </div>
          ) : pendingDraftUnavailable ? (
            <p className="text-sm text-app-danger" role="alert">This tailoring draft is no longer available. Return to the application review to discard it or start again.</p>
          ) : applicationContextError ? (
            <p className="text-sm text-app-danger" role="alert">{applicationContextError}</p>
          ) : null}
        </section>
      )}
    </>
  );
}
