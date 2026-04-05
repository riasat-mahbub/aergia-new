import { useEffect, useCallback, useState, useRef, useMemo } from "react";
import { useParams, useNavigate, useBlocker } from "react-router-dom";
import { motion } from "motion/react";

import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";
import ExportPDFButton from "../components/builder/ExportPDFButton";
import { useCVStore } from "../lib/store/cvStore";
import { useAutoSave } from "../hooks/useAutoSave";
import SectionList from "../components/sections/SectionList";
import TemplateSwitcher from "../components/preview/TemplateSwitcher";
import CustomizePanel from "../components/customization/CustomizePanel";

import type { SectionInstance, SectionStyle } from "../lib/sections/types";
import { createDefaultInstance } from "../lib/sections/types";
import { updateCV } from "../lib/api/cvs";
import { fetchTemplate } from "../lib/api/templates";

export default function BuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading, isSaving, lastSaved, setIsSaving, setLastSaved } = useCVStore();
  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
  const [localInstances, setLocalInstances] = useState<SectionInstance[]>([]);
  const [localCustomizations, setLocalCustomizations] = useState<Record<string, unknown>>({});
  const loadedRef = useRef(false);
  const needsReloadRef = useRef(false);
  const hasChangesRef = useRef(false);
  const pendingSaveRef = useRef<Promise<unknown> | null>(null);

  const isPending = useCallback(() => pendingSaveRef.current != null, []);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;

    setLocalInstances([]);
    setLocalCustomizations({});
    loadedRef.current = false;

    (async () => {
      await loadCV(id);
      if (cancelled) return;
      const state = useCVStore.getState();
      if (state.currentCV?.sections) {
        setLocalInstances(state.currentCV.sections as SectionInstance[]);
        setLocalCustomizations(state.currentCV.customizations || {});
        loadedRef.current = true;
      }
    })();

    return () => { cancelled = true; };
  }, [id, loadCV]);

  const instances = localInstances;
  const customizations = localCustomizations;
  const instancesRef = useRef(instances);
  instancesRef.current = instances;
  const idRef = useRef(id);
  idRef.current = id;
  const customizationsRef = useRef(customizations);
  customizationsRef.current = customizations;
  const instancesForUnloadRef = useRef({ sections: localInstances, customizations: localCustomizations });
  instancesForUnloadRef.current = { sections: localInstances, customizations: localCustomizations };
  const templateContentRef = useRef<string | null>(null);

  useEffect(() => {
    if (currentCV.template_id.startsWith("user_")) {
      fetchTemplate(currentCV.template_id)
        .then(setTemplateContent)
        .catch(() => {});
    }
  }, [currentCV.template_id]);

  const setTemplateContent = (content: string | null) => {
    templateContentRef.current = content;
  };

  const triggerSave = useCallback(
    async (saveData: { sections: SectionInstance[]; customizations: Record<string, unknown> }) => {
      const cvId = idRef.current;
      if (!cvId) return;
      try {
        setIsSaving(true);
        const p = updateCV(cvId, saveData);
        pendingSaveRef.current = p;
        await p;
        setLastSaved(new Date());
        hasChangesRef.current = false;
      } finally {
        setIsSaving(false);
        pendingSaveRef.current = null;
      }
    },
    [setIsSaving, setLastSaved]
  );

  const autoSaveDataRef = useRef({ sections: localInstances, customizations: localCustomizations });
  const stableAutoSaveData = useMemo(() => {
    const next = { sections: localInstances, customizations: localCustomizations };
    if (JSON.stringify(next) !== JSON.stringify(autoSaveDataRef.current)) {
      autoSaveDataRef.current = next;
    }
    return autoSaveDataRef.current;
  }, [localInstances, localCustomizations]);

  const handleAutoSaveComplete = useCallback(() => {
    setLastSaved(new Date());
    needsReloadRef.current = true;
  }, [setLastSaved]);

  const { isSaving: hookSaving } = useAutoSave({
    cvId: id,
    data: stableAutoSaveData as Record<string, unknown>,
    debounceMs: 3000,
    enabled: loadedRef.current && !!id,
    onSaveComplete: handleAutoSaveComplete,
    isPending,
  });

  useEffect(() => {
    setIsSaving(hookSaving);
  }, [hookSaving, setIsSaving]);

  useEffect(() => {
    if (needsReloadRef.current && !isSaving && id) {
      needsReloadRef.current = false;
      loadCV(id);
    }
  }, [isSaving, id, loadCV]);

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasChangesRef.current &&
      currentLocation.pathname !== nextLocation.pathname &&
      id != null
  );

  useEffect(() => {
    if (blocker.state !== "blocked") return;
    (async () => {
      try {
        await triggerSave(instancesForUnloadRef.current);
      } finally {
        blocker.proceed();
      }
    })();
  }, [blocker.state, triggerSave]);

  useEffect(() => {
    if (!hasChangesRef.current) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleToggle = useCallback(
    (sectionId: string) => {
      hasChangesRef.current = true;
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, enabled: !i.enabled } : i)));
    },
    []
  );

  const handleUpdateData = useCallback(
    (sectionId: string, data: any) => {
      hasChangesRef.current = true;
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, data } : i)));
    },
    []
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const currentInstances = instancesRef.current;
      let updatedInstances: SectionInstance[] | null = null;

      const sectionIdx = currentInstances.findIndex((i) => i.id === active.id);
      if (sectionIdx !== -1) {
        const oldIndex = currentInstances.findIndex((i) => i.id === active.id);
        const newIndex = currentInstances.findIndex((i) => i.id === over.id);
        updatedInstances = arrayMove(currentInstances, oldIndex, newIndex);
        setLocalInstances(updatedInstances);
      } else {
        for (const instance of currentInstances) {
          const entries = instance.data as any[];
          if (Array.isArray(entries)) {
            const entryIdx = entries.findIndex((e: any) => e.id === active.id);
            if (entryIdx !== -1) {
              const oldIndex = entries.findIndex((e: any) => e.id === active.id);
              const newIndex = entries.findIndex((e: any) => e.id === over.id);
              const reordered = arrayMove(entries, oldIndex, newIndex);
              updatedInstances = currentInstances.map((i) =>
                i.id === instance.id ? { ...i, data: reordered } : i
              );
              setLocalInstances(updatedInstances);
              break;
            }
          }
        }
      }

      if (updatedInstances) {
        triggerSave({ sections: updatedInstances, customizations: customizationsRef.current });
      }
    },
    [triggerSave]
  );

  const handleAddSection = useCallback(
    (type: string) => {
      hasChangesRef.current = true;
      const newInstance = createDefaultInstance(type);
      setLocalInstances((prev) => [...prev, newInstance]);
    },
    []
  );

  const handleRemoveInstance = useCallback(
    (sectionId: string) => {
      hasChangesRef.current = true;
      setLocalInstances((prev) => prev.filter((i) => i.id !== sectionId));
    },
    []
  );

  const handleRenameInstance = useCallback(
    (sectionId: string, title: string) => {
      hasChangesRef.current = true;
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, title } : i)));
    },
    []
  );

  const handleUpdateStyle = useCallback(
    (sectionId: string, style: SectionStyle) => {
      hasChangesRef.current = true;
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, style: style.font || style.color || style.weight ? style : undefined } : i)));
    },
    []
  );

  const handleTemplateChange = useCallback(
    async (newTemplateId: string) => {
      if (!id) return;
      try {
        setIsSaving(true);
        const cleanInstances = localInstances.map((i) => ({ ...i, style: undefined }));
        setLocalInstances(cleanInstances);
        
        let templateContent = null;
        if (newTemplateId.startsWith("user_")) {
          templateContent = await fetchTemplate(newTemplateId);
        }
        
        await updateCV(id, { template_id: newTemplateId, sections: cleanInstances, customizations: localCustomizations });
        await loadCV(id);
      } finally {
        setIsSaving(false);
      }
    },
    [id, localInstances, localCustomizations, loadCV, setIsSaving]
  );

  const handleCustomizationsChange = useCallback(
    (newCustomizations: Record<string, unknown>) => {
      hasChangesRef.current = true;
      setLocalCustomizations(newCustomizations);
    },
    []
  );

  if (isLoading || !currentCV) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex h-screen items-center justify-center"
      >
        <p className="text-gray-500">{isLoading ? "Loading CV..." : "CV not found"}</p>
      </motion.div>
    );
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b bg-white px-4 py-3">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/dashboard")} className="text-sm text-gray-500 hover:text-gray-700">
            &larr; Back
          </button>
          <h1 className="text-lg font-semibold text-gray-900">{currentCV.title}</h1>
          {isSaving && <span className="text-xs text-gray-400">Saving...</span>}
          {lastSaved && !isSaving && (
            <span className="text-xs text-gray-400">Saved</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {id && <ExportPDFButton cvId={id} cvTitle={currentCV.title} />}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <motion.div
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="flex w-1/2 flex-col overflow-hidden border-r bg-white"
        >
          <div className="flex border-b bg-gray-50">
            <button
              onClick={() => setActiveTab("content")}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === "content"
                  ? "border-b-2 border-blue-600 bg-white text-blue-700"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Content
            </button>
            <button
              onClick={() => setActiveTab("customize")}
              className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === "customize"
                  ? "border-b-2 border-blue-600 bg-white text-blue-700"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Customize
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === "content" && (
              <SectionList
                instances={instances}
                onToggle={handleToggle}
                onUpdateData={handleUpdateData}
                onAddSection={handleAddSection}
                onRemoveInstance={handleRemoveInstance}
                onRenameInstance={handleRenameInstance}
              />
            )}
            {activeTab === "customize" && (
              <CustomizePanel
                customizations={customizations}
                onChange={handleCustomizationsChange}
                templateId={currentCV.template_id}
                onTemplateChange={handleTemplateChange}
                instances={instances}
                onUpdateStyle={handleUpdateStyle}
              />
            )}
          </div>
        </motion.div>

        <motion.div
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="w-1/2 overflow-y-auto bg-gray-100 p-6"
        >
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Preview</h2>
          <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
            <TemplateSwitcher
              templateId={currentCV.template_id}
              instances={instances}
              customizations={customizations}
              templateContent={templateContentRef.current}
            />
          </div>
        </motion.div>
      </div>
    </div>
    </DndContext>
  );
}
