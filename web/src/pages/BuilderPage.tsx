import { useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useCVStore } from "../lib/store/cvStore";
import { updateCV } from "../lib/api/cvs";
import SectionList from "../components/sections/SectionList";
import TemplateSwitcher from "../components/preview/TemplateSwitcher";
import CustomizePanel from "../components/customization/CustomizePanel";
import type { SectionData } from "../lib/sections/types";

export default function BuilderPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentCV, loadCV, isLoading } = useCVStore();

  useEffect(() => {
    if (id) loadCV(id);
  }, [id, loadCV]);

  const sections = (currentCV?.sections || { order: [], enabled: [], data: {} }) as {
    order: string[];
    enabled: string[];
    data: SectionData;
  };
  const customizations = currentCV?.customizations || {};

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
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">{isLoading ? "Loading CV..." : "CV not found"}</p>
      </div>
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
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 capitalize">
            {currentCV.template_id.replace("generic-", "")}
          </span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex w-1/2 overflow-hidden">
          <div className="w-2/3 overflow-y-auto border-r bg-white p-4">
            <SectionList
              order={sections.order}
              enabled={sections.enabled}
              data={sections.data}
              onOrderChange={handleOrderChange}
              onToggle={handleToggle}
              onDataChange={handleDataChange}
            />
          </div>
          <div className="w-1/3 overflow-y-auto border-r bg-gray-50 p-4">
            <CustomizePanel customizations={customizations} onChange={handleCustomizationsChange} />
          </div>
        </div>

        <div className="w-1/2 overflow-y-auto bg-gray-100 p-6">
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
        </div>
      </div>
    </div>
  );
}
