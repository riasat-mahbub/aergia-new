import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronDown } from "lucide-react";
import type { SectionInstance, SectionStyle } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";

interface Props {
  customizations: Record<string, any>;
  onChange: (customizations: Record<string, any>) => void;
  templateId: string;
  onTemplateChange: (templateId: string) => void;
  instances: SectionInstance[];
  onUpdateStyle: (id: string, style: SectionStyle) => void;
}

const TEMPLATES = [
  { id: "generic-modern", name: "Modern", hint: "2-column · sidebar + main" },
  { id: "generic-classic", name: "Classic", hint: "1-column · serif · dividers" },
  { id: "generic-minimal", name: "Minimal", hint: "1-column · clean · no decoration" },
];

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

export default function CustomizePanel({ customizations, onChange, templateId, onTemplateChange, instances, onUpdateStyle }: Props) {
  const [globalOpen, setGlobalOpen] = useState(true);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const colors = customizations?.colors || {};
  const fonts = customizations?.fonts || {};
  const spacing = customizations?.spacing || {};

  const updateColors = (key: string, value: string) => {
    onChange({ ...customizations, colors: { ...colors, [key]: value } });
  };
  const updateFonts = (key: string, value: string) => {
    onChange({ ...customizations, fonts: { ...fonts, [key]: value } });
  };
  const updateSpacing = (key: string, value: string) => {
    onChange({ ...customizations, spacing: { ...spacing, [key]: value } });
  };

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Customize</h3>

      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Template</h4>
        <div className="space-y-1.5">
          {TEMPLATES.map((t) => {
            const isActive = t.id === templateId;
            return (
              <button
                key={t.id}
                onClick={() => !isActive && onTemplateChange(t.id)}
                disabled={isActive}
                className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition-colors ${
                  isActive
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                } disabled:cursor-default`}
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{t.name}</p>
                  <p className="text-xs text-gray-400">{t.hint}</p>
                </div>
                {isActive && <Check className="h-4 w-4 text-blue-600" />}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-4 rounded-lg border border-gray-200">
        <button
          onClick={() => setGlobalOpen(!globalOpen)}
          className="flex w-full items-center justify-between rounded-t-lg px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 hover:bg-gray-50"
        >
          Global
          <motion.div animate={{ rotate: globalOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown className="h-3 w-3" />
          </motion.div>
        </button>
        <AnimatePresence>
          {globalOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="space-y-3 border-t p-3">
                <div className="space-y-2">
                  {[
                    { key: "accent", label: "Accent", default: "#2563eb" },
                    { key: "bg_sidebar", label: "Sidebar BG", default: "#f8fafc" },
                    { key: "header", label: "Header", default: "#000000" },
                    { key: "divider", label: "Divider", default: "#d1d5db" },
                    { key: "text", label: "Text", default: "#374151" },
                    { key: "heading", label: "Heading", default: "#111827" },
                  ].map(({ key, label, default: _default }) => (
                    <div key={key} className="flex items-center gap-2">
                      <label className="w-20 text-xs text-gray-600">{label}</label>
                      <input
                        type="color"
                        value={colors[key] || _default}
                        onChange={(e) => updateColors(key, e.target.value)}
                        className="h-7 w-10 cursor-pointer rounded border"
                      />
                      <input
                        type="text"
                        value={colors[key] || _default}
                        onChange={(e) => updateColors(key, e.target.value)}
                        className="flex-1 rounded border px-2 py-1 text-xs"
                      />
                    </div>
                  ))}
                </div>
                <div className="space-y-2 border-t pt-3">
                  <div>
                    <label className="block text-xs text-gray-600">Body Font</label>
                    <select value={fonts.body || "Inter, system-ui, sans-serif"} onChange={(e) => updateFonts("body", e.target.value)} className="mt-1 w-full rounded border px-2 py-1 text-sm">
                      {FONT_OPTIONS.map((f) => <option key={f} value={f}>{f.split(",")[0]}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600">Heading Font</label>
                    <select value={fonts.heading || "Inter, system-ui, sans-serif"} onChange={(e) => updateFonts("heading", e.target.value)} className="mt-1 w-full rounded border px-2 py-1 text-sm">
                      {FONT_OPTIONS.map((f) => <option key={f} value={f}>{f.split(",")[0]}</option>)}
                    </select>
                  </div>
                </div>
                <div className="border-t pt-3">
                  <label className="block text-xs text-gray-600">Section Gap: {spacing.section_gap || "24px"}</label>
                  <input
                    type="range"
                    min="8"
                    max="48"
                    value={parseInt(spacing.section_gap || "24")}
                    onChange={(e) => updateSpacing("section_gap", `${e.target.value}px`)}
                    className="mt-1 w-full"
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

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
    </div>
  );
}