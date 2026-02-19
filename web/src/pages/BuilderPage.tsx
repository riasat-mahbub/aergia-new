import { useEffect, useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { useCVStore } from "../lib/store/cvStore";
import { updateCV } from "../lib/api/cvs";
import SectionList from "../components/sections/SectionList";
import TemplateSwitcher from "../components/preview/TemplateSwitcher";
import CustomizePanel from "../components/customization/CustomizePanel";
import TemplateBrowser from "../components/template-browser/TemplateBrowser";
import type { SectionData } from "../lib/sections/types";

export default function BuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading } = useCVStore();
  const [showTemplateBrowser, setShowTemplateBrowser] = useState(false);

  useEffect(() => {
    if (id) loadCV(id);
  }, [id, loadCV]);

  const sections = (currentCV?.sections || { order: [], enabled: [], data: {} }) as {
    order: string[];
    enabled: string[];
    data: SectionData;
  };
  const customizations = currentCV?.customizations || {};

  const templateLabel = currentCV?.template_id?.replace("generic-", "") || "";

  const handleOrderChange = useCallback(
    async (order: string[]) => {
      if (!id) return;
      try {
        await updateCV(id, { sections: { ...sections, order } });
        await loadCV(id);
      } catch {}
    },
    [id, sections, loadCV]
  );

  const handleToggle = useCallback(
    async (sectionType: string) => {
      if (!id) return;
      const enabled = sections.enabled.includes(sectionType)
        ? sections.enabled.filter((s: string) => s !== sectionType)
        : [...sections.enabled, sectionType];
      try {
        await updateCV(id, { sections: { ...sections, enabled } });
        await loadCV(id);
      } catch {}
    },
    [id, sections, loadCV]
  );

  const handleDataChange = useCallback(
    async (data: SectionData) => {
      if (!id) return;
      try {
        await updateCV(id, { sections: { ...sections, data } });
        await loadCV(id);
      } catch {}
    },
    [id, sections, loadCV]
  );

  const handleAddSection = useCallback(
    async (sectionType: string) => {
      if (!id) return;
      const newOrder = [...sections.order, sectionType];
      const newEnabled = [...sections.enabled, sectionType];
      await updateCV(id, { sections: { ...sections, order: newOrder, enabled: newEnabled } });
      await loadCV(id);
    },
    [id, sections, loadCV]
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
          <div className="w-2/3 overflow-y-auto border-r bg-white p-4">
            <SectionList
              order={sections.order}
              enabled={sections.enabled}
              data={sections.data}
              onOrderChange={handleOrderChange}
              onToggle={handleToggle}
              onDataChange={handleDataChange}
              onAddSection={handleAddSection}
            />
          </div>
          <div className="w-1/3 overflow-y-auto border-r bg-gray-50 p-4">
            <CustomizePanel customizations={customizations} onChange={handleCustomizationsChange} />
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
              sections={sections.data}
              order={sections.order}
              enabled={sections.enabled}
              customizations={currentCV.customizations}
            />
          </div>
        </motion.div>
      </div>
    </div>
  );
}
