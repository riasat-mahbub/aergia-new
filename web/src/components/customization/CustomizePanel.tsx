import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import type { SectionInstance, SectionStyle, LayoutConfig, FieldStyle } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import { getFieldDefs } from "../../lib/sections/fieldStyles";
import TemplateSelectorModal from "./TemplateSelectorModal";
import StyleEditor, { type StyleVarSchema } from "./StyleEditor";
import SectionZoneView from "../layout/SectionZoneView";
interface Props {
  customizations: Record<string, any>;
  onChange: (customizations: Record<string, any>) => void;
  templateId: string;
  onTemplateChange: (templateId: string) => void;
  instances: SectionInstance[];
  onUpdateStyle: (id: string, style: SectionStyle) => void;
  layoutConfig: LayoutConfig;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  assets?: Record<string, string>;

  globalStyleSchema?: StyleVarSchema[];
}

const FONT_OPTIONS = [
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

const WEIGHT_OPTIONS = [
  { label: "Normal", value: "400" },
  { label: "Medium", value: "500" },
  { label: "Semibold", value: "600" },
  { label: "Bold", value: "700" },
];

const SIZE_OPTIONS = [
  "0.625rem", "0.75rem", "0.875rem", "1rem", "1.125rem", "1.25rem",
  "1.5rem", "1.75rem", "2rem", "2.25rem", "2.5rem", "3rem",
];

function FieldStyleRow({ label, value, onChange }: { label: string; value: FieldStyle; onChange: (next: FieldStyle) => void }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-700">{label}</span>
        {(value.font || value.size || value.weight) && (
          <button type="button" onClick={() => onChange({})} className="text-[10px] text-blue-600 hover:underline">
            Reset
          </button>
        )}
      </div>
      <div className="grid grid-cols-3 gap-1">
        <select value={value.font || ""} onChange={(e) => onChange({ ...value, font: e.target.value || undefined })} className="rounded border px-1 py-1 text-xs">
          <option value="">Font</option>
          {FONT_OPTIONS.map((f) => <option key={f} value={f}>{f.split(",")[0]}</option>)}
        </select>
        <select value={value.size || ""} onChange={(e) => onChange({ ...value, size: e.target.value || undefined })} className="rounded border px-1 py-1 text-xs">
          <option value="">Size</option>
          {SIZE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={value.weight || ""} onChange={(e) => onChange({ ...value, weight: e.target.value || undefined })} className="rounded border px-1 py-1 text-xs">
          <option value="">Weight</option>
          {WEIGHT_OPTIONS.map((w) => <option key={w.value} value={w.value}>{w.label}</option>)}
        </select>
      </div>
    </div>
  );
}

export default function CustomizePanel({
  customizations,
  onChange,
  templateId,
  onTemplateChange,
  instances,
  onUpdateStyle,
  layoutConfig,
  onLayoutConfigChange,
  assets,
  globalStyleSchema,
}: Props) {
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);

  // Clear selection if the selected section no longer exists.
  useEffect(() => {
    if (selectedSectionId && !instances.some((i) => i.id === selectedSectionId)) {
      setSelectedSectionId(null);
    }
  }, [instances, selectedSectionId]);

  const selectedInstance = instances.find((i) => i.id === selectedSectionId) || null;
  const selectedStyle: SectionStyle = selectedInstance?.style || {};

  const updateSelectedStyle = (partial: Partial<SectionStyle>) => {
    if (!selectedSectionId) return;
    const merged = { ...selectedStyle, ...partial };
    const hasValues =
      merged.font ||
      merged.color ||
      merged.weight ||
      merged.text_align ||
      merged.layout ||
      typeof merged.show_title === "boolean" ||
      (merged.field_styles && Object.keys(merged.field_styles).length > 0);
    onUpdateStyle(selectedSectionId, hasValues ? merged : {});
  };

  const updateSelectedFieldStyle = (field: string, partial: FieldStyle) => {
    if (!selectedSectionId) return;
    const current = selectedStyle.field_styles?.[field] || {};
    const nextField = { ...current, ...partial };
    const nextFieldStyles = { ...(selectedStyle.field_styles || {}) };
    if (nextField.font || nextField.size || nextField.weight) {
      nextFieldStyles[field] = nextField;
    } else {
      delete nextFieldStyles[field];
    }
    updateSelectedStyle({ field_styles: nextFieldStyles });
  };

  const defaultShowTitle = selectedInstance?.type !== "profile";
  const currentShowTitle =
    typeof selectedStyle.show_title === "boolean"
      ? selectedStyle.show_title
      : defaultShowTitle;

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Customize</h3>
      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Template</h4>
        <div className="space-y-1.5">
          <button
            onClick={() => setShowTemplateModal(true)}
            className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-left transition-colors hover:border-gray-300 hover:bg-gray-50"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">
                {templateId.startsWith("user_") ? "User Template" : templateId.split("-")[1] || templateId}
              </p>
              <p className="text-xs text-gray-400">Click to change template</p>
            </div>
            <Check className="h-4 w-4 text-blue-600" />
          </button>
        </div>
      </div>


      <h4 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-gray-500">Layout</h4>
      <SectionZoneView
        instances={instances}
        layoutConfig={layoutConfig}
        assets={assets}
        readOnly={false}
        selectedSectionId={selectedSectionId}
        onSelect={setSelectedSectionId}
        onUpdateData={() => {}}
        onAddSection={() => {}}
        onRemoveInstance={() => {}}
        onRenameInstance={() => {}}
        onLayoutConfigChange={onLayoutConfigChange}
        onReorderInstances={() => {}}
        onEntryDragEnd={() => {}}
      />

      {selectedInstance && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <div>
              <p className="text-sm font-medium text-gray-900">Style: {selectedInstance.title}</p>
              <p className="text-xs text-gray-400">
                {SECTION_LABELS[selectedInstance.type] || selectedInstance.type}
              </p>
            </div>
          </div>
          <div className="space-y-2 p-3">
            <div>
              <label className="block text-xs text-gray-600">Font</label>
              <select
                value={selectedStyle.font || ""}
                onChange={(e) => updateSelectedStyle({ font: e.target.value || undefined })}
                className="mt-1 w-full rounded border px-2 py-1 text-sm"
              >
                <option value="">Default</option>
                {FONT_OPTIONS.map((f) => (
                  <option key={f} value={f}>
                    {f.split(",")[0]}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="w-14 text-xs text-gray-600">Color</label>
              <input
                type="color"
                value={selectedStyle.color || "#374151"}
                onChange={(e) => updateSelectedStyle({ color: e.target.value })}
                className="h-7 w-10 cursor-pointer rounded border"
              />
              <input
                type="text"
                value={selectedStyle.color || ""}
                onChange={(e) => updateSelectedStyle({ color: e.target.value || undefined })}
                placeholder="Default"
                className="flex-1 rounded border px-2 py-1 text-xs"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Weight</label>
              <select
                value={selectedStyle.weight || ""}
                onChange={(e) => updateSelectedStyle({ weight: e.target.value || undefined })}
                className="mt-1 w-full rounded border px-2 py-1 text-sm"
              >
                <option value="">Default</option>
                {WEIGHT_OPTIONS.map((w) => (
                  <option key={w.value} value={w.value}>
                    {w.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600">Text Align</label>
              <select
                value={selectedStyle.text_align ?? ""}
                onChange={(e) =>
                  updateSelectedStyle({ text_align: (e.target.value || undefined) as SectionStyle["text_align"] })
                }
                className="mt-1 w-full rounded border px-2 py-1 text-sm"
              >
                <option value="">Default</option>
                <option value="left">Left</option>
                <option value="right">Right</option>
                <option value="center">Center</option>
                <option value="justify">Justify</option>
              </select>
            </div>
            {selectedInstance.type === "skills" && (
              <div>
                <label htmlFor="skills-layout" className="block text-xs text-gray-600">Layout</label>
                <select
                  id="skills-layout"
                  value={selectedStyle.layout ?? ""}
                  onChange={(e) =>
                    updateSelectedStyle({
                      layout: (e.target.value || undefined) as SectionStyle["layout"],
                    })
                  }
                  className="mt-1 w-full rounded border px-2 py-1 text-sm"
                >
                  <option value="">Block (default)</option>
                  <option value="inline">Inline</option>
                </select>
              </div>
            )}
            <div className="flex items-center justify-between pt-1">
              <div>
                <label className="block text-xs text-gray-600">Show Title</label>
                <p className="mt-0.5 text-[10px] text-gray-400">
                  {selectedInstance?.type === "profile"
                    ? "Hidden by default for profile."
                    : "Section heading in the live preview and PDF."}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={currentShowTitle}
                onClick={() => updateSelectedStyle({ show_title: !currentShowTitle })}
                className={`relative h-5 w-9 rounded-full transition-colors ${
                  currentShowTitle ? "bg-blue-600" : "bg-gray-300"
                }`}
              >
                <span
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                    currentShowTitle ? "translate-x-4" : "translate-x-0.5"
                  }`}
                />
              </button>
            </div>
            {getFieldDefs(selectedInstance.type).length > 0 && (
              <div className="border-t pt-2 mt-2">
                <h5 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                  Per-field typography
                </h5>
                <div className="space-y-3">
                  {getFieldDefs(selectedInstance.type).map((f) => (
                    <FieldStyleRow
                      key={f.key}
                      label={f.label}
                      value={selectedStyle.field_styles?.[f.key] || {}}
                      onChange={(next) => updateSelectedFieldStyle(f.key, next)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <StyleEditor customizations={customizations} onChange={onChange} title="Global" globalStyleSchema={globalStyleSchema} />


      <TemplateSelectorModal
        open={showTemplateModal}
        onClose={() => setShowTemplateModal(false)}
        templateId={templateId}
        onSelect={(newTemplateId) => {
          onTemplateChange(newTemplateId);
          setShowTemplateModal(false);
        }}
      />
    </div>
  );
}
