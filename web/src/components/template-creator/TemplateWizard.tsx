import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowLeft, ArrowRight, Check, Loader2, X } from "lucide-react";
import StyleEditor from "../customization/StyleEditor";
import TemplateLayoutView from "./TemplateLayoutView";
import client from "../../lib/api/client";
import { useToastStore } from "../../lib/store/uiStore";
import type { Zone, AssetItem } from "../../lib/sections/types";

/* ── Asset Manager ─────────────────────────────────────────────── */

function generateAssetId(): string {
  return `ast_${Math.random().toString(36).slice(2, 10)}`;
}

interface AssetManagerProps {
  zones: Zone[];
  assetItems: AssetItem[];
  assetPlacement: Record<string, string>;
  onUpdate: (items: AssetItem[], placement: Record<string, string>, assets: Record<string, string>) => void;
}

function AssetManager({ zones, assetItems, assetPlacement, onUpdate }: AssetManagerProps) {
  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files || []).forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const id = generateAssetId();
        const data = reader.result as string;
        const item: AssetItem = { id, name: file.name, data, type: "image" };
        onUpdate(
          [...assetItems, item],
          { ...assetPlacement },
          { [file.name]: data },
        );
      };
      reader.readAsDataURL(file);
    });
  };

  const removeAsset = (id: string) => {
    const remaining = assetItems.filter((a) => a.id !== id);
    const { [id]: _, ...restPlacement } = assetPlacement;
    onUpdate(remaining, restPlacement, {});
  };

  const setPlacement = (assetId: string, zoneId: string) => {
    onUpdate(assetItems, { ...assetPlacement, [assetId]: zoneId }, {});
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-500">Upload images and place them in a zone.</p>
      <input type="file" multiple accept="image/*" onChange={handleUpload} className="block w-full text-sm text-gray-500 file:mr-2 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-blue-700 hover:file:bg-blue-100" />
      {assetItems.length > 0 && (
        <div className="space-y-2">
          {assetItems.map((asset) => (
            <div key={asset.id} className="flex items-center gap-3 rounded-lg border bg-white p-2">
              <img src={asset.data} alt={asset.name} className="h-10 w-10 flex-shrink-0 rounded object-cover" />
              <span className="min-w-0 flex-1 truncate text-xs text-gray-700">{asset.name}</span>
              <select
                value={assetPlacement[asset.id] || ""}
                onChange={(e) => setPlacement(asset.id, e.target.value)}
                className="rounded border px-2 py-1 text-xs"
              >
                <option value="">Not placed</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>{zone.label || zone.id}</option>
                ))}
              </select>
              <button onClick={() => removeAsset(asset.id)} className="flex-shrink-0 text-gray-300 hover:text-red-500">
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface WizardProps {
  initialManifest?: Record<string, any>;
  onSave?: (manifest: Record<string, any>) => void;
  onComplete?: () => void;
  onManifestChange?: (manifest: Record<string, any>) => void;
}

type StepId = "basics" | "layout" | "styles" | "assets" | "review";

const steps: { id: StepId; label: string; description: string }[] = [
  { id: "basics", label: "Basics", description: "Name and describe your template" },
  { id: "layout", label: "Layout", description: "Arrange zones and rows" },
  { id: "styles", label: "Styles", description: "Colors, fonts, spacing" },
  { id: "assets", label: "Assets", description: "Upload images and place them in zones" },
  { id: "review", label: "Review", description: "Preview and save" },
];

export default function TemplateWizard({ initialManifest = {}, onSave, onComplete, onManifestChange }: WizardProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [manifest, setManifest] = useState<Record<string, any>>({
    version: 1,
    name: initialManifest.name || "",
    description: initialManifest.description || "",
    zones: initialManifest.zones || [{ id: "main", row: 0, styles: { width: "100%", padding: "24px" } }],
    placement: initialManifest.placement || { profile: "main" },
    globalStyleSchema: initialManifest.globalStyleSchema || [],
    assets: initialManifest.assets || {},
    asset_items: initialManifest.asset_items || [],
    asset_placement: initialManifest.asset_placement || {},
    sectionSchema: initialManifest.sectionSchema || {},
    ...initialManifest,
  });
  const [saving, setSaving] = useState(false);

  const currentStep = steps[currentStepIndex];

  const updateManifest = useCallback((partial: Record<string, any>) => {
    setManifest((prev) => {
      const next = { ...prev, ...partial };
      onManifestChange?.(next);
      return next;
    });
  }, [onManifestChange]);

  const goNext = () => {
    if (currentStepIndex < steps.length - 1) setCurrentStepIndex((i) => i + 1);
  };

  const goPrev = () => {
    if (currentStepIndex > 0) setCurrentStepIndex((i) => i - 1);
  };

  const handleLayoutChange = (config: { zones: Zone[]; placement: Record<string, string> }) => {
    updateManifest({ zones: config.zones, placement: config.placement });
  };

  const handleStyleChange = (customizations: Record<string, any>) => {
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
    setManifest((prev) => {
      const next = { ...prev, globalStyleSchema: schema, default_customizations: customizations };
      onManifestChange?.(next);
      return next;
    });
  };

  const addToast = useToastStore((s) => s.addToast);

  const handleSave = async () => {
    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("manifest_json", JSON.stringify(manifest));
      
      const response = await client.post("/templates", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      
      addToast("Template saved", "success");
      onSave?.(response.data);
      onComplete?.();
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || (e as Error)?.message
        || "Failed to save template";
      addToast(detail, "error");
    } finally {
      setSaving(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep.id) {
      case "basics":
        return (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Template Name</label>
              <input
                type="text"
                value={manifest.name || ""}
                onChange={(e) => updateManifest({ name: e.target.value })}
                placeholder="My Template"
                className="w-full rounded border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-500">Description</label>
              <textarea
                value={manifest.description || ""}
                onChange={(e) => updateManifest({ description: e.target.value })}
                placeholder="Brief description of your template"
                rows={3}
                className="w-full rounded border px-3 py-2 text-sm"
              />
            </div>
          </div>
        );
      case "layout":
        return (
          <TemplateLayoutView
            zones={manifest.zones || []}
            placement={manifest.placement || {}}
            onChange={handleLayoutChange}
          />
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
          <AssetManager
            zones={manifest.zones || []}
            assetItems={manifest.asset_items || []}
            assetPlacement={manifest.asset_placement || {}}
            onUpdate={(assetItems, assetPlacement, assets) => {
              const next = {
                ...manifest,
                asset_items: assetItems,
                asset_placement: assetPlacement,
                assets: { ...manifest.assets, ...assets },
              };
              setManifest(next);
              onManifestChange?.(next);
            }}
          />
        );
      case "review":
        return (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">Your template is ready. Preview it live on the right, then save.</p>
            <div className="rounded-lg border bg-gray-50 p-3">
              <div className="mb-1 text-xs font-medium text-gray-500">Template Name</div>
              <div className="text-sm font-semibold">{manifest.name || "Untitled"}</div>
            </div>
            <div className="rounded-lg border bg-gray-50 p-3">
              <div className="mb-1 text-xs font-medium text-gray-500">Zones</div>
              <div className="text-sm">{(manifest.zones || []).length} zone(s) in {(manifest.zones || []).reduce((s: number[], z: Zone) => { const r = z.row ?? 0; if (!s.includes(r)) s.push(r); return s; }, []).length} row(s)</div>
            </div>
            <div className="rounded-lg border bg-gray-50 p-3">
              <div className="mb-1 text-xs font-medium text-gray-500">Assets</div>
              <div className="text-sm">{(manifest.asset_items || []).length} asset(s)</div>
            </div>
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