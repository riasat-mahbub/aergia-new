import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";

export interface StyleVarSchema {
  key: string;
  type: "color" | "font" | "length" | "enum" | "boolean";
  label: string;
  default: string;
  options?: string[];
  min?: number;
  max?: number;
}

interface StyleEditorProps {
  customizations: Record<string, any>;
  onChange: (customizations: Record<string, any>) => void;
  title?: string;
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

const DEFAULT_SCHEMA: StyleVarSchema[] = [
  { key: "accent", type: "color", label: "Accent", default: "#2563eb" },
  { key: "bg_sidebar", type: "color", label: "Sidebar BG", default: "#f8fafc" },
  { key: "header", type: "color", label: "Header", default: "#000000" },
  { key: "divider", type: "color", label: "Divider", default: "#d1d5db" },
  { key: "text", type: "color", label: "Text", default: "#374151" },
  { key: "heading", type: "color", label: "Heading", default: "#111827" },
  { key: "section_gap", type: "length", label: "Section Gap", default: "24px", min: 0, max: 48 },
  { key: "subsection_gap", type: "length", label: "Subsection Gap", default: "12px", min: 0, max: 24 },
  { key: "underline_section_titles", type: "boolean", label: "Underline Section Titles", default: "false" },
]

export default function StyleEditor({
  customizations,
  onChange,
  title = "Colors & Fonts",
  globalStyleSchema,
}: StyleEditorProps) {
  const [open, setOpen] = useState(true);

  const schema = globalStyleSchema || DEFAULT_SCHEMA;

  const colors = customizations?.colors || {};
  const fonts = customizations?.fonts || {};
  const spacing = customizations?.spacing || {};
  const flags = customizations?.flags || {};

  const updateColors = (key: string, value: string) => {
    onChange({ ...customizations, colors: { ...colors, [key]: value } });
  };
  const updateFonts = (key: string, value: string) => {
    onChange({ ...customizations, fonts: { ...fonts, [key]: value } });
  };
  const updateSpacing = (key: string, value: string) => {
    onChange({ ...customizations, spacing: { ...spacing, [key]: value } });
  };
  const updateFlags = (key: string, value: boolean) => {
    onChange({ ...customizations, flags: { ...flags, [key]: value } });
  };

  const updateVar = (key: string, value: string | boolean, type: string) => {
    if (type === "color") updateColors(key, String(value));
    else if (type === "font") updateFonts(key, String(value));
    else if (type === "length") updateSpacing(key, String(value));
    else if (type === "boolean") {
      const next = typeof value === "boolean" ? value : value === "true";
      updateFlags(key, next);
    } else if (type === "enum") {
      // determine bucket based on key presence
      if (colors.hasOwnProperty(key)) updateColors(key, String(value));
      else if (fonts.hasOwnProperty(key)) updateFonts(key, String(value));
      else if (flags.hasOwnProperty(key)) updateFlags(key, String(value) === "true");
      else updateSpacing(key, String(value));
    }
  };

  const getVarValue = (key: string, def: string) => {
    if (colors.hasOwnProperty(key)) return colors[key] || def;
    if (fonts.hasOwnProperty(key)) return fonts[key] || def;
    if (spacing.hasOwnProperty(key)) return spacing[key] || def;
    if (flags.hasOwnProperty(key)) return String(flags[key]);
    return def;
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
              {schema.map((item) => {
                const value = getVarValue(item.key, item.default);
                switch (item.type) {
                  case "color":
                    return (
                      <div key={item.key} className="flex items-center gap-2">
                        <label className="w-20 text-xs text-gray-600">{item.label}</label>
                        <input
                          type="color"
                          value={value}
                          onChange={(e) => updateVar(item.key, e.target.value, "color")}
                          className="h-7 w-10 cursor-pointer rounded border"
                        />
                        <input
                          type="text"
                          value={value}
                          onChange={(e) => updateVar(item.key, e.target.value, "color")}
                          className="flex-1 rounded border px-2 py-1 text-xs"
                        />
                      </div>
                    );
                  case "font":
                    return (
                      <div key={item.key} className="flex flex-col">
                        <label className="block text-xs text-gray-600">{item.label}</label>
                        <select
                          value={value}
                          onChange={(e) => updateVar(item.key, e.target.value, "font")}
                          className="mt-1 w-full rounded border px-2 py-1 text-sm"
                        >
                          {FONT_OPTIONS.map((f) => (
                            <option key={f} value={f}>
                              {f.split(",")[0]}
                            </option>
                          ))}
                        </select>
                      </div>
                    );
                  case "length": {
                    const min = item.min ?? 8;
                    const max = item.max ?? 48;
                    return (
                      <div key={item.key} className="flex flex-col">
                        <label className="block text-xs text-gray-600">
                          {item.label}: {value}
                        </label>
                        <input
                          type="range"
                          min={min}
                          max={max}
                          value={Math.min(Math.max(parseInt(value.replace("px", "")) || min, min), max)}
                          onChange={(e) => updateVar(item.key, `${e.target.value}px`, "length")}
                          className="mt-1 w-full"
                        />
                      </div>
                    );
                  };
                  case "boolean": {
                    const isChecked = value === true || value === "true";

                    return (
                      <div key={item.key} className="flex items-center justify-between gap-2">
                        <label htmlFor={`switch-${item.key}`} className="text-xs text-gray-600 cursor-pointer select-none">
                          {item.label}
                        </label>
                        <button
                          id={`switch-${item.key}`}
                          type="button"
                          role="switch"
                          aria-checked={isChecked}
                          onClick={() => updateVar(item.key, !isChecked, "boolean")}
                          className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                            isChecked ? "bg-blue-600" : "bg-gray-300"
                          }`}
                        >
                          <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${
                              isChecked ? "translate-x-[18px]" : "translate-x-[2px]"
                            }`}
                          />
                        </button>
                      </div>
                    );
                  };
                  case "enum":
                    return (
                      <div key={item.key} className="flex flex-col">
                        <label className="block text-xs text-gray-600">{item.label}</label>
                        <select
                          value={value}
                          onChange={(e) => updateVar(item.key, e.target.value, "enum")}
                          className="mt-1 w-full rounded border px-2 py-1 text-sm"
                        >
                          {item.options?.map((opt) => (
                            <option key={opt} value={opt}>
                              {opt}
                            </option>
                          ))}
                        </select>
                      </div>
                    );
                  default:
                    return null;
                 }
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}