import { useEffect, useLayoutEffect, useCallback, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { motion } from "motion/react";

import BuilderHeader from "./components/BuilderHeader";
import BuilderWorkspace from "./components/BuilderWorkspace";
import { ScannerAnalysisDrawer } from "@/features/applications";
import type { ScannerAnalysisContext } from "@/features/applications";
import { fetchCV } from "@/features/cvs";
import type { CVDetail } from "@/features/cvs";
import { useBuilderDocumentStore } from "./state/builderDocumentStore";
import { useSupportStore } from "./state/supportStore";
import type { SectionInstance, SectionInstanceStyle } from "@/shared/cv/schema";
import { useBuilderDocumentLoader } from "./hooks/useBuilderDocumentLoader";
import { useBuilderPersistence } from "./hooks/useBuilderPersistence";
import { useTemplateManifest } from "./hooks/useTemplateManifest";
import {
  addSection,
  removeInstance,
  renameInstance,
  resetDocument,
  toggleInstance,
  updateInstanceData,
  updateInstanceStyle,
} from "./domain/documentCommands";
import { useBuilderApplicationContext } from "./hooks/useBuilderApplicationContext";
import { reevaluateTailoringDraft } from "@/features/tailoring";

interface PageActionResource {
  key: string;
  generation: number;
  mounted: boolean;
  draftActionInFlight: boolean;
}

interface DraftActionState {
  resourceKey: string;
  working: boolean;
  error: string | null;
}

function httpStatus(error: unknown): number | null {
  if (!error || typeof error !== "object") return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === "number" ? response.status : null;
}

function errorMessage(error: unknown): string | null {
  if (!error || typeof error !== "object") return null;
  const message = (error as { message?: unknown }).message;
  return typeof message === "string" ? message : null;
}

export interface BuilderPageProps {
  cvId: string;
  applicationId: string | null;
}

export default function BuilderPage({ cvId, applicationId }: BuilderPageProps) {
  const id = cvId;
  const resourceKey = `${id}:${applicationId ?? ""}`;
  const navigate = useNavigate();
  const pageActionResourceRef = useRef<PageActionResource>({ key: "", generation: 0, mounted: false, draftActionInFlight: false });
  const [draftActionState, setDraftActionState] = useState<DraftActionState>({
    resourceKey: "",
    working: false,
    error: null,
  });
  const draftActionCurrent = draftActionState.resourceKey === resourceKey
    ? draftActionState
    : { resourceKey, working: false, error: null };

  useLayoutEffect(() => {
    const generation = pageActionResourceRef.current.generation + 1;
    pageActionResourceRef.current = { key: resourceKey, generation, mounted: true, draftActionInFlight: false };
    // Reset route-local progress on A → B → A so an older request cannot leave the reopened resource disabled.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- route-scoped action state is external to the new resource
    setDraftActionState({ resourceKey, working: false, error: null });
    return () => {
      if (pageActionResourceRef.current.generation === generation) {
        pageActionResourceRef.current = { key: resourceKey, generation: generation + 1, mounted: false, draftActionInFlight: false };
      }
    };
  }, [resourceKey]);

  const { currentCV, loadCV, isLoading, isSaving, lastSaved, setIsSaving, setLastSaved } = useBuilderDocumentStore();
  const documentError = useBuilderDocumentStore((state) => state.error);

  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
  const [scannerDrawerOpen, setScannerDrawerOpen] = useState(false);
  // Inspector replaces CustomizePanel as of Phase C of
  // FEAT-01M0X607K4MWVGGCVZWWMSKJHE.
  const {
    applicationContext,
    pendingDraftContext,
    pendingDraftApplicationId,
    pendingDraftUnavailable,
    applicationContextError,
    draftContextRefreshFailed,
    scannerRefreshing,
    scannerRefreshError,
    refreshApplicationAnalysis,
    runScanner,
    applyPendingDraftReview,
  } = useBuilderApplicationContext({ applicationId, cvId: id });
  const {
    instances,
    customizations,
    setInstances,
    setCustomizations,
    isLoaded,
    showLoading,
    retry,
  } = useBuilderDocumentLoader({ id, loadCV });
  const syncBuilderDraft = useCallback((cv: CVDetail) => {
    setInstances(cv.sections);
    setCustomizations(cv.customizations);
  }, [setCustomizations, setInstances]);
  useEffect(() => {
    useSupportStore.getState().ensureLoaded();
  }, []);

  const { templateManifest, handleTemplateChange } = useTemplateManifest({
    id,
    templateId: currentCV?.template_id,
    isLoaded,
    instances,
    customizations,
    setInstances,
    setCustomizations,
    setIsSaving,
    loadCV,
  });
  const {
    hasUnsavedChanges,
    markDirty,
    handleSave,
    saveForTailoringReview,
    syncSavedDocument,
    instancesRef,
    customizationsRef,
    showSavedFeedback,
    saveError,
  } = useBuilderPersistence({
    id,
    instances,
    customizations,
    ready: isLoaded && currentCV?.id === id,
    syncBuilderDraft,
    setIsSaving,
    setLastSaved,
    refreshApplicationAnalysis,
  });
  const draftReview = pendingDraftContext?.draft_review;
  const pendingDraftScannerContext: ScannerAnalysisContext | null = pendingDraftContext ? {
    company: pendingDraftContext.job.company,
    role: pendingDraftContext.job.role,
    cv_id: pendingDraftContext.draft_cv_id,
    scanner_result: draftReview?.scanner_result ?? null,
    scanner_status: draftReview?.scanner_result
      ? (hasUnsavedChanges || isSaving || Boolean(saveError) || draftActionCurrent.working || Boolean(draftActionCurrent.error) || draftContextRefreshFailed || draftReview.state !== "current" || currentCV?.id !== id || draftReview.cv_revision !== currentCV.revision ? "stale" : "current")
      : "not_scanned",
  } : null;

  const reevaluateDraft = useCallback(async () => {
    const active = pageActionResourceRef.current;
    const generation = active.generation;
    const isCurrentAction = () => {
      const current = pageActionResourceRef.current;
      return current.mounted && current.key === resourceKey && current.generation === generation;
    };
    const draft = pendingDraftContext;
    if (!isCurrentAction() || active.draftActionInFlight || !draft || draft.draft_cv_id !== id) return;

    active.draftActionInFlight = true;
    try {
      setDraftActionState({ resourceKey, working: true, error: null });
      try {
        const savedRevision = await saveForTailoringReview(id);
        if (!isCurrentAction()) return;

        const response = await reevaluateTailoringDraft(draft.session_id, {
          expected_cv_revision: savedRevision.revision,
        });
        if (!isCurrentAction()) return;
        if (
          response.session_id !== draft.session_id
          || response.application_id !== draft.application_id
          || response.draft_cv_id !== id
        ) {
          throw new Error("The draft review response did not match the draft being edited.");
        }
        const reviewedRevision = response.draft_review.cv_revision;
        if (
          response.draft_review.state !== "current"
          || typeof reviewedRevision !== "number"
          || !Number.isInteger(reviewedRevision)
          || reviewedRevision < savedRevision.revision
        ) {
          throw new Error("The saved draft changed during review. Save the latest edits and try again.");
        }
        const reviewedCv = await fetchCV(id);
        if (!isCurrentAction()) return;
        if (reviewedCv.id !== id || reviewedCv.revision !== reviewedRevision) {
          throw new Error("The saved draft changed after review. Save the latest edits and try again.");
        }
        if (!syncSavedDocument(reviewedCv, savedRevision.token, reviewedRevision)) {
          throw new Error("The CV changed while the review was finishing. Save the latest edits and try again.");
        }
        if (!applyPendingDraftReview(response)) {
          throw new Error("The draft review is no longer available. Return to the application review and reopen the draft.");
        }
      } catch (error) {
        if (!isCurrentAction()) return;
        try {
          await refreshApplicationAnalysis();
        } catch {
          // The context hook records deleted or unavailable drafts in its own state.
        }
        if (!isCurrentAction()) return;
        const message = httpStatus(error) === 404
          ? "This tailoring draft is no longer available. Return to the application review to discard it or start again."
          : errorMessage(error) ?? "The draft could not be saved and reevaluated. Save successfully, then retry.";
        setDraftActionState({ resourceKey, working: false, error: message });
        throw error;
      }

      if (isCurrentAction()) setDraftActionState({ resourceKey, working: false, error: null });
    } finally {
      if (pageActionResourceRef.current === active) active.draftActionInFlight = false;
    }
  }, [applyPendingDraftReview, id, pendingDraftContext, refreshApplicationAnalysis, resourceKey, saveForTailoringReview, syncSavedDocument]);

  const retryDraftContextRefresh = useCallback(async () => {
    await refreshApplicationAnalysis();
  }, [refreshApplicationAnalysis]);

  const handleExplicitSave = useCallback(async () => {
    const activeResource = pageActionResourceRef.current;
    await handleSave();
    if (pageActionResourceRef.current !== activeResource) return;
    setDraftActionState((current) => current.resourceKey !== resourceKey || !current.error
      ? current
      : { ...current, error: null });
  }, [handleSave, resourceKey]);

  const handleToggle = useCallback(
    (sectionId: string) => {
      markDirty();
      setInstances((prev) => toggleInstance(prev, sectionId));
    },
    [markDirty, setInstances]
  );

  const handleUpdateData = useCallback(
    (sectionId: string, data: unknown) => {
      markDirty();
      // Empty list after last entry is removed → drop the section entirely.
      setInstances((prev) => updateInstanceData(prev, sectionId, data));
    },
    [markDirty, setInstances]
  );
  const handleReorderInstances = useCallback(
    (newInstances: SectionInstance[]) => {
      markDirty();
      setInstances(newInstances);
    },
    [markDirty, setInstances]
  );

  const handleAddSection = useCallback(
    (type: string, zoneId?: string) => {
      markDirty();
      const currentInstances = instancesRef.current;
      const currentCustomizations = customizationsRef.current;
      const next = addSection(currentInstances, currentCustomizations, type, zoneId);
      setInstances(next.instances);
      setCustomizations(next.customizations);
    },
    [customizationsRef, instancesRef, markDirty, setCustomizations, setInstances]
  );
  const handleRemoveInstance = useCallback(
    (sectionId: string) => {
      markDirty();
      setInstances((prev) => removeInstance(prev, sectionId));
    },
    [markDirty, setInstances]
  );

  const handleRenameInstance = useCallback(
    (sectionId: string, title: string) => {
      markDirty();
      setInstances((prev) => renameInstance(prev, sectionId, title));
    },
    [markDirty, setInstances]
  );

  const handleUpdateStyle = useCallback(
    (sectionId: string, style: SectionInstanceStyle) => {
      markDirty();
      // Persist the style object when any field (including an explicit
      // show_title or a per-field style) is set. The customize panel strips
      // the object entirely when nothing is set; this matches that intent.
      setInstances((prev) => updateInstanceStyle(prev, sectionId, style));
    },
    [markDirty, setInstances]
  );

  const handleReset = useCallback(() => {
    markDirty();
    // The Customize tab resets section styles only. Keep the zone placement
    // authored in the content/layout model intact.
    setCustomizations((previous) => previous.layout ? { layout: previous.layout } : {});
    setInstances((prev) => resetDocument(prev));
  }, [markDirty, setCustomizations, setInstances]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (hasUnsavedChanges) {
          void handleExplicitSave().catch(() => {});
        }
      }
    },
    [handleExplicitSave, hasUnsavedChanges]
  );

  const handleBack = useCallback(() => {
    const targetApplicationId = pendingDraftContext?.application_id ?? pendingDraftApplicationId ?? applicationId;
    if (targetApplicationId) {
      navigate({ to: "/applications/$id", params: { id: targetApplicationId } });
      return;
    }
    navigate({ to: "/cvs" });
  }, [applicationId, navigate, pendingDraftApplicationId, pendingDraftContext]);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const formatLastSaved = useCallback((date: Date) => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 60) return "just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  }, []);
  return (
    <>
    {showLoading ? (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-screen items-center justify-center"
      >
        <p className="text-app-ink-3">{isLoading || !isLoaded ? "Loading CV..." : "CV not found"}</p>
      </motion.div>
    ) : documentError ? (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-screen items-center justify-center"
      >
        <div className="text-center" role="alert">
          <p className="text-app-danger">{documentError}</p>
          <button type="button" onClick={retry} className="mt-3 rounded-md border border-app-rule-strong px-3 py-1.5 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted">
            Try again
          </button>
        </div>
      </motion.div>
    ) : currentCV ? (
      <div className="flex h-screen flex-col">
        <BuilderHeader
          cv={currentCV}
          cvId={id}
          applicationContext={applicationContext}
          pendingDraftScannerContext={pendingDraftScannerContext}
          pendingDraftContext={pendingDraftContext}
          pendingDraftUnavailable={pendingDraftUnavailable}
          applicationContextError={applicationContextError}
          draftContextRefreshFailed={draftContextRefreshFailed}
          hasUnsavedChanges={hasUnsavedChanges}
          isSaving={isSaving}
          lastSaved={lastSaved}
          showSavedFeedback={showSavedFeedback}
          onBack={handleBack}
          onOpenScanner={() => setScannerDrawerOpen(true)}
          onSave={handleExplicitSave}
          onReevaluateDraft={reevaluateDraft}
          onRefreshDraftContext={retryDraftContextRefresh}
          reevaluatingDraft={draftActionCurrent.working}
          reevaluateDraftError={draftActionCurrent.error}
          canReevaluateDraft={Boolean(
            isLoaded
            && currentCV?.id === id
            && pendingDraftContext
            && pendingDraftContext.draft_review.cv_revision !== null
            && !draftContextRefreshFailed
          )}
          saveError={saveError}
          formatLastSaved={formatLastSaved}
        />
        <BuilderWorkspace
          cv={currentCV}
          cvId={id}
          instances={instances}
          customizations={customizations}
          templateManifest={templateManifest}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onToggle={handleToggle}
          onUpdateData={handleUpdateData}
          onAddSection={handleAddSection}
          onRemoveInstance={handleRemoveInstance}
          onRenameInstance={handleRenameInstance}
          onReorderInstances={handleReorderInstances}
          onUpdateStyle={handleUpdateStyle}
          onTemplateChange={() => handleTemplateChange(currentCV.template_id)}
          onReset={handleReset}
        />
        {(pendingDraftScannerContext || applicationContext) && <ScannerAnalysisDrawer
          open={scannerDrawerOpen}
          application={pendingDraftScannerContext ?? applicationContext!}
          onClose={() => setScannerDrawerOpen(false)}
          onScan={pendingDraftContext ? reevaluateDraft : runScanner}
          scanning={pendingDraftContext ? isSaving || draftActionCurrent.working : scannerRefreshing}
          scanError={pendingDraftContext
            ? draftActionCurrent.error
            : scannerRefreshError ? "We couldn’t complete the analysis. Please try again." : null}
          scanActionLabel={pendingDraftContext ? "Save and reevaluate draft" : undefined}
        />}
      </div>
    ) : (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-screen items-center justify-center"
      >
        <p className="text-app-ink-3">CV not found</p>
      </motion.div>
    )}
    </>
  );
}
