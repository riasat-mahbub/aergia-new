/**
 * Phase 3 — TemplateWizard rebuild.
 *
 * Four steps: Basics, Layout, Global Styles, Review. The wizard's local
 * state is the source of truth; the page mirrors the live manifest into
 * the preview pane on every change. Save is gated by
 * ``templateManifestSchema``.
 *
 * Phase 4 — the wizard now writes the closed design vocabulary:
 * width/padding tokens, font tokens, color refs (hex literal or
 * palette.<name>). The manifest never carries raw CSS strings.
 */

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check } from "lucide-react";

import { uploadUserTemplate } from "../../lib/api/templates";
import { templateManifestSchema } from "../../lib/validators/sections";
import { SECTION_LABELS, SECTION_TYPES } from "../../lib/sections/types";
import { useSupportStore, type SupportField } from "../../lib/store/supportStore";

// Design tokens. The schema declares these enums; the wizard offers the
// same options via pickers. The renderer (resolver) maps each token to
// its CSS value; the manifest only carries the name.
const WIDTH_TOKENS = ["narrow", "half", "full", "auto"] as const;
const PADDING_TOKENS = ["none", "tight", "comfortable", "loose"] as const;
const FONT_TOKENS = ["sans-serif", "serif", "mono", "display"] as const;
const SPACING_OPTIONS = ["compact", "comfortable", "minimal"] as const;
type SpacingPreset = (typeof SPACING_OPTIONS)[number];

// Default palette: matches the backend's DEFAULT_PALETTE. The wizard
// authors a value by picking a palette slot or typing a hex literal.
const PALETTE_OPTIONS = [
  { name: "accent", hex: "#2563eb" },
  { name: "surface", hex: "#ffffff" },
  { name: "surface-2", hex: "#f8fafc" },
  { name: "text", hex: "#111827" },
  { name: "text-muted", hex: "#6b7280" },
  { name: "divider", hex: "#e5e7eb" },
] as const;

const FONT_LABELS: Record<(typeof FONT_TOKENS)[number], string> = {
  "sans-serif": "Sans-serif",
  serif: "Serif",
  mono: "Monospace",
  display: "Display",
};

const WIDTH_LABELS: Record<(typeof WIDTH_TOKENS)[number], string> = {
  narrow: "Narrow (~30%)",
  half: "Half (~50%)",
  full: "Full (100%)",
  auto: "Auto",
};

const PADDING_LABELS: Record<(typeof PADDING_TOKENS)[number], string> = {
  none: "None",
  tight: "Tight",
  comfortable: "Comfortable",
  loose: "Loose",
};

const STEPS = ["Basics", "Layout", "Global Styles", "Review"] as const;
type StepName = (typeof STEPS)[number];

type Manifest = Record<string, unknown>;

interface ZoneRecord {
  id: string;
  label?: string | null;
  styles?: {
    width?: string | null;
    background?: string | null;
    padding?: string | null;
  };
}

interface SectionPolicyRecord {
  show_title?: boolean;
  skill_variant?: "block" | "inline" | null;
}

interface TemplateWizardProps {
  initialManifest?: Record<string, unknown>;
  onManifestChange?: (m: Record<string, unknown>) => void;
  onComplete?: () => void;
  onSave?: (manifest: Record<string, unknown>) => void;
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

function cloneBase(initial: Manifest | undefined): Manifest {
  const base: Manifest = initial ? { ...initial } : {};
  base.manifest_version = 2;
  if (typeof base.name !== "string") base.name = "";
  if (!Array.isArray(base.zones)) base.zones = [];
  if (!base.placement || typeof base.placement !== "object") base.placement = {};
  if (!base.layout_defaults || typeof base.layout_defaults !== "object") {
    base.layout_defaults = { spacing: "comfortable" };
  }
  if (!base.policy_overrides || typeof base.policy_overrides !== "object") {
    base.policy_overrides = { by_type: {} };
  }
  if (!base.global_styles || typeof base.global_styles !== "object") {
    base.global_styles = {};
  }
  return base;
}

function readByType(policyOverrides: unknown): Record<string, SectionPolicyRecord> {
  if (!policyOverrides || typeof policyOverrides !== "object") return {};
  if (!("by_type" in policyOverrides)) return {};
  const byType = policyOverrides.by_type;
  if (!byType || typeof byType !== "object") return {};
  return byType as Record<string, SectionPolicyRecord>;
}

interface GlobalStylesRecord {
  accent_color?: string | null;
  body_font?: string | null;
  heading_font?: string | null;
}

function readGlobalStyles(value: unknown): GlobalStylesRecord {
  if (!value || typeof value !== "object") return {};
  return value as GlobalStylesRecord;
}

function readZones(value: unknown): ZoneRecord[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (z): z is ZoneRecord => !!z && typeof z === "object" && "id" in z,
  );
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export default function TemplateWizard({
  initialManifest,
  onManifestChange,
  onComplete,
  onSave,
}: TemplateWizardProps) {
  const [step, setStep] = useState<StepName>("Basics");
  const [manifest, setManifest] = useState<Manifest>(() => cloneBase(initialManifest));
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const support = useSupportStore((s) => s.support);
  const ensureSupport = useSupportStore((s) => s.ensureLoaded);
  useEffect(() => {
    void ensureSupport();
  }, [ensureSupport]);

  useEffect(() => {
    onManifestChange?.(manifest);
  }, [manifest, onManifestChange]);

  const zones = useMemo(() => readZones(manifest.zones), [manifest.zones]);
  const byType = useMemo(() => readByType(manifest.policy_overrides), [manifest.policy_overrides]);
  const globalStyles = useMemo(
    () => readGlobalStyles(manifest.global_styles),
    [manifest.global_styles],
  );
  const currentSpacing = (manifest.layout_defaults as { spacing?: string } | undefined)?.spacing;
  const spacingToken: SpacingPreset =
    currentSpacing === "compact" || currentSpacing === "comfortable" || currentSpacing === "minimal"
      ? currentSpacing
      : "comfortable";

  const updateGlobalStyle = (key: "accent_color" | "body_font" | "heading_font", value: string | null) => {
    setManifest((prev) => {
      const styles: GlobalStylesRecord = { ...readGlobalStyles(prev.global_styles) };
      if (value === null || value === "") {
        delete styles[key];
      } else {
        styles[key] = value;
      }
      return { ...prev, global_styles: styles };
    });
  };

  const updateZoneStyle = (
    zoneId: string,
    key: "width" | "background" | "padding",
    value: string | null,
  ) => {
    setManifest((prev) => {
      const nextZones = (Array.isArray(prev.zones) ? prev.zones : []).map((z: unknown) => {
        if (!z || typeof z !== "object" || (z as { id?: unknown }).id !== zoneId) return z;
        const zone = z as Record<string, unknown>;
        const styles: Record<string, unknown> = {
          ...((zone.styles as Record<string, unknown> | undefined) ?? {}),
        };
        if (value === null || value === "") {
          delete styles[key];
        } else {
          styles[key] = value;
        }
        return { ...zone, styles };
      });
      return { ...prev, zones: nextZones };
    });
  };

  const updateLayoutSpacing = (spacing: SpacingPreset) => {
    setManifest((prev) => {
      const layout =
        prev.layout_defaults && typeof prev.layout_defaults === "object"
          ? (prev.layout_defaults as Record<string, unknown>)
          : {};
      return { ...prev, layout_defaults: { ...layout, spacing } };
    });
  };

  const updatePolicyForType = (type: string, partial: Partial<SectionPolicyRecord>) => {
    setManifest((prev) => {
      const current = readByType(prev.policy_overrides);
      const merged: SectionPolicyRecord = { ...current[type], ...partial };
      const cleaned: SectionPolicyRecord = {};
      if (merged.show_title !== undefined) cleaned.show_title = merged.show_title;
      if (merged.skill_variant !== undefined && merged.skill_variant !== null) {
        cleaned.skill_variant = merged.skill_variant;
      }
      const nextByType = { ...current, [type]: cleaned };
      return { ...prev, policy_overrides: { by_type: nextByType } };
    });
  };

  const updateField = (field: "name" | "description", value: string) => {
    setManifest((prev) => ({ ...prev, [field]: value || null }));
  };

  const handleSaveLocal = () => {
    const result = templateManifestSchema.safeParse(manifest);
    if (!result.success) {
      setValidationError(result.error.issues.map((i) => i.message).join("; "));
      return;
    }
    setValidationError(null);
    onSave?.(manifest);
  };

  const handleUseTemplate = async () => {
    const result = templateManifestSchema.safeParse(manifest);
    if (!result.success) {
      setValidationError(result.error.issues.map((i) => i.message).join("; "));
      return;
    }
    setValidationError(null);
    setIsSaving(true);
    try {
      await uploadUserTemplate({
        name: readString(manifest.name),
        description: readString(manifest.description) || undefined,
        manifest: manifest as Record<string, unknown>,
      });
      setSavedAt(new Date().toISOString());
      onComplete?.();
    } catch (e) {
      setValidationError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  const goNext = () => {
    const idx = STEPS.indexOf(step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1]);
  };
  const goPrev = () => {
    const idx = STEPS.indexOf(step);
    if (idx > 0) setStep(STEPS[idx - 1]);
  };

  return (
    <div className="space-y-4">
      <ol className="flex gap-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">
        {STEPS.map((name, idx) => (
          <li
            key={name}
            className={
              name === step
                ? "rounded bg-blue-100 px-2 py-1 text-blue-700"
                : "rounded bg-gray-100 px-2 py-1 text-gray-600"
            }
            data-testid={`wizard-step-${name.replace(/\s+/g, "-")}`}
          >
            {idx + 1}. {name}
          </li>
        ))}
      </ol>

      {step === "Basics" && (
        <section className="space-y-3" aria-label="Basics">
          <div>
            <label className="block text-xs font-medium text-gray-700" htmlFor="wizard-name">
              Name
            </label>
            <input
              id="wizard-name"
              type="text"
              value={readString(manifest.name)}
              onChange={(e) => updateField("name", e.target.value)}
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
              data-testid="wizard-name-input"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700" htmlFor="wizard-description">
              Description
            </label>
            <input
              id="wizard-description"
              type="text"
              value={readString(manifest.description)}
              onChange={(e) => updateField("description", e.target.value)}
              className="mt-1 w-full rounded border px-2 py-1 text-sm"
            />
          </div>
        </section>
      )}

      {step === "Layout" && (
        <section className="space-y-3" aria-label="Layout">
          <div>
            <span className="block text-xs font-medium text-gray-700">Spacing</span>
            <div className="mt-1 flex gap-3">
              {SPACING_OPTIONS.map((s) => (
                <label key={s} className="flex items-center gap-1 text-xs text-gray-700">
                  <input
                    type="radio"
                    name="wizard-spacing"
                    value={s}
                    checked={spacingToken === s}
                    onChange={() => updateLayoutSpacing(s)}
                    data-testid={`wizard-spacing-${s}`}
                  />
                  {s}
                </label>
              ))}
            </div>
          </div>

          <div>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Zones
            </h4>
            {zones.length === 0 && (
              <p className="text-xs text-gray-500">No zones defined.</p>
            )}
            <ul className="space-y-2">
              {zones.map((zone) => (
                <li key={zone.id} className="rounded border border-gray-100 p-2">
                  <details>
                    <summary className="cursor-pointer text-xs font-medium text-gray-700">
                      {zone.id}
                    </summary>
                    <div className="mt-2 space-y-2">
                      <div className="flex items-center gap-2">
                        <label
                          className="w-20 text-[11px] text-gray-600"
                          htmlFor={`wizard-zone-${zone.id}-width`}
                        >
                          Width
                        </label>
                        <select
                          id={`wizard-zone-${zone.id}-width`}
                          value={zone.styles?.width ?? ""}
                          onChange={(e) =>
                            updateZoneStyle(zone.id, "width", e.target.value || null)
                          }
                          data-testid={`wizard-zone-${zone.id}-width`}
                          className="flex-1 rounded border px-2 py-1 text-xs"
                        >
                          <option value="">Default</option>
                          {WIDTH_TOKENS.map((w) => (
                            <option key={w} value={w}>
                              {WIDTH_LABELS[w]}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="flex items-center gap-2">
                        <label
                          className="w-20 text-[11px] text-gray-600"
                          htmlFor={`wizard-zone-${zone.id}-padding`}
                        >
                          Padding
                        </label>
                        <select
                          id={`wizard-zone-${zone.id}-padding`}
                          value={zone.styles?.padding ?? ""}
                          onChange={(e) =>
                            updateZoneStyle(zone.id, "padding", e.target.value || null)
                          }
                          data-testid={`wizard-zone-${zone.id}-padding`}
                          className="flex-1 rounded border px-2 py-1 text-xs"
                        >
                          <option value="">Default</option>
                          {PADDING_TOKENS.map((p) => (
                            <option key={p} value={p}>
                              {PADDING_LABELS[p]}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="flex items-center gap-2">
                        <label
                          className="w-20 text-[11px] text-gray-600"
                          htmlFor={`wizard-zone-${zone.id}-background`}
                        >
                          Background
                        </label>
                        <select
                          id={`wizard-zone-${zone.id}-background`}
                          value={
                            zone.styles?.background?.startsWith("palette.")
                              ? zone.styles.background
                              : ""
                          }
                          onChange={(e) =>
                            updateZoneStyle(zone.id, "background", e.target.value || null)
                          }
                          data-testid={`wizard-zone-${zone.id}-background`}
                          className="flex-1 rounded border px-2 py-1 text-xs"
                        >
                          <option value="">Default</option>
                          {PALETTE_OPTIONS.map((p) => (
                            <option key={p.name} value={`palette.${p.name}`}>
                              {p.name} ({p.hex})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </details>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {step === "Global Styles" && (
        <section className="space-y-3" aria-label="Global styles">
          <div className="space-y-1">
            <span className="block text-xs font-medium text-gray-700">Accent color</span>
            <div className="flex items-center gap-2">
              <select
                value={
                  globalStyles.accent_color?.startsWith("palette.")
                    ? globalStyles.accent_color
                    : ""
                }
                onChange={(e) =>
                  updateGlobalStyle("accent_color", e.target.value || null)
                }
                data-testid="wizard-accent-palette"
                className="rounded border px-2 py-1 text-xs"
              >
                <option value="">Custom hex</option>
                {PALETTE_OPTIONS.map((p) => (
                  <option key={p.name} value={`palette.${p.name}`}>
                    {p.name} ({p.hex})
                  </option>
                ))}
              </select>
              <input
                type="color"
                value={
                  globalStyles.accent_color?.startsWith("#")
                    ? globalStyles.accent_color
                    : "#000000"
                }
                onChange={(e) => updateGlobalStyle("accent_color", e.target.value)}
              />
              <input
                type="text"
                value={globalStyles.accent_color ?? ""}
                onChange={(e) => updateGlobalStyle("accent_color", e.target.value || null)}
                placeholder="#aabbcc or palette.accent"
                data-testid="wizard-accent-input"
                className="flex-1 rounded border px-2 py-1 text-xs"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="w-28 text-xs font-medium text-gray-700" htmlFor="wizard-body">
              Body font
            </label>
            <select
              id="wizard-body"
              value={globalStyles.body_font ?? ""}
              onChange={(e) => updateGlobalStyle("body_font", e.target.value || null)}
              data-testid="wizard-body-font"
              className="flex-1 rounded border px-2 py-1 text-xs"
            >
              <option value="">Default</option>
              {FONT_TOKENS.map((f) => (
                <option key={f} value={f}>
                  {FONT_LABELS[f]}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="w-28 text-xs font-medium text-gray-700" htmlFor="wizard-heading">
              Heading font
            </label>
            <select
              id="wizard-heading"
              value={globalStyles.heading_font ?? ""}
              onChange={(e) => updateGlobalStyle("heading_font", e.target.value || null)}
              className="flex-1 rounded border px-2 py-1 text-xs"
            >
              <option value="">Default</option>
              {FONT_TOKENS.map((f) => (
                <option key={f} value={f}>
                  {FONT_LABELS[f]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Per-section policy
            </h4>
            <ul className="space-y-1">
              {SECTION_TYPES.map((type) => {
                const policy = byType[type] ?? {};
                const showTitle = policy.show_title ?? type !== "profile";
                return (
                  <li key={type} className="rounded border border-gray-100 p-2 text-xs text-gray-700">
                    <div className="flex items-center gap-2">
                      <span className="w-32 font-medium">{SECTION_LABELS[type]}</span>
                      <label className="flex items-center gap-1">
                        <input
                          type="checkbox"
                          checked={showTitle}
                          onChange={(e) => updatePolicyForType(type, { show_title: e.target.checked })}
                          data-testid={`wizard-show-title-${type}`}
                        />
                        Show title
                      </label>
                      {type === "skills" && support?.feature_skills_inline !== "NONE" && (
                        <>
                          <BestEffortBadge field="feature_skills_inline" />
                          <select
                            value={policy.skill_variant ?? ""}
                            onChange={(e) =>
                              updatePolicyForType(type, {
                                skill_variant: (e.target.value || null) as
                                  | "block"
                                  | "inline"
                                  | null,
                              })
                            }
                            className="rounded border px-1 py-0.5 text-[11px]"
                          >
                            <option value="">Default (block)</option>
                            <option value="block">block</option>
                            <option value="inline">inline</option>
                          </select>
                        </>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      )}

      {step === "Review" && (
        <section className="space-y-3" aria-label="Review">
          <pre
            data-testid="wizard-manifest-json"
            className="max-h-72 overflow-auto rounded border border-gray-100 bg-gray-50 p-2 text-[10px] text-gray-700"
          >
            {JSON.stringify(manifest, null, 2)}
          </pre>
          {validationError && (
            <p className="text-xs text-red-600" data-testid="wizard-validation-error">
              {validationError}
            </p>
          )}
          {savedAt && (
            <p className="flex items-center gap-1 text-xs text-green-700">
              <Check className="h-3.5 w-3.5" /> Saved
            </p>
          )}
        </section>
      )}

      <div className="flex items-center justify-between pt-2">
        <button
          onClick={goPrev}
          disabled={step === STEPS[0]}
          className="rounded border px-3 py-1 text-xs text-gray-600 disabled:opacity-40"
        >
          Back
        </button>
        {step !== "Review" ? (
          <button
            onClick={goNext}
            className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
          >
            Next
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={handleSaveLocal}
              className="rounded border border-gray-300 px-3 py-1 text-xs text-gray-700 hover:bg-gray-50"
              data-testid="wizard-save-template"
            >
              Save template
            </button>
            <button
              onClick={handleUseTemplate}
              disabled={isSaving}
              className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              data-testid="wizard-use-template"
            >
              {isSaving ? "Saving..." : "Use this template"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
