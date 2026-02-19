import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";

interface Props {
  customizations: Record<string, any>;
  onChange: (customizations: Record<string, any>) => void;
}

const FONT_OPTIONS = [
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

export default function CustomizePanel({ customizations, onChange }: Props) {
  const [activeTab, setActiveTab] = useState<"colors" | "fonts" | "spacing">("colors");

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
      <div className="mb-3 flex gap-1">
        {(["colors", "fonts", "spacing"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`rounded px-2 py-1 text-xs ${activeTab === tab ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <AnimatePresence>
        {activeTab === "colors" && (
          <motion.div
            key="colors"
            initial={false}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            className="space-y-2">
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
        </motion.div>
      )}

      {activeTab === "fonts" && (
        <motion.div
          key="fonts"
          initial={false}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 10 }}
          className="space-y-3">
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
        </motion.div>
      )}

      {activeTab === "spacing" && (
        <motion.div
          key="spacing"
          initial={false}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 10 }}
          className="space-y-3">
          <div>
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
        </motion.div>
      )}
      </AnimatePresence>
    </div>
  );
}
