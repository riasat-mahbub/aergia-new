import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, ArrowRight, Check, Loader2 } from "lucide-react";
import ZoneLayoutBar from "../customization/ZoneLayoutBar";
import StyleEditor from "../customization/StyleEditor";
import client from "../../lib/api/client";
import type { LayoutConfig } from "../../lib/sections/types";

interface WizardProps {
  initialManifest?: Record<string, any>;
  onSave?: (manifest: Record<string, any>) => void;
}

type StepId = "layout" | "styles" | "assets" | "review";

const steps: { id: StepId; label: string; description: string }[] = [
  { id: "layout", label: "Layout", description: "Arrange zones and rows" },
  { id: "styles", label: "Styles", description: "Colors, fonts, spacing" },
  { id: "assets", label: "Assets", description: "Fonts, images (optional)" },
  { id: "review", label: "Review", description: "Preview and save" },
];

export default function TemplateWizard({ initialManifest = {}, onSave }: WizardProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [manifest, setManifest] = useState<Record<string, any>>({
    version: 1,
    name: initialManifest.name || "",
    description: initialManifest.description || "",
    zones: initialManifest.zones || [{ id: "main", row: 0, styles: { width: "100%", padding: "24px" } }],
    placement: initialManifest.placement || { profile: "main" },
    globalStyleSchema: initialManifest.globalStyleSchema || [],
    assets: initialManifest.assets || {},
    sectionSchema: initialManifest.sectionSchema || {},
    ...initialManifest,
  });
  const [saving, setSaving] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string>("");

  const currentStep = steps[currentStepIndex];

  const updateManifest = useCallback((partial: Record<string, any>) => {
    setManifest((prev) => ({ ...prev, ...partial }));
  }, []);

  const goNext = () => {
    if (currentStepIndex < steps.length - 1) setCurrentStepIndex((i) => i + 1);
  };

  const goPrev = () => {
    if (currentStepIndex > 0) setCurrentStepIndex((i) => i - 1);
  };

  const handleLayoutChange = (config: LayoutConfig) => {
    updateManifest({ zones: config.zones, placement: config.placement, rowHeights: config.rowHeights });
  };

  const handleStyleChange = (customizations: Record<string, any>) => {
    // Build globalStyleSchema from customizations
    const schema: any[] = [];
    const colors = customizations.colors || {};
    const fonts = customizations.fonts || {};
    const spacing = customizations.spacing || {};
    Object.entries(colors).forEach(([key, value]) => {
      schema.push({ key, type: "color", label: key, default: value });
    });
    Object.entries(fonts).forEach(([key, value]) => {
      schema.push({ key, type: "font", label: key, default: value });
    });
    Object.entries(spacing).forEach(([key, value]) => {
      schema.push({ key, type: "length", label: key, default: value });
    });
    setManifest((prev) => ({
      ...prev,
      globalStyleSchema: schema,
      default_customizations: customizations,
    }));
  };

  const generatePreview = async () => {
    try {
      const response = await client.post("/api/v1/render/html", {
        manifest: {
          zones: manifest.zones,
          placement: manifest.placement,
          globalStyleSchema: manifest.globalStyleSchema,
          default_customizations: manifest.default_customizations,
        },
        cv_data: { instances: [] },
        customizations: manifest.default_customizations || {},
      });
      setPreviewHtml(response.data.html);
    } catch (e) {
      console.error("Preview generation failed", e);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("manifest_json", JSON.stringify(manifest));
      
      const response = await client.post("/templates", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      
      onSave?.(response.data);
    } catch (e) {
      console.error("Save failed", e);
    } finally {
      setSaving(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep.id) {
      case "layout":
        return (
          <ZoneLayoutBar layoutConfig={{ zones: manifest.zones, placement: manifest.placement, rowHeights: manifest.rowHeights }} onChange={handleLayoutChange} />
        );
      case "styles":
        return (
          <StyleEditor
            customizations={manifest.default_customizations || {}}
            onChange={handleStyleChange}
            title="Global Styles"
          />
        );
      case "assets":
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">Drag and drop fonts or images (optional).</p>
            {/* simple file input for assets */}
            <input type="file" multiple onChange={(e) => {
              Array.from(e.target.files || []).forEach((file) => {
                const reader = new FileReader();
                reader.onload = () => {
                  setManifest((prev) => ({
                    ...prev,
                    assets: { ...prev.assets, [file.name]: reader.result },
                  }));
                };
                reader.readAsDataURL(file);
              });
            }} />
          </div>
        );
      case "review":
        return (
          <div className="space-y-4">
            <button onClick={generatePreview} disabled={saving} className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
              {saving ? <Loader2 className="h-4 w-4 animate-spin inline mr-1" /> : "Generate Preview"}
            </button>
            {previewHtml && (
              <div className="mx-auto max-w-[210mm] rounded bg-white shadow-sm">
                <iframe
                  srcDoc={previewHtml}
                  className="h-[297mm] w-full"
                  sandbox="allow-scripts allow-same-origin"
                />
              </div>
            )}
            <button onClick={handleSave} disabled={saving} className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700">
              {saving ? <Loader2 className="h-4 w-4 animate-spin inline mr-1" /> : "Save Template"}
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Stepper header */}
      <div className="mb-6 flex items-center justify-between border-b pb-4">
        {steps.map((step, idx) => (
          <div key={step.id} className="flex flex-col items-center relative">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors ${
                idx < currentStepIndex
                  ? "bg-emerald-600 text-white"
                  : idx === currentStepIndex
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-600"
              }`}
            >
              {idx < currentStepIndex ? <Check className="h-4 w-4" /> : idx + 1}
            </div>
            <p className="mt-1 text-xs text-center text-gray-500">{step.label}</p>
            {idx < steps.length - 1 && (
              <div className={`absolute top-4 left-full w-full h-0.5 ${idx < currentStepIndex ? "bg-emerald-600" : "bg-gray-200"}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          <h3 className="mb-2 text-lg font-semibold">{currentStep.label}</h3>
          <p className="mb-4 text-sm text-gray-500">{currentStep.description}</p>
          {renderStepContent()}
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="mt-6 flex justify-between border-t pt-4">
        <button
          onClick={goPrev}
          disabled={currentStepIndex === 0}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50"
        >
          <ArrowLeft className="inline h-4 w-4 mr-1" /> Back
        </button>
        {currentStepIndex === steps.length - 1 ? (
          <button onClick={handleSave} disabled={saving} className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin inline mr-1" /> : "Save Template"}
          </button>
        ) : (
          <button onClick={goNext} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Next <ArrowRight className="inline h-4 w-4 ml-1" />
          </button>
        )}
      </div>
    </div>
  );
}