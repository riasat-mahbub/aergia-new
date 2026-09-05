import { useEffect, useCallback, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "motion/react";

import ExportPDFButton from "./_components/ExportPDFButton";
import PromoteToLibraryButton from "./_components/PromoteToLibraryButton";
import RelevanceDrawer from "./_components/RelevanceDrawer";
import ContentSectionList from "./_components/ContentSectionList";
import { useCVStore } from "@/store/cvStore";
import { useSupportStore } from "./_stores/supportStore";
import UserTemplateRenderer from "./_components/preview/UserTemplateRenderer";
import Inspector from "./_components/customization/Inspector";
import type { SectionInstance, SectionInstanceStyle, LayoutConfig } from "@/lib/cv/types";
import { createDefaultInstance, getFirstZoneId, migratePlacement } from "@/lib/cv/types";
import { updateCV } from "@/services/cvs";
import * as templatesApi from "@/services/templates";
import type { UserTemplate } from "@/contracts/templates";
import { APPLICATION_RELEVANCE_TOOLTIP } from "./_lib/applicationRelevance";
import { sectionStyleHasValues } from "./_lib/sectionStyle";
import { useBuilderApplicationContext } from "./_hooks/useBuilderApplicationContext";
import { useUnsavedChanges, type BuilderSaveData } from "./_hooks/useUnsavedChanges";

export default function BuilderPage() {
  const location = useLocation();
  const id = location.pathname.split("/builder/")[1] || "";
  const applicationId = new URLSearchParams(location.search).get("application");
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading, isSaving, lastSaved, setIsSaving, setLastSaved } = useCVStore();

  const [showLoading, setShowLoading] = useState(true);
  const [localInstances, setLocalInstances] = useState<SectionInstance[]>([]);
  const [localCustomizations, setLocalCustomizations] = useState<Record<string, unknown>>({});
  const [templateManifest, setTemplateManifest] = useState<UserTemplate | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
  const [relevanceDrawerOpen, setRelevanceDrawerOpen] = useState(false);
  // Inspector replaces CustomizePanel as of Phase C of
  // FEAT-01M0X607K4MWVGGCVZWWMSKJHE.
  const [showSavedFeedback, setShowSavedFeedback] = useState(false);
  const pendingSaveRef = useRef<Promise<unknown> | null>(null);
  const {
    applicationContext,
    relevance,
    relevanceRefreshing,
    relevanceRefreshError,
    refreshApplicationRelevance,
  } = useBuilderApplicationContext({ applicationId, cvId: id });

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    // eslint-disable-next-line react-hooks/set-state-in-effect -- CV switch reset; see Phase 9 lint debt
    setLocalInstances([]);
    setLocalCustomizations({});
    setIsLoaded(false);

    (async () => {
      await loadCV(id);
      setShowLoading(false);
      if (cancelled) return;
      const state = useCVStore.getState();
      if (state.currentCV?.sections) {
        const instances = state.currentCV.sections as SectionInstance[];
        const customizations = state.currentCV.customizations || {};

        // Migrate old type-based placement to instance-based
        const layout = customizations.layout as LayoutConfig | undefined;
        if (layout && layout.placement) {
          customizations.layout = migratePlacement(layout, instances);
        }

        setLocalInstances(instances);
        setLocalCustomizations(customizations);
        setIsLoaded(true);
      }
    })();


    return () => { cancelled = true; };
  }, [id, loadCV]);
  useEffect(() => {
    useSupportStore.getState().ensureLoaded();
  }, []);

  const instances = localInstances;
  const customizations = localCustomizations;
  // Mirror state into refs inside effects so the latest values are
  // available to async handlers without re-running them every render.
  const instancesRef = useRef(instances);
  const idRef = useRef(id);
  const customizationsRef = useRef(customizations);
  const instancesForUnloadRef = useRef({ sections: localInstances, customizations: localCustomizations });
  useEffect(() => { instancesRef.current = instances; }, [instances]);
  useEffect(() => { idRef.current = id; }, [id]);
  useEffect(() => { customizationsRef.current = customizations; }, [customizations]);
  useEffect(() => {
    instancesForUnloadRef.current = { sections: localInstances, customizations: localCustomizations };
  }, [localInstances, localCustomizations]);
  useEffect(() => {
    if (!currentCV || !isLoaded) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- template fetch reset; see Phase 9 lint debt
    setTemplateManifest(null);

    (async () => {
      try {
        const template = await templatesApi.fetchTemplate(currentCV.template_id);
        setTemplateManifest(template ?? null);
      } catch {
        // Template fetch failed
      }
    })();
  }, [currentCV?.template_id, isLoaded, id]);

  const triggerSave = useCallback(
    async (saveData: BuilderSaveData) => {
      const cvId = idRef.current;
      if (!cvId) return;
      try {
        setIsSaving(true);
        const p = updateCV(cvId, saveData);
        pendingSaveRef.current = p;
        await p;
        await refreshApplicationRelevance();
        setLastSaved(new Date());
      } finally {
        setIsSaving(false);
        pendingSaveRef.current = null;
      }
    },
    [setIsSaving, setLastSaved, refreshApplicationRelevance]
  );

  const getPendingSaveData = useCallback(() => instancesForUnloadRef.current, []);
  const { hasUnsavedChanges, markDirty, markClean } = useUnsavedChanges({
    enabled: Boolean(id),
    getPendingSaveData,
    save: triggerSave,
  });

  const handleSave = useCallback(async () => {
    const cvId = idRef.current;
    const data = { sections: instancesRef.current, customizations: customizationsRef.current };
    if (!cvId) return;
    try {
      setIsSaving(true);
      const p = updateCV(cvId, data);
      pendingSaveRef.current = p;
      await p;
      await refreshApplicationRelevance();
      setLastSaved(new Date());
      markClean();
      setShowSavedFeedback(true);
      setTimeout(() => setShowSavedFeedback(false), 2000);
    } finally {
      setIsSaving(false);
      pendingSaveRef.current = null;
    }
  }, [setIsSaving, setLastSaved, setShowSavedFeedback, refreshApplicationRelevance, markClean]);

  const handleToggle = useCallback(
    (sectionId: string) => {
      markDirty();
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, enabled: !i.enabled } : i)));
    },
    [markDirty]
  );

  const handleUpdateData = useCallback(
    (sectionId: string, data: unknown) => {
      markDirty();
      // Empty list after last entry is removed → drop the section entirely.
      if (Array.isArray(data) && data.length === 0) {
        setLocalInstances((prev) => prev.filter((i) => i.id !== sectionId));
        return;
      }
      setLocalInstances((prev) =>
        prev.map((i) => (i.id === sectionId ? { ...i, data: data as SectionInstance["data"] } : i)),
      );
    },
    [markDirty]
  );
  const handleReorderInstances = useCallback(
    (newInstances: SectionInstance[]) => {
      markDirty();
      setLocalInstances(newInstances);
    },
    [markDirty]
  );

  const handleAddSection = useCallback(
    (type: string, zoneId?: string) => {
      markDirty();
      const newInstance = createDefaultInstance(type);
      setLocalInstances((prev) => [...prev, newInstance]);

      // Decide which zone receives the new section: caller-provided zone, or
      // the first zone of the effective layout. If no zones exist, leave the
      // section unassigned (no placement entry written).
      setLocalCustomizations((prev) => {
        const existingLayout = prev.layout as LayoutConfig | undefined;
        const hasValidLayout = existingLayout && existingLayout.zones?.length;
        const baseLayout: LayoutConfig = hasValidLayout
          ? existingLayout
          : { zones: [], placement: {} };
        const targetZoneId = zoneId ?? getFirstZoneId(baseLayout);
        if (!targetZoneId) return prev;
        return {
          ...prev,
          layout: { ...baseLayout, placement: { ...baseLayout.placement, [newInstance.id]: targetZoneId } },
        };
      });
    },
    [markDirty]
  );
  const handleRemoveInstance = useCallback(
    (sectionId: string) => {
      markDirty();
      setLocalInstances((prev) => prev.filter((i) => i.id !== sectionId));
    },
    [markDirty]
  );

  const handleRenameInstance = useCallback(
    (sectionId: string, title: string) => {
      markDirty();
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, title } : i)));
    },
    [markDirty]
  );

  const handleUpdateStyle = useCallback(
    (sectionId: string, style: SectionInstanceStyle) => {
      markDirty();
      // Persist the style object when any field (including an explicit
      // show_title or a per-field style) is set. The customize panel strips
      // the object entirely when nothing is set; this matches that intent.
      const hasValues = sectionStyleHasValues(style);
      setLocalInstances((prev) =>
        prev.map((i) =>
          i.id === sectionId ? { ...i, style: hasValues ? style : undefined } : i
        )
      );
    },
    [markDirty]
  );

  const handleUpdateCustomizations = useCallback(
    (next: Record<string, unknown>) => {
      markDirty();
      setLocalCustomizations(next);
    },
    [markDirty],
  );

  const handleReset = useCallback(() => {
    markDirty();
    setLocalCustomizations({});
    setLocalInstances((prev) => prev.map((i) => ({ ...i, style: undefined })));
  }, [markDirty]);
  const handleTemplateChange = useCallback(
    async (newTemplateId: string) => {
      if (!id) return;
      if (
        !window.confirm(
          "Switching templates installs the new template's zones and reassigns every section to the first zone. Per-section content (text, entries, order) is preserved. Continue?"
        )
      ) {
        return;
      }
      try {
        setIsSaving(true);
        // Defensive: drop every per-instance style so the new template's styles take effect.
        const cleanInstances = localInstances.map((i) => ({ ...i, style: undefined }));
        setLocalInstances(cleanInstances);

        let customizationsWithLayout: Record<string, unknown>;
        try {
          const template = await templatesApi.fetchTemplate(newTemplateId);
          const zones = template.manifest?.zones;
          const placement = template.manifest?.placement;
          if (Array.isArray(zones) && zones.length > 0 && placement) {
            // Install the new template's zones verbatim and reassign every section
            // to the first zone so the editor is never left with zero zones.
            const newLayout: LayoutConfig = { zones, placement: {} };
            const firstZoneId = getFirstZoneId(newLayout);
            for (const instance of cleanInstances) {
              if (firstZoneId) newLayout.placement[instance.id] = firstZoneId;
            }
            customizationsWithLayout = { ...localCustomizations, layout: newLayout };
          } else {
            customizationsWithLayout = {};
          }
        } catch {
          // Template fetch failed — fall back to the wipe-and-reload behavior
          // so the user is never stranded with a stale layout.
          customizationsWithLayout = {};
        }
        setLocalCustomizations(customizationsWithLayout);

        await updateCV(id, {
          template_id: newTemplateId,
          sections: cleanInstances,
          customizations: customizationsWithLayout,
        });
        await loadCV(id);
      } finally {
        setIsSaving(false);
      }
    },
    [id, localInstances, localCustomizations, loadCV, setIsSaving]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (hasUnsavedChanges) {
          handleSave();
        }
      }
    },
    [handleSave, hasUnsavedChanges]
  );

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
        <p className="text-app-ink-3">{isLoading ? "Loading CV..." : "CV not found"}</p>
      </motion.div>
    ) : currentCV ? (
      <div className="flex h-screen flex-col">
        <header className="flex items-center justify-between border-b bg-app-surface px-4 py-3">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate("/dashboard/cvs")} className="text-sm text-app-ink-3 hover:text-app-ink-2">
              &larr; Back
            </button>
            <h1 className="text-lg font-semibold text-app-ink">{currentCV!.title}</h1>
            {applicationContext && (
              <button
                type="button"
                onClick={() => setRelevanceDrawerOpen(true)}
                title={APPLICATION_RELEVANCE_TOOLTIP}
                aria-label="Open relevance details"
                className="rounded-full bg-app-primary-soft px-2.5 py-1 text-xs font-medium text-app-primary hover:bg-app-primary-soft"
              >
                Relevance {relevance ? `${relevance.score}%` : "—"}
              </button>
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
              onClick={handleSave}
              disabled={(!hasUnsavedChanges && !showSavedFeedback) || isSaving}
              className="rounded-md bg-app-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? "Saving..." : showSavedFeedback ? "Saved!" : "Save"}
            </button>

            {id && <ExportPDFButton cvId={id} cvTitle={currentCV!.title} onBeforeExport={handleSave} />}
            {id && <PromoteToLibraryButton cvId={id} />}
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden">
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="flex w-1/2 flex-col overflow-hidden border-r bg-app-surface"
          >
            <div className="flex border-b bg-app-canvas">
              <button
                onClick={() => setActiveTab("content")}
                className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === "content"
                    ? "border-b-2 border-app-primary bg-app-surface text-app-primary"
                    : "text-app-ink-3 hover:text-app-ink-2"
                }`}
              >
                Content
              </button>
              <button
                onClick={() => setActiveTab("customize")}
                className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === "customize"
                    ? "border-b-2 border-app-primary bg-app-surface text-app-primary"
                    : "text-app-ink-3 hover:text-app-ink-2"
                }`}
              >
                Customize
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {activeTab === "customize" && (
                <Inspector
                  templateId={currentCV!.template_id}
                  templateName={templateManifest?.name ?? ""}
                  instances={instances}
                  onUpdateStyle={handleUpdateStyle}
                  onCustomizationsChange={handleUpdateCustomizations}
                  onTemplateChange={() => handleTemplateChange(currentCV!.template_id)}
                  onReset={handleReset}
                  customizations={localCustomizations}
                />
              )}
              {activeTab === "content" && (
                <ContentSectionList
                  instances={instances}
                  cvId={id}
                  onToggle={handleToggle}
                  onUpdateData={handleUpdateData}
                  onAddSection={handleAddSection}
                  onRemoveInstance={handleRemoveInstance}
                  onRenameInstance={handleRenameInstance}
                  onReorderInstances={handleReorderInstances}
                />
              )}
            </div>
          </motion.div>
          <motion.div
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="w-1/2 overflow-y-auto bg-app-surface-muted p-6"
          >
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-app-ink-3">Preview</h2>
            <div className="w-full min-w-0">
              <UserTemplateRenderer
                instances={instances}
                customizations={customizations}
                manifest={templateManifest?.manifest ?? undefined}
              />
            </div>
          </motion.div>
        </div>
        <RelevanceDrawer
          open={relevanceDrawerOpen}
          relevance={relevance}
          refreshing={relevanceRefreshing}
          refreshError={relevanceRefreshError}
          onClose={() => setRelevanceDrawerOpen(false)}
        />
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
