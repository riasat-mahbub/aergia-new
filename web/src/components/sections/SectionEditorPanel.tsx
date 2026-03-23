import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import type { SectionInstance, SectionStyle } from "../../lib/sections/types";
import { renderSectionEditor } from "./SectionRegistry";

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

interface Props {
  instance: SectionInstance;
  onChange: (id: string, data: any) => void;
  onUpdateStyle?: (id: string, style: SectionStyle) => void;
}

export default function SectionEditorPanel({ instance, onChange, onUpdateStyle }: Props) {
  const [stylesOpen, setStylesOpen] = useState(false);

  const handleSectionChange = (newData: any) => {
    onChange(instance.id, newData);
  };

  const style = instance.style || {};

  const updateStyle = (partial: Partial<SectionStyle>) => {
    if (!onUpdateStyle) return;
    const merged = { ...style, ...partial };
    const hasValues = merged.font || merged.color || merged.weight;
    onUpdateStyle(instance.id, hasValues ? merged : {});
  };

  return (
    <div className={`rounded-lg border ${instance.enabled ? "border-gray-200" : "border-dashed border-gray-300"} bg-white p-4`}>
      {onUpdateStyle && (
        <>
          <button
            onClick={() => setStylesOpen(!stylesOpen)}
            className="mb-2 flex w-full items-center justify-between rounded px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100"
          >
            Style
            <motion.div animate={{ rotate: stylesOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <ChevronDown className="h-3 w-3" />
            </motion.div>
          </button>
          <AnimatePresence>
            {stylesOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="mb-3 space-y-2 rounded bg-gray-50 p-3">
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
        </>
      )}
      {instance.enabled && renderSectionEditor(instance.type, instance.data, handleSectionChange)}
    </div>
  );
}
