import { useState, useCallback, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { Save, ArrowLeft, Loader2, Upload } from "lucide-react";
import type { UserTemplate } from "../lib/api/templates";
import type { LayoutConfig } from "../lib/sections/types";
import { fetchSystemTemplates, uploadUserTemplate, fetchTemplate } from "../lib/api/templates";
import { layoutConfigToHTML } from "../lib/sections/templateHtml";
import { sampleInstances } from "../lib/sections/sampleData";
import BaseTemplateCard from "../components/template-creator/BaseTemplateCard";
import TemplateCustomizePanel from "../components/template-creator/TemplateCustomizePanel";
import TemplateSwitcher from "../components/preview/TemplateSwitcher";

type Mode = "picker" | "editor";
type EditorTab = "design" | "html";

interface EditorState {
  baseTemplateId: string;
  layoutConfig: LayoutConfig;
  customizations: Record<string, any>;
  templateName: string;
}

const DEFAULT_CUSTOMIZATIONS = {
  colors: { accent: "#2563eb", bg_sidebar: "#f8fafc", header: "#000000", divider: "#d1d5db", text: "#374151", heading: "#111827" },
  fonts: { body: "Inter, system-ui, sans-serif", heading: "Inter, system-ui, sans-serif" },
  spacing: { section_gap: "24px" },
};

export default function TemplateCreatorPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("picker");
  const [systemTemplates, setSystemTemplates] = useState<UserTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [editor, setEditor] = useState<EditorState>({
    baseTemplateId: "",
    layoutConfig: { zones: [], placement: {} },
    customizations: DEFAULT_CUSTOMIZATIONS,
    templateName: "",
  });

  // Editor tabs & HTML state
  const [activeTab, setActiveTab] = useState<EditorTab>("design");
  const [htmlContent, setHtmlContent] = useState("");

  // Load system templates on mount
  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const templates = await fetchSystemTemplates();
        setSystemTemplates(templates);
      } catch {
        // If fetch fails, use empty list — user can still proceed with defaults
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);

  const handleSelectBase = useCallback(async (templateId: string) => {
    try {
      const detail = await fetchTemplate(templateId);
      const layoutConfig = (detail.layout_config || { zones: [], placement: {} }) as LayoutConfig;
      const customizations = detail.default_customizations || DEFAULT_CUSTOMIZATIONS;
      const name = `My ${detail.name}`;

      setEditor({
        baseTemplateId: templateId,
        layoutConfig,
        customizations,
        templateName: name,
      });
      setHtmlContent(layoutConfigToHTML(layoutConfig));
      setActiveTab("design");
      setMode("editor");
    } catch {
      // Fallback to list data if fetchTemplate fails
      const tpl = systemTemplates.find((t) => t.id === templateId);
      if (!tpl) return;

      const layoutConfig = (tpl.layout_config || { zones: [], placement: {} }) as LayoutConfig;
      const customizations = tpl.default_customizations || DEFAULT_CUSTOMIZATIONS;
      const name = `My ${tpl.name}`;

      setEditor({
        baseTemplateId: templateId,
        layoutConfig,
        customizations,
        templateName: name,
      });
      setHtmlContent(layoutConfigToHTML(layoutConfig));
      setActiveTab("design");
      setMode("editor");
    }
  }, [systemTemplates]);

  const handleBackToPicker = useCallback(() => {
    setMode("picker");
    setSaveError(null);
  }, []);

  const handleLayoutConfigChange = useCallback((config: LayoutConfig) => {
    setEditor((prev) => ({ ...prev, layoutConfig: config }));
    // Sync HTML when switching to HTML tab later
    setHtmlContent(layoutConfigToHTML(config));
  }, []);

  const handleCustomizationsChange = useCallback((customizations: Record<string, any>) => {
    setEditor((prev) => ({ ...prev, customizations }));
  }, []);

  const handleNameChange = useCallback((name: string) => {
    setEditor((prev) => ({ ...prev, templateName: name }));
  }, []);

  // Sync HTML content when switching to HTML tab from Design
  useEffect(() => {
    if (activeTab === "html" && !htmlContent.trim()) {
      setHtmlContent(layoutConfigToHTML(editor.layoutConfig));
    }
  }, [activeTab, editor.layoutConfig, htmlContent]);

  const handleImportFile = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      if (content) {
        setHtmlContent(content);
        setActiveTab("html");
      }
    };
    reader.readAsText(file);

    // Reset file input so same file can be selected again
    if (event.target) {
      event.target.value = "";
    }
  }, []);

  const handleSave = useCallback(async () => {
    if (!editor.templateName.trim()) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      const layoutTemplate = htmlContent || layoutConfigToHTML(editor.layoutConfig);
      await uploadUserTemplate({
        name: editor.templateName.trim(),
        layout_template: layoutTemplate,
        layout_config: editor.layoutConfig as unknown as Record<string, unknown>,
        default_customizations: editor.customizations,
      });
      navigate("/dashboard");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Failed to save template");
    } finally {
      setIsSaving(false);
    }
  }, [editor.templateName, editor.layoutConfig, editor.customizations, htmlContent, navigate]);

  // Generate a simple template ID for preview
  const previewTemplateId = useMemo(() => {
    if (!editor.baseTemplateId) return "generic-modern";
    return editor.baseTemplateId;
  }, [editor.baseTemplateId]);

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
          /* ─── Picker Mode ───────────────────────────────────── */
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
          /* ─── Editor Mode ───────────────────────────────────── */
          <motion.div
            key="editor"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {/* Top bar */}
            <div className="mb-4 flex items-center justify-between rounded-lg border bg-white px-4 py-3 shadow-sm">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleBackToPicker}
                  className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Change Base
                </button>
                <div className="h-5 w-px bg-gray-200" />
                <input
                  type="text"
                  value={editor.templateName}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="Template name"
                  className="max-w-xs rounded border-none bg-transparent text-sm font-semibold text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={handleSave}
                disabled={!editor.templateName.trim() || isSaving}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save Template
              </button>
            </div>

            {/* Error */}
            {saveError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {saveError}
              </div>
            )}

            {/* Tab bar */}
            <div className="mb-4 flex gap-1 rounded-lg border bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setActiveTab("design")}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeTab === "design"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                }`}
              >
                Design
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("html")}
                className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeTab === "html"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                }`}
              >
                HTML
              </button>
            </div>

            {/* Tab content */}
            <AnimatePresence mode="wait">
              {activeTab === "design" ? (
                <motion.div
                  key="design"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  transition={{ duration: 0.15 }}
                  className="flex h-[calc(100vh-12rem)] gap-4 overflow-hidden"
                >
                  {/* Left: Customize */}
                  <div className="w-5/12 overflow-y-auto rounded-lg border bg-white shadow-sm">
                    <div className="p-4">
                      <TemplateCustomizePanel
                        layoutConfig={editor.layoutConfig}
                        onLayoutConfigChange={handleLayoutConfigChange}
                        customizations={editor.customizations}
                        onCustomizationsChange={handleCustomizationsChange}
                      />
                    </div>
                  </div>

                  {/* Right: Preview */}
                  <div className="w-7/12 overflow-y-auto rounded-lg bg-gray-100 p-6">
                    <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Preview</h2>
                    <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
                      <TemplateSwitcher
                        templateId={previewTemplateId}
                        instances={sampleInstances as unknown as typeof sampleInstances}
                        customizations={editor.customizations}
                        layoutConfig={editor.layoutConfig}
                        defaultCustomizations={editor.customizations}
                      />
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="html"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.15 }}
                  className="flex h-[calc(100vh-12rem)] gap-4 overflow-hidden"
                >
                  {/* Left: HTML editor */}
                  <div className="w-5/12 flex flex-col gap-3 overflow-hidden rounded-lg border bg-white shadow-sm">
                    <div className="flex items-center justify-between border-b px-3 py-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Layout Template</span>
                      <label className="cursor-pointer rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">
                        <div className="flex items-center gap-1">
                          <Upload className="h-3 w-3" />
                          Import HTML
                        </div>
                        <input
                          type="file"
                          accept=".html,.htm"
                          onChange={handleImportFile}
                          className="hidden"
                        />
                      </label>
                    </div>
                    <textarea
                      value={htmlContent}
                      onChange={(e) => setHtmlContent(e.target.value)}
                      className="flex-1 resize-none border-t bg-gray-50 p-3 font-mono text-xs leading-relaxed focus:outline-none"
                      spellCheck={false}
                    />
                  </div>

                  {/* Right: Preview */}
                  <div className="w-7/12 overflow-y-auto rounded-lg bg-gray-100 p-6">
                    <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">Preview</h2>
                    <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
                      <TemplateSwitcher
                        templateId={previewTemplateId}
                        instances={sampleInstances as unknown as typeof sampleInstances}
                        customizations={editor.customizations}
                        layoutConfig={editor.layoutConfig}
                        defaultCustomizations={editor.customizations}
                      />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
