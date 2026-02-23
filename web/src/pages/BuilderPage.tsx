import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Palette } from "lucide-react";
import { useCVStore } from "../lib/store/cvStore";
import { updateCV } from "../lib/api/cvs";
import SectionList from "../components/sections/SectionList";
import TemplateSwitcher from "../components/preview/TemplateSwitcher";
import CustomizePanel from "../components/customization/CustomizePanel";
import TemplateBrowser from "../components/template-browser/TemplateBrowser";
import type { SectionInstance } from "../lib/sections/types";
import { createDefaultInstance } from "../lib/sections/types";

export default function BuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading } = useCVStore();
  const [showTemplateBrowser, setShowTemplateBrowser] = useState(false);
  const [showCustomizePanel, setShowCustomizePanel] = useState(false);

  useEffect(() => {
    if (id) loadCV(id);
  }, [id, loadCV]);

  const instances = (currentCV?.sections as SectionInstance[]) || [];
  const customizations = currentCV?.customizations || {};

  const templateLabel = currentCV?.template_id?.replace("generic-", "") || "";

  const handleReorder = useCallback(
    async (ids: string[]) => {
      if (!id) return;
      const reordered = ids.map((itemId) => instances.find((i) => i.id === itemId)).filter(Boolean) as SectionInstance[];
      try {
        await updateCV(id, { sections: reordered });
        await loadCV(id);
      } catch {}
    },
    [id, instances, loadCV]
  );

  const handleToggle = useCallback(
    async (sectionId: string) => {
      if (!id) return;
      const updated = instances.map((i) =>
        i.id === sectionId ? { ...i, enabled: !i.enabled } : i
      );
      try {
        await updateCV(id, { sections: updated });
        await loadCV(id);
      } catch {}
    },
    [id, instances, loadCV]
  );

  const handleUpdateData = useCallback(
    async (sectionId: string, data: any) => {
      if (!id) return;
      const updated = instances.map((i) =>
        i.id === sectionId ? { ...i, data } : i
      );
      try {
        await updateCV(id, { sections: updated });
        await loadCV(id);
      } catch {}
    },
    [id, instances, loadCV]
  );

  const handleAddSection = useCallback(
    async (type: string) => {
      if (!id) return;
      const newInstance = createDefaultInstance(type);
      const updated = [...instances, newInstance];
      try {
        await updateCV(id, { sections: updated });
        await loadCV(id);
      } catch {}
    },
    [id, instances, loadCV]
  );

  const handleRemoveInstance = useCallback(
    async (sectionId: string) => {
      if (!id) return;
      const updated = instances.filter((i) => i.id !== sectionId);
      try {
        await updateCV(id, { sections: updated });
        await loadCV(id);
      } catch {}
    },
    [id, instances, loadCV]
  );

  const handleRenameInstance = useCallback(
    async (sectionId: string, title: string) => {
      if (!id) return;
      const updated = instances.map((i) =>
        i.id === sectionId ? { ...i, title } : i
      );
      try {
        await updateCV(id, { sections: updated });
        await loadCV(id);
      } catch {}
    },
    [id, instances, loadCV]
  );

  const handleTemplateChange = useCallback(
    async (newTemplateId: string) => {
      if (!id) return;
      await updateCV(id, { template_id: newTemplateId });
      await loadCV(id);
      setShowTemplateBrowser(false);
    },
    [id, loadCV]
  );

  const handleCustomizationsChange = useCallback(
    async (newCustomizations: Record<string, any>) => {
      if (!id) return;
      try {
        await updateCV(id, { customizations: newCustomizations });
        await loadCV(id);
      } catch {}
    },
    [id, loadCV]
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
        </div>
        <button
          onClick={() => setShowCustomizePanel((v) => !v)}
          className={`rounded p-1.5 transition-colors ${showCustomizePanel ? "bg-blue-100 text-blue-600" : "text-gray-400 hover:text-gray-600"}`}
          title="Toggle customization panel"
        >
          <Palette className="h-4 w-4" />
        </button>
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
              customizations={currentCV.customizations}
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}
