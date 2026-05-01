import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Loader2 } from "lucide-react";
import type { UserTemplate } from "../lib/api/templates";
import { fetchSystemTemplates, fetchTemplate } from "../lib/api/templates";
import { sampleInstances } from "../lib/sections/sampleData";
import BaseTemplateCard from "../components/template-creator/BaseTemplateCard";
import TemplateSwitcher from "../components/preview/TemplateSwitcher";
import TemplateWizard from "../components/template-creator/TemplateWizard";

type Mode = "picker" | "editor";

export default function TemplateCreatorPage() {
  const [mode, setMode] = useState<Mode>("picker");
  const [systemTemplates, setSystemTemplates] = useState<UserTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedManifest, setSelectedManifest] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const templates = await fetchSystemTemplates();
        setSystemTemplates(templates);
      } catch {
        // If fetch fails, fetch fails, use empty list — user can still proceed with defaults
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  const handleSelectBase = useCallback(async (templateId: string) => {
    try {
      const detail = await fetchTemplate(templateId);
      setSelectedManifest(detail.manifest || {});
      setMode("editor");
    } catch {
      const tpl = systemTemplates.find((t) => t.id === templateId);
      if (tpl?.manifest) {
        setSelectedManifest(tpl.manifest);
        setMode("editor");
      }
    }
  }, [systemTemplates]);

const handleBackToPicker = useCallback(() => {
    setMode("picker");
    setSelectedManifest(null);
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <AnimatePresence mode="wait">
        {mode === "picker" ? (
          <motion.div
            key="picker"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="mb-8 flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Template Creator</h1>
                <p className="mt-1 text-sm text-gray-500">Choose a base template to start customizing your own.</p>
              </div>
            </div>

            <motion.div layout className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {systemTemplates.map((template) => (
                <BaseTemplateCard key={template.id} template={template} onSelect={handleSelectBase} />
              ))}
            </motion.div>
          </motion.div>
        ) : (
          <motion.div
            key="editor"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="mb-4 flex items-center justify-between rounded-lg border bg-white px-4 py-3 shadow-sm">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleBackToPicker}
                  className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
                >
                  <span className="h-4 w-4" />
                  Change Base
                </button>
              </div>
            </div>

            <div className="flex h-[calc(100vh-10rem)]">
              {/* Left: Wizard */}
              <div className="w-5/12 overflow-y-auto rounded-lg border bg-white shadow-sm p-4">
                <TemplateWizard
                  initialManifest={selectedManifest || undefined}
                  onSave={(manifest) => console.log("Template saved:", manifest)}
                />
              </div>

              {/* Right: Preview */}
              <div className="w-7/12 overflow-y-auto rounded-lg bg-gray-100 p-6">
                <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Preview</h2>
                <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
                  <TemplateSwitcher
                    templateId="wizard"
                    instances={sampleInstances as unknown as typeof sampleInstances}
                    customizations={selectedManifest?.default_customizations || {}}
                    layoutConfig={selectedManifest ? { zones: selectedManifest.zones, placement: selectedManifest.placement } : undefined}
                    defaultCustomizations={selectedManifest?.default_customizations || {}}
                    manifest={selectedManifest || undefined}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}