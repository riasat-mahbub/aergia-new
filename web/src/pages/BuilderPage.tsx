import { useEffect, useCallback, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Palette } from "lucide-react";
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
  const [showCustomizePanel, setShowCustomizePanel] = useState(false);
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

  const handleReorder = useCallback(
    (ids: string[]) => {
      const reordered = ids.map((itemId) => instances.find((i) => i.id === itemId)).filter(Boolean) as SectionInstance[];
      setLocalInstances(reordered);
    },
    [instances]
  );

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
            onClick={() => setShowCustomizePanel((v) => !v)}
            className={`rounded p-1.5 transition-colors ${showCustomizePanel ? "bg-blue-100 text-blue-600" : "text-gray-400 hover:text-gray-600"}`}
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
          className="flex w-1/2 overflow-hidden"
        >
          <div className={`overflow-y-auto border-r bg-white p-4 ${showCustomizePanel ? "w-2/3" : "w-full"}`}>
            <SectionList
              instances={instances}
              onReorder={handleReorder}
              onToggle={handleToggle}
              onUpdateData={handleUpdateData}
              onAddSection={handleAddSection}
              onRemoveInstance={handleRemoveInstance}
              onRenameInstance={handleRenameInstance}
            />
          </div>
          {showCustomizePanel && (
            <div className="w-1/3 overflow-y-auto border-r bg-gray-50 p-4">
              <CustomizePanel customizations={customizations} onChange={handleCustomizationsChange} />
            </div>
          )}
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
  );
}
