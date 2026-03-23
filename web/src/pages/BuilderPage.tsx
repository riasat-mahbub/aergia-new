import { useEffect, useCallback, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Palette } from "lucide-react";
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
import TemplateBrowser from "../components/template-browser/TemplateBrowser";
import type { SectionInstance } from "../lib/sections/types";
import { createDefaultInstance } from "../lib/sections/types";
import { updateCV } from "../lib/api/cvs";

export default function BuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading, isSaving, lastSaved, setIsSaving, setLastSaved } = useCVStore();
  const [showTemplateBrowser, setShowTemplateBrowser] = useState(false);
  const [activeTab, setActiveTab] = useState<"content" | "customize">("content");
  const [localInstances, setLocalInstances] = useState<SectionInstance[]>([]);
  const [localCustomizations, setLocalCustomizations] = useState<Record<string, unknown>>({});
  const loadedRef = useRef(false);
  const needsReloadRef = useRef(false);

  useEffect(() => {
    if (id) {
      loadedRef.current = false;
      loadCV(id);
    }
  }, [id, loadCV]);

  useEffect(() => {
    if (currentCV?.sections && !loadedRef.current) {
      setLocalInstances(currentCV.sections as SectionInstance[]);
      setLocalCustomizations(currentCV.customizations || {});
      loadedRef.current = true;
    }
  }, [currentCV]);

  const autoSaveData = {
    sections: localInstances,
    customizations: localCustomizations,
  };

  const handleAutoSaveComplete = useCallback(async () => {
    setLastSaved(new Date());
    needsReloadRef.current = true;
  }, [setLastSaved]);

  const { isSaving: hookSaving } = useAutoSave({
    cvId: id,
    data: autoSaveData as Record<string, unknown>,
    debounceMs: 3000,
    enabled: loadedRef.current && !!id,
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

  const instances = localInstances;
  const customizations = localCustomizations;
  const templateLabel = currentCV?.template_id?.replace("generic-", "") || "";

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleToggle = useCallback(
    (sectionId: string) => {
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, enabled: !i.enabled } : i)));
    },
    []
  );

  const handleUpdateData = useCallback(
    (sectionId: string, data: any) => {
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, data } : i)));
    },
    []
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const sectionIdx = instances.findIndex((i) => i.id === active.id);
      if (sectionIdx !== -1) {
        const oldIndex = instances.findIndex((i) => i.id === active.id);
        const newIndex = instances.findIndex((i) => i.id === over.id);
        setLocalInstances(arrayMove(instances, oldIndex, newIndex));
        return;
      }

      for (const instance of instances) {
        const entries = instance.data as any[];
        if (Array.isArray(entries)) {
          const entryIdx = entries.findIndex((e: any) => e.id === active.id);
          if (entryIdx !== -1) {
            const oldIndex = entries.findIndex((e: any) => e.id === active.id);
            const newIndex = entries.findIndex((e: any) => e.id === over.id);
            const reordered = arrayMove(entries, oldIndex, newIndex);
            handleUpdateData(instance.id, reordered);
            return;
          }
        }
      }
    },
    [instances, handleUpdateData]
  );

  const handleAddSection = useCallback(
    (type: string) => {
      const newInstance = createDefaultInstance(type);
      setLocalInstances((prev) => [...prev, newInstance]);
    },
    []
  );

  const handleRemoveInstance = useCallback(
    (sectionId: string) => {
      setLocalInstances((prev) => prev.filter((i) => i.id !== sectionId));
    },
    []
  );

  const handleRenameInstance = useCallback(
    (sectionId: string, title: string) => {
      setLocalInstances((prev) => prev.map((i) => (i.id === sectionId ? { ...i, title } : i)));
    },
    []
  );

  const handleTemplateChange = useCallback(
    async (newTemplateId: string) => {
      if (!id) return;
      try {
        setIsSaving(true);
        await updateCV(id, { template_id: newTemplateId, sections: localInstances, customizations: localCustomizations });
        await loadCV(id);
        setShowTemplateBrowser(false);
      } finally {
        setIsSaving(false);
      }
    },
    [id, localInstances, localCustomizations, loadCV, setIsSaving]
  );

  const handleCustomizationsChange = useCallback(
    (newCustomizations: Record<string, unknown>) => {
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
          <button onClick={() => navigate("/")} className="text-sm text-gray-500 hover:text-gray-700">
            &larr; Back
          </button>
          <h1 className="text-lg font-semibold text-gray-900">{currentCV.title}</h1>
          <button
            onClick={() => setShowTemplateBrowser(true)}
            className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 capitalize hover:bg-gray-200"
          >
            {templateLabel || "template"} &middot; Change
          </button>
          {isSaving && <span className="text-xs text-gray-400">Saving...</span>}
          {lastSaved && !isSaving && (
            <span className="text-xs text-gray-400">Saved</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {id && <ExportPDFButton cvId={id} cvTitle={currentCV.title} />}
          <button
            onClick={() => setActiveTab(activeTab === "customize" ? "content" : "customize")}
            className={`rounded p-1.5 transition-colors ${activeTab === "customize" ? "bg-blue-100 text-blue-600" : "text-gray-400 hover:text-gray-600"}`}
            title="Toggle customization panel"
          >
            <Palette className="h-4 w-4" />
          </button>
        </div>
      </header>

      <TemplateBrowser
        open={showTemplateBrowser}
        onClose={() => setShowTemplateBrowser(false)}
        currentTemplateId={currentCV.template_id}
        onSelect={handleTemplateChange}
      />

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
              <CustomizePanel customizations={customizations} onChange={handleCustomizationsChange} />
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
            />
          </div>
        </motion.div>
      </div>
    </div>
    </DndContext>
  );
}
