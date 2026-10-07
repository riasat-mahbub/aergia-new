/**
 * Cascade helpers — what the resolver does server-side, mirrored
 * client-side so the inspector can show effective values and detect
 * overrides.
 *
 * Why this exists: the resolver merges template → document → per-section
 * into a single resolved style. The current panel reads the *override*
 * and shows unchecked checkboxes when the user hasn't touched a field
 * but the schema default is True (keep_together, heading_keeps_with_first).
 * These helpers compute the effective value from the override plus the
 * schema defaults so the inspector never lies about state.
 */

import type {
  Customizations,
  LayoutHints,
  SectionInstanceStyle,
  SectionTypography,
  SubsectionStyle,
  TemplateManifest,
} from "@/shared/cv/schema";
import { SECTION_SPACING_PX } from "@/styles/tokens";
import type { SectionSpacingToken } from "@/styles/tokens";
import {
  defaultLayoutFor,
  defaultPolicyFor,
  defaultSubsectionFor,
  defaultTypographyFor,
} from "./styleDefaults";

/** Layered subsections: type-default → instance override. */
export function effectiveSubsection(
  instanceType: string,
  override: SubsectionStyle | null | undefined,
): SubsectionStyle {
  return { ...defaultSubsectionFor(instanceType), ...(override ?? {}) };
}

/** Layered layout: type-default → instance override. */
export function effectiveLayout(
  instanceType: string,
  override: LayoutHints | null | undefined,
): LayoutHints {
  return { ...defaultLayoutFor(instanceType), ...(override ?? {}) };
}

export function effectiveTypography(
  instanceType: string,
  override: SectionTypography | null | undefined,
): SectionTypography {
  return { ...defaultTypographyFor(instanceType), ...(override ?? {}) };
}

/** Layered section-instance style. The instance carries local axes; each
 * axis layers over the type default. */
export function effectiveStyle(
  instanceType: string,
  style: SectionInstanceStyle | null | undefined,
): SectionInstanceStyle {
  const s = style ?? {};
  return {
    text: s.text ?? {},
    subsection: effectiveSubsection(instanceType, s.subsection),
    layout: effectiveLayout(instanceType, s.layout),
    typography: effectiveTypography(instanceType, s.typography),
    policy: { ...defaultPolicyFor(instanceType), ...(s.policy ?? {}) },
  };
}

/** True when the section's effective value differs from the inherited
 * value. Used by the override pill and revert affordance. */
export function isOverridden<T>(effective: T, inherited: T): boolean {
  return JSON.stringify(effective) !== JSON.stringify(inherited);
}

export interface InheritedGapHint {
  source: "Template default" | "Document spacing" | "Default";
  pixels: number;
}

/** Resolve the inherited entry or field gap shown by the inspector. This
 * mirrors the render resolver's precedence without writing values to a
 * section instance: document spacing owns the gap when selected, otherwise
 * the manifest's dedicated token wins over its legacy layout preset. */
export function inheritedGapHint(
  manifest: TemplateManifest | null | undefined,
  customizations: Customizations,
  axis: "entry_gap" | "field_gap",
): InheritedGapHint {
  const documentSpacing = customizations.spacing;
  const layoutDefaults = manifest?.layout_defaults;
  const preset = documentSpacing ?? layoutDefaults?.spacing ?? "none";
  const token = documentSpacing == null ? layoutDefaults?.[axis] : null;
  const presetGapPixels: Record<NonNullable<NonNullable<TemplateManifest["layout_defaults"]>["spacing"]>, number> = {
    none: 0,
    compact: 0,
    comfortable: 16,
    minimal: 0,
  };

  return {
    source: documentSpacing != null
      ? "Document spacing"
      : manifest
        ? "Template default"
        : "Default",
    pixels: token != null
      ? SECTION_SPACING_PX[token as SectionSpacingToken]
      : presetGapPixels[preset],
  };
}

/** Strip a section-instance override back to "inherit from document".
 * Returns a new style object (does not mutate). The caller is
 * responsible for writing the result.
 *
 * The schema permits the local axis keys; the cast to
 * `SectionInstanceStyle` lives at the helper boundary because the
 * deletion needs an untyped map and the resulting object is the same
 * shape the schema accepts. */
export function withoutOverride(
  style: SectionInstanceStyle | null | undefined,
  axis: "subsection" | "layout" | "typography" | "policy",
): SectionInstanceStyle {
  const s = style ?? {};
  const next: Record<string, unknown> = { ...s };
  delete next[axis];
  return next as unknown as SectionInstanceStyle;
}
