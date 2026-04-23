import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronDown } from "lucide-react";
import type { SectionInstance, SectionStyle, LayoutConfig } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import TemplateSelectorModal from "./TemplateSelectorModal";
import StyleEditor from "./StyleEditor";
import ZonesSection from "./ZonesSection";

interface Props {
  customizations: Record<string, any>;
  onChange: (customizations: Record<string, any>) => void;
  templateId: string;
  onTemplateChange: (templateId: string) => void;
  instances: SectionInstance[];
  onUpdateStyle: (id: string, style: SectionStyle) => void;
  layoutConfig: LayoutConfig | null;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  templateLayoutConfig: LayoutConfig | null;
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

export default function CustomizePanel({ customizations, onChange, templateId, onTemplateChange, instances, onUpdateStyle, layoutConfig, onLayoutConfigChange, templateLayoutConfig }: Props) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);

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
              <p className="text-xs text-gray-400">
                {templateId.startsWith("user_") ? "Click to change template" : "Click to change template"}
              </p>
            </div>
            <Check className="h-4 w-4 text-blue-600" />
          </button>
        </div>
      </div>

      <ZonesSection
        layoutConfig={layoutConfig}
        onChange={onLayoutConfigChange}
        templateLayoutConfig={templateLayoutConfig}
      />

      <StyleEditor customizations={customizations} onChange={onChange} title="Global" />

      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Section Overrides</h4>
      <div className="space-y-2">
        {instances.map((instance) => {
          const isOpen = expandedSection === instance.id;
          const style = instance.style || {};
          const updateStyle = (partial: Partial<SectionStyle>) => {
            const merged = { ...style, ...partial };
            const hasValues = merged.font || merged.color || merged.weight;
            onUpdateStyle(instance.id, hasValues ? merged : {});
          };
          return (
            <div key={instance.id} className="overflow-hidden rounded-lg border border-gray-200">
              <button
                onClick={() => setExpandedSection(isOpen ? null : instance.id)}
                className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-gray-50"
              >
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-gray-900">{instance.title}</p>
                  <span className="text-xs text-gray-400">{SECTION_LABELS[instance.type] || instance.type}</span>
                </div>
                <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
                  <ChevronDown className="h-4 w-4 text-gray-400" />
                </motion.div>
              </button>
              <AnimatePresence>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="space-y-2 border-t p-3">
                      <div>
                        <label className="block text-xs text-gray-600">Font</label>
                        <select
                          value={style.font || ""}
                          onChange={(e) => updateStyle({ font: e.target.value || undefined })}
                          className="mt-1 w-full rounded border px-2 py-1 text-sm"
                        >
                          <option value="">Default</option>
                          {FONT_OPTIONS.map((f) => (
                            <option key={f} value={f}>{f.split(",")[0]}</option>
                          ))}
                        </select>
                      </div>
                      <div className="flex items-center gap-2">
                        <label className="w-14 text-xs text-gray-600">Color</label>
                        <input
                          type="color"
                          value={style.color || "#374151"}
                          onChange={(e) => updateStyle({ color: e.target.value })}
                          className="h-7 w-10 cursor-pointer rounded border"
                        />
                        <input
                          type="text"
                          value={style.color || ""}
                          onChange={(e) => updateStyle({ color: e.target.value || undefined })}
                          placeholder="Default"
                          className="flex-1 rounded border px-2 py-1 text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600">Weight</label>
                        <select
                          value={style.weight || ""}
                          onChange={(e) => updateStyle({ weight: e.target.value || undefined })}
                          className="mt-1 w-full rounded border px-2 py-1 text-sm"
                        >
                          <option value="">Default</option>
                          {WEIGHT_OPTIONS.map((w) => (
                            <option key={w.value} value={w.value}>{w.label}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

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