import { useEffect, useState, useMemo } from "react";
import { AlertTriangle, Check } from "lucide-react";

import type {
  SectionInstance,
  SectionInstanceStyle,
  LayoutHints,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
  LayoutConfig,
} from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import { getFieldDefs } from "../../lib/sections/fieldStyles";
import TemplateSelectorModal from "./TemplateSelectorModal";
import SectionZoneView from "../layout/SectionZoneView";
import {
  useSupportStore,
  type SupportField,
} from "../../lib/store/supportStore";
import { DATE_STYLE_OPTIONS } from "../../lib/sections/DateField";
interface Props {
  /**
   * Per-CV ``Customizations`` overrides. The Document <details> group
   * below writes these four canonical fields:
   *   - accent_color
   *   - body_font
   *   - heading_font
   *   - spacing
   * Other keys (``per_section``, ``flags``) are preserved.
   */
  customizations?: Record<string, unknown>;
  onCustomizationsChange?: (customizations: Record<string, unknown>) => void;
  templateId: string;
  onTemplateChange: (templateId: string) => void;
  instances: SectionInstance[];
  onUpdateStyle: (id: string, style: SectionInstanceStyle) => void;
  layoutConfig: LayoutConfig;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  assets?: Record<string, string>;
}

const FONT_OPTIONS = [
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

// TextStyle.font_size is a Literal enum (xs / small / normal / large / xl).
// The panel surfaces enum names and maps them to CSS strings at write
// time. Unmapped CSS values snap to the nearest enum bucket.
const FONT_SIZE_CSS: Record<NonNullable<TextStyle["font_size"]>, string> = {
  xs: "11px",
  small: "12px",
  normal: "14px",
  large: "16px",
  xl: "18px",
};

const FONT_SIZE_TO_ENUM: Record<string, NonNullable<TextStyle["font_size"]>> = Object.fromEntries(
  Object.entries(FONT_SIZE_CSS).map(([k, v]) => [v, k]),
) as Record<string, NonNullable<TextStyle["font_size"]>>;

function normalizeFontSize(css: string | null | undefined): TextStyle["font_size"] {
  if (!css) return undefined;
  if (css in FONT_SIZE_TO_ENUM) return FONT_SIZE_TO_ENUM[css];
  // Snap to nearest known enum value (rounded to 14px if in between).
  const numeric = parseFloat(css);
  if (Number.isNaN(numeric)) return undefined;
  if (numeric <= 11) return "xs";
  if (numeric <= 12) return "small";
  if (numeric <= 14) return "normal";
  if (numeric <= 16) return "large";
  return "xl";
}

function FieldStyleRow({
  label,
  initial,
  onChange,
}: {
  label: string;
  initial: TextStyle;
  onChange: (next: TextStyle) => void;
}) {
  return (
    <div className="rounded border border-gray-100 p-2">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-gray-500">{label}</p>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-gray-700">
          <input
            type="checkbox"
            className="h-3.5 w-3.5"
            checked={initial.bold === true}
            onChange={(e) => onChange({ ...initial, bold: e.target.checked || undefined })}
          />
          Bold
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-gray-700">
          <input
            type="checkbox"
            className="h-3.5 w-3.5"
            checked={initial.italic === true}
            onChange={(e) => onChange({ ...initial, italic: e.target.checked || undefined })}
          />
          Italic
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-gray-700">
          Size
          <select
            value={initial.font_size ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              onChange({ ...initial, font_size: v ? (v as NonNullable<TextStyle["font_size"]>) : undefined });
            }}
            className="rounded border px-1.5 py-0.5 text-[11px]"
          >
            <option value="">Default</option>
            {Object.keys(FONT_SIZE_CSS).map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-gray-700" title="Text color">
          <input
            type="color"
            className="h-6 w-8 cursor-pointer rounded border"
            value={initial.color ?? "#000000"}
            onChange={(e) => onChange({ ...initial, color: e.target.value })}
          />
          <input
            type="text"
            value={initial.color ?? ""}
            onChange={(e) => onChange({ ...initial, color: e.target.value || null })}
            className="w-20 rounded border px-1.5 py-0.5 text-[11px]"
            placeholder="#RRGGBB"
          />
        </label>
      </div>
    </div>
  );
}

function BestEffortBadge({ field }: { field: SupportField }) {
  const support = useSupportStore((s) => s.support);
  const level = support?.[field];
  if (level !== "BEST_EFFORT") return null;
  return (
    <AlertTriangle
      className="ml-1 inline h-3.5 w-3.5 text-amber-500"
      aria-label="Renderer is best-effort for this feature"
    />
  );
}

const SPACING_OPTIONS = ["compact", "comfortable", "minimal"] as const;

export default function CustomizePanel({
  templateId,
  onTemplateChange,
  instances,
  onUpdateStyle,
  layoutConfig,
  onLayoutConfigChange,
  assets,
  customizations,
  onCustomizationsChange,
}: Props) {
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const support = useSupportStore((s) => s.support);
  const supportError = useSupportStore((s) => s.error);
  const supportLoaded = useSupportStore((s) => s.loaded);

  useEffect(() => {
    if (selectedSectionId && !instances.some((i) => i.id === selectedSectionId)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- derived clear when selection vanished; see Phase 9 lint debt
      setSelectedSectionId(null);
    }
  }, [instances, selectedSectionId]);

  const selectedInstance = instances.find((i) => i.id === selectedSectionId) || null;
  const selectedStyle = (selectedInstance?.style ?? {}) as SectionInstanceStyle;

  const writeStyle = (style: SectionInstanceStyle) => {
    if (!selectedSectionId) return;
    onUpdateStyle(selectedSectionId, style);
  };

  const updateSelectedLayout = (partial: Partial<LayoutHints>) =>
    writeStyle({ ...selectedStyle, layout: { ...(selectedStyle.layout ?? {}), ...partial } });

  const updateSelectedSubsection = (partial: Partial<SubsectionStyle>) =>
    writeStyle({
      ...selectedStyle,
      subsection: { ...(selectedStyle.subsection ?? {}), ...partial },
    });

  const updateSelectedPolicy = (partial: Partial<SectionPolicy>) =>
    writeStyle({
      ...selectedStyle,
      policy: { ...(selectedStyle.policy ?? {}), ...partial },
    });

  const writeCustomizations = (partial: Record<string, unknown>) => {
    const next: Record<string, unknown> = { ...(customizations ?? {}), ...partial };
    onCustomizationsChange?.(next);
  };

  const updateCustomizationsField = (key: string, value: unknown) => {
    const next: Record<string, unknown> = { ...(customizations ?? {}) };
    if (value === null || value === undefined) {
      delete next[key];
    } else {
      next[key] = value;
    }
    onCustomizationsChange?.(next);
  };

  const customizationString = (key: string): string => {
    const v = customizations?.[key];
    return typeof v === "string" ? v : "";
  };

  const supportLoadedButEmpty = supportLoaded && support === null && supportError !== null;
  const retry = () => useSupportStore.getState().retry();

  const defaultShowTitle = selectedInstance ? selectedInstance.type !== "profile" : true;
  const currentShowTitle =
    typeof selectedStyle.policy?.show_title === "boolean"
      ? selectedStyle.policy.show_title
      : defaultShowTitle;

  const fieldDefs = useMemo(
    () => (selectedInstance ? getFieldDefs(selectedInstance.type) : []),
    [selectedInstance],
  );

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Customize</h3>

      {supportLoadedButEmpty && (
        <div
          className="mb-3 flex items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700"
          role="status"
        >
          <span>Renderer support unavailable.</span>
          <button
            onClick={retry}
            className="rounded bg-amber-200 px-2 py-1 text-[11px] font-medium hover:bg-amber-300"
          >
            Retry
          </button>
        </div>
      )}

      <details className="mb-3 rounded border border-gray-100 p-2" data-testid="document-group">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-gray-500">
          Document
        </summary>
        <div className="mt-2 space-y-2">
          <div className="flex items-center gap-2">
            <label className="w-28 text-[11px] text-gray-600" htmlFor="doc-accent">
              Accent color
            </label>
            <input
              id="doc-accent"
              type="color"
              value={customizationString("accent_color") || "#000000"}
              onChange={(e) => updateCustomizationsField("accent_color", e.target.value)}
            />
            <input
              type="text"
              value={customizationString("accent_color")}
              onChange={(e) => updateCustomizationsField("accent_color", e.target.value || null)}
              data-testid="document-accent-input"
              className="flex-1 rounded border px-2 py-1 text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="w-28 text-[11px] text-gray-600" htmlFor="doc-body">
              Body font
            </label>
            <select
              id="doc-body"
              value={customizationString("body_font")}
              onChange={(e) => updateCustomizationsField("body_font", e.target.value || null)}
              data-testid="document-body-font"
              className="flex-1 rounded border px-2 py-1 text-xs"
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
            <label className="w-28 text-[11px] text-gray-600" htmlFor="doc-heading">
              Heading font
            </label>
            <select
              id="doc-heading"
              value={customizationString("heading_font")}
              onChange={(e) => updateCustomizationsField("heading_font", e.target.value || null)}
              className="flex-1 rounded border px-2 py-1 text-xs"
            >
              <option value="">Default</option>
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f}>
                  {f.split(",")[0]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="mb-1 block text-[11px] text-gray-600">Spacing</span>
            <div className="flex gap-3">
              {SPACING_OPTIONS.map((s) => (
                <label key={s} className="flex items-center gap-1 text-xs text-gray-700">
                  <input
                    type="radio"
                    name="document-spacing"
                    value={s}
                    checked={customizationString("spacing") === s}
                    onChange={() => writeCustomizations({ spacing: s })}
                    data-testid={`document-spacing-${s}`}
                  />
                  {s}
                </label>
              ))}
            </div>
          </div>
        </div>
      </details>

      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Template</h4>
        <div className="space-y-1.5">
          <button
            onClick={() => setShowTemplateModal(true)}
            className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-left transition-colors hover:border-gray-300 hover:bg-gray-50"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">
                {templateId.startsWith("user_")
                  ? "User Template"
                  : templateId.split("-")[1] || templateId}
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

          <div className="space-y-3 p-3">
            <details open className="rounded border border-gray-100 p-2">
              <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                Layout (page flow)
              </summary>
              <div className="mt-2 space-y-2">
                <div>
                  <label className="block text-[11px] text-gray-600">Font family</label>
                  <select
                    value={(selectedStyle.layout?.font_family as string | null | undefined) ?? ""}
                    onChange={(e) =>
                      updateSelectedLayout({
                        font_family: e.target.value || null,
                      })
                    }
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

                {support?.break_before !== "NONE" && (
                  <label className="flex items-center gap-2 text-xs text-gray-700">
                    <input
                      type="checkbox"
                      checked={selectedStyle.layout?.break_before === true}
                      onChange={(e) => updateSelectedLayout({ break_before: e.target.checked })}
                    />
                    Break before
                    <BestEffortBadge field="break_before" />
                  </label>
                )}

                {support?.keep_together !== "NONE" && (
                  <label className="flex items-center gap-2 text-xs text-gray-700">
                    <input
                      type="checkbox"
                      checked={selectedStyle.layout?.keep_together === true}
                      onChange={(e) => updateSelectedLayout({ keep_together: e.target.checked })}
                    />
                    Keep together
                    <BestEffortBadge field="keep_together" />
                  </label>
                )}

                {support?.heading_keeps_with_first !== "NONE" && (
                  <label className="flex items-center gap-2 text-xs text-gray-700">
                    <input
                      type="checkbox"
                      checked={selectedStyle.layout?.heading_keeps_with_first === true}
                      onChange={(e) =>
                        updateSelectedLayout({ heading_keeps_with_first: e.target.checked })
                      }
                    />
                    Heading keeps with first
                    <BestEffortBadge field="heading_keeps_with_first" />
                  </label>
                )}

                <div className="flex items-center gap-2">
                  <label className="w-20 text-[11px] text-gray-600">Orphans</label>
                  <input
                    type="number"
                    min={1}
                    value={selectedStyle.layout?.orphans ?? ""}
                    onChange={(e) =>
                      updateSelectedLayout({
                        orphans: e.target.value === "" ? undefined : Number(e.target.value),
                      })
                    }
                    className="w-20 rounded border px-2 py-1 text-xs"
                  />
                  <label className="w-20 text-[11px] text-gray-600">Widows</label>
                  <input
                    type="number"
                    min={1}
                    value={selectedStyle.layout?.widows ?? ""}
                    onChange={(e) =>
                      updateSelectedLayout({
                        widows: e.target.value === "" ? undefined : Number(e.target.value),
                      })
                    }
                    className="w-20 rounded border px-2 py-1 text-xs"
                  />
                </div>

                {["experience", "education", "projects", "certifications", "research"].includes(
                  selectedInstance.type,
                ) && (
                  <div>
                    <label className="block text-[11px] text-gray-600">Date format</label>
                    <select
                      value={selectedStyle.layout?.date_style?.key ?? ""}
                      onChange={(e) =>
                        updateSelectedLayout({
                          date_style: e.target.value
                            ? { key: e.target.value, rangeSep: " – " }
                            : undefined,
                        })
                      }
                      className="mt-1 w-full rounded border px-2 py-1 text-sm"
                    >
                      <option value="">Default (YYYY-MM)</option>
                      {DATE_STYLE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </details>

            <details className="rounded border border-gray-100 p-2">
              <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                Block style (subsection)
              </summary>
              <div className="mt-2 space-y-2">
                <div>
                  <label className="block text-[11px] text-gray-600">Text align</label>
                  <select
                    value={selectedStyle.subsection?.text_align ?? ""}
                    onChange={(e) =>
                      updateSelectedSubsection({
                        text_align: (e.target.value || null) as SubsectionStyle["text_align"],
                      })
                    }
                    className="mt-1 w-full rounded border px-2 py-1 text-sm"
                  >
                    <option value="">Default</option>
                    <option value="left">Left</option>
                    <option value="center">Center</option>
                    <option value="right">Right</option>
                    <option value="justify">Justify</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="w-28 text-[11px] text-gray-600">Spacing before</label>
                  <input
                    type="text"
                    placeholder="e.g. 12px"
                    value={selectedStyle.subsection?.spacing_before ?? ""}
                    onChange={(e) =>
                      updateSelectedSubsection({
                        spacing_before: e.target.value || null,
                      })
                    }
                    className="flex-1 rounded border px-2 py-1 text-xs"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="w-28 text-[11px] text-gray-600">Spacing after</label>
                  <input
                    type="text"
                    placeholder="e.g. 12px"
                    value={selectedStyle.subsection?.spacing_after ?? ""}
                    onChange={(e) =>
                      updateSelectedSubsection({
                        spacing_after: e.target.value || null,
                      })
                    }
                    className="flex-1 rounded border px-2 py-1 text-xs"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="w-28 text-[11px] text-gray-600">BG color</label>
                  <input
                    type="color"
                    value={selectedStyle.subsection?.background_color ?? "#ffffff"}
                    onChange={(e) =>
                      updateSelectedSubsection({ background_color: e.target.value })
                    }
                  />
                  <input
                    type="text"
                    value={selectedStyle.subsection?.background_color ?? ""}
                    onChange={(e) =>
                      updateSelectedSubsection({
                        background_color: e.target.value || null,
                      })
                    }
                    className="flex-1 rounded border px-2 py-1 text-xs"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="w-28 text-[11px] text-gray-600">Section color</label>
                  <input
                    type="color"
                    value={selectedStyle.subsection?.section_color ?? "#000000"}
                    onChange={(e) => updateSelectedSubsection({ section_color: e.target.value })}
                  />
                  <input
                    type="text"
                    value={selectedStyle.subsection?.section_color ?? ""}
                    onChange={(e) =>
                      updateSelectedSubsection({
                        section_color: e.target.value || null,
                      })
                    }
                    className="flex-1 rounded border px-2 py-1 text-xs"
                  />
                </div>
              </div>
            </details>

            <details className="rounded border border-gray-100 p-2">
              <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                Section policy
              </summary>
              <div className="mt-2 space-y-2">
                <label className="flex items-center gap-2 text-xs text-gray-700">
                  <input
                    type="checkbox"
                    checked={currentShowTitle}
                    onChange={(e) => updateSelectedPolicy({ show_title: e.target.checked })}
                  />
                  Show title
                </label>
                {selectedInstance.type === "skills" &&
                  support?.feature_skills_inline !== "NONE" && (
                    <div>
                      <label className="block text-[11px] text-gray-600">Skills layout</label>
                      <select
                        value={selectedStyle.policy?.skill_variant ?? ""}
                        onChange={(e) =>
                          updateSelectedPolicy({
                            skill_variant: (e.target.value || null) as SectionPolicy["skill_variant"],
                          })
                        }
                        className="mt-1 w-full rounded border px-2 py-1 text-sm"
                      >
                        <option value="">Default</option>
                        <option value="block">Block</option>
                        <option value="inline">Inline</option>
                      </select>
                    </div>
                  )}
              </div>
            </details>

            {fieldDefs.length > 0 && (
              <details className="rounded border border-gray-100 p-2">
                <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-gray-500">
                  Field styles
                </summary>
                <div className="mt-2 space-y-3">
                  {fieldDefs.map((f) => (
                    <FieldStyleRow
                      key={f.key}
                      label={f.label}
                      initial={selectedStyle.text?.[f.key] ?? {}}
                      onChange={(next) => {
                        const text = { ...(selectedStyle.text ?? {}) };
                        if (Object.keys(next).length === 0) {
                          delete text[f.key];
                        } else {
                          text[f.key] = next;
                        }
                        writeStyle({ ...selectedStyle, text });
                      }}
                    />
                  ))}
                </div>
              </details>
            )}
          </div>
        </div>
      )}

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

export { normalizeFontSize };
