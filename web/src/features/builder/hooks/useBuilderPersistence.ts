import { useCallback, useEffect, useRef, useState } from "react";
import { updateCV } from "@/features/cvs";
import { useUnsavedChanges, type BuilderSaveData } from "./useUnsavedChanges";

interface UseBuilderPersistenceOptions {
  id: string;
  instances: BuilderSaveData["sections"];
  customizations: BuilderSaveData["customizations"];
  setIsSaving: (saving: boolean) => void;
  setLastSaved: (date: Date) => void;
  refreshApplicationAnalysis: () => Promise<void>;
}

export interface BuilderPersistence {
  hasUnsavedChanges: boolean;
  markDirty: () => void;
  markClean: () => void;
  handleSave: () => Promise<void>;
  instancesRef: React.MutableRefObject<BuilderSaveData["sections"]>;
  customizationsRef: React.MutableRefObject<BuilderSaveData["customizations"]>;
  showSavedFeedback: boolean;
}

/** Owns dirty tracking, pending-save serialization, and save feedback for one Builder document. */
export function useBuilderPersistence({
  id,
  instances,
  customizations,
  setIsSaving,
  setLastSaved,
  refreshApplicationAnalysis,
}: UseBuilderPersistenceOptions): BuilderPersistence {
  const [showSavedFeedback, setShowSavedFeedback] = useState(false);
  const pendingSaveRef = useRef<Promise<unknown> | null>(null);
  const instancesRef = useRef(instances);
  const customizationsRef = useRef(customizations);
  const instancesForUnloadRef = useRef<BuilderSaveData>({ sections: instances, customizations });
  const idRef = useRef(id);

  useEffect(() => {
    instancesRef.current = instances;
    instancesForUnloadRef.current.sections = instances;
  }, [instances]);
  useEffect(() => {
    customizationsRef.current = customizations;
    instancesForUnloadRef.current.customizations = customizations;
  }, [customizations]);
  useEffect(() => {
    idRef.current = id;
  }, [id]);

  const triggerSave = useCallback(
    async (saveData: BuilderSaveData) => {
      const cvId = idRef.current;
      if (!cvId) return;
      try {
        setIsSaving(true);
        const request = updateCV(cvId, saveData);
        pendingSaveRef.current = request;
        await request;
        await refreshApplicationAnalysis();
        setLastSaved(new Date());
      } finally {
        setIsSaving(false);
        pendingSaveRef.current = null;
      }
    },
    [refreshApplicationAnalysis, setIsSaving, setLastSaved],
  );

  const getPendingSaveData = useCallback(() => instancesForUnloadRef.current, []);
  const { hasUnsavedChanges, markDirty, markClean } = useUnsavedChanges({
    enabled: Boolean(id),
    resetKey: id,
    getPendingSaveData,
    save: triggerSave,
  });

  const handleSave = useCallback(async () => {
    const cvId = idRef.current;
    if (!cvId) return;
    try {
      setIsSaving(true);
      const request = updateCV(cvId, {
        sections: instancesRef.current,
        customizations: customizationsRef.current,
      });
      pendingSaveRef.current = request;
      await request;
      await refreshApplicationAnalysis();
      setLastSaved(new Date());
      markClean();
      setShowSavedFeedback(true);
      window.setTimeout(() => setShowSavedFeedback(false), 2000);
    } finally {
      setIsSaving(false);
      pendingSaveRef.current = null;
    }
  }, [markClean, refreshApplicationAnalysis, setIsSaving, setLastSaved]);

  return {
    hasUnsavedChanges,
    markDirty,
    markClean,
    handleSave,
    instancesRef,
    customizationsRef,
    showSavedFeedback,
  };
}
