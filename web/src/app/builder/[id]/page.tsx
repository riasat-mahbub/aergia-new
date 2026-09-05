import { useEffect, useCallback, useState } from "react";
import { useNavigate, useParams, useSearch } from "@tanstack/react-router";
import { motion } from "motion/react";

import BuilderHeader from "./_components/BuilderHeader";
import BuilderWorkspace from "./_components/BuilderWorkspace";
import RelevanceDrawer from "./_components/RelevanceDrawer";
import { useBuilderDocumentStore } from "./_stores/builderDocumentStore";
import { useSupportStore } from "./_stores/supportStore";
import type { SectionInstance, SectionInstanceStyle } from "@/lib/cv/schema";
import { useBuilderDocumentLoader } from "./_hooks/useBuilderDocumentLoader";
import { useBuilderPersistence } from "./_hooks/useBuilderPersistence";
import { useTemplateManifest } from "./_hooks/useTemplateManifest";
import {
  addSection,
  removeInstance,
  renameInstance,
  resetDocument,
  toggleInstance,
  updateInstanceData,
  updateInstanceStyle,
} from "./_lib/documentCommands";
import { useBuilderApplicationContext } from "./_hooks/useBuilderApplicationContext";

export default function BuilderPage() {
  const { id = "" } = useParams({ from: "/_authenticated/builder/$id" });
  const { application: applicationId = null } = useSearch({ from: "/_authenticated/builder/$id" });
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading, isSaving, lastSaved, setIsSaving, setLastSaved } = useBuilderDocumentStore();

  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
  const [relevanceDrawerOpen, setRelevanceDrawerOpen] = useState(false);
  // Inspector replaces CustomizePanel as of Phase C of
  // FEAT-01M0X607K4MWVGGCVZWWMSKJHE.
  const {
    applicationContext,
    relevance,
    relevanceRefreshing,
    relevanceRefreshError,
    refreshApplicationRelevance,
  } = useBuilderApplicationContext({ applicationId, cvId: id });

  const {
    instances,
    customizations,
    setInstances,
    setCustomizations,
    isLoaded,
    showLoading,
  } = useBuilderDocumentLoader({ id, loadCV });
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
    instancesRef,
    customizationsRef,
    showSavedFeedback,
  } = useBuilderPersistence({
    id,
    instances,
    customizations,
    setIsSaving,
    setLastSaved,
    refreshApplicationRelevance,
  });

  const handleToggle = useCallback(
    (sectionId: string) => {
      markDirty();
      setInstances((prev) => toggleInstance(prev, sectionId));
    },
    [markDirty]
  );

  const handleUpdateData = useCallback(
    (sectionId: string, data: unknown) => {
      markDirty();
      // Empty list after last entry is removed → drop the section entirely.
      setInstances((prev) => updateInstanceData(prev, sectionId, data));
    },
    [markDirty]
  );
  const handleReorderInstances = useCallback(
    (newInstances: SectionInstance[]) => {
      markDirty();
      setInstances(newInstances);
    },
    [markDirty]
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
    [markDirty]
  );
  const handleRemoveInstance = useCallback(
    (sectionId: string) => {
      markDirty();
      setInstances((prev) => removeInstance(prev, sectionId));
    },
    [markDirty]
  );

  const handleRenameInstance = useCallback(
    (sectionId: string, title: string) => {
      markDirty();
      setInstances((prev) => renameInstance(prev, sectionId, title));
    },
    [markDirty]
  );

  const handleUpdateStyle = useCallback(
    (sectionId: string, style: SectionInstanceStyle) => {
      markDirty();
      // Persist the style object when any field (including an explicit
      // show_title or a per-field style) is set. The customize panel strips
      // the object entirely when nothing is set; this matches that intent.
      setInstances((prev) => updateInstanceStyle(prev, sectionId, style));
    },
    [markDirty]
  );

  const handleUpdateCustomizations = useCallback(
    (next: Record<string, unknown>) => {
      markDirty();
      setCustomizations(next);
    },
    [markDirty],
  );

  const handleReset = useCallback(() => {
    markDirty();
    setCustomizations({});
    setInstances((prev) => resetDocument(prev));
  }, [markDirty]);

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
        <BuilderHeader
          cv={currentCV}
          cvId={id}
          applicationContext={applicationContext}
          relevance={relevance}
          hasUnsavedChanges={hasUnsavedChanges}
          isSaving={isSaving}
          lastSaved={lastSaved}
          showSavedFeedback={showSavedFeedback}
          onBack={() => navigate({ to: "/dashboard/cvs" })}
          onOpenRelevance={() => setRelevanceDrawerOpen(true)}
          onSave={handleSave}
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
          onCustomizationsChange={handleUpdateCustomizations}
          onTemplateChange={() => handleTemplateChange(currentCV.template_id)}
          onReset={handleReset}
        />
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
