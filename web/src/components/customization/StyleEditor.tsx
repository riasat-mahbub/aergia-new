import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";

interface StyleEditorProps {
  customizations: Record<string, any>;
  onChange: (customizations: Record<string, any>) => void;
  title?: string;
}

const FONT_OPTIONS = [
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

export default function StyleEditor({
  customizations,
  onChange,
  title = "Colors & Fonts",
}: StyleEditorProps) {
  const [open, setOpen] = useState(true);

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
    <div className="mb-4 rounded-lg border border-gray-200">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between rounded-t-lg px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 hover:bg-gray-50"
      >
        {title}
        <motion.div
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-3 w-3" />
        </motion.div>
      </button>
      <AnimatePresence>
        {open && (
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
                  <select
                    value={fonts.body || "Inter, system-ui, sans-serif"}
                    onChange={(e) => updateFonts("body", e.target.value)}
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                  >
                    {FONT_OPTIONS.map((f) => (
                      <option key={f} value={f}>
                        {f.split(",")[0]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-600">Heading Font</label>
                  <select
                    value={fonts.heading || "Inter, system-ui, sans-serif"}
                    onChange={(e) => updateFonts("heading", e.target.value)}
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                  >
                    {FONT_OPTIONS.map((f) => (
                      <option key={f} value={f}>
                        {f.split(",")[0]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="border-t pt-3">
                <label className="block text-xs text-gray-600">
                  Section Gap: {spacing.section_gap || "24px"}
                </label>
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
  );
}