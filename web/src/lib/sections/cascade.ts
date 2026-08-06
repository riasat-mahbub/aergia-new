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
  LayoutHints,
  SectionInstanceStyle,
  SubsectionStyle,
} from "../../generated/schema";
import {
  defaultLayoutFor,
  defaultPolicyFor,
  defaultSubsectionFor,
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

/** Layered section-instance style. The instance carries three axes; each
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
    policy: { ...defaultPolicyFor(instanceType), ...(s.policy ?? {}) },
  };
}

/** True when the section's effective value differs from the inherited
 * value. Used by the override pill and revert affordance. */
export function isOverridden<T>(effective: T, inherited: T): boolean {
  return JSON.stringify(effective) !== JSON.stringify(inherited);
}

/** Strip a section-instance override back to "inherit from document".
 * Returns a new style object (does not mutate). The caller is
 * responsible for writing the result.
 *
 * The schema permits the three axis keys; the cast to
 * `SectionInstanceStyle` lives at the helper boundary because the
 * deletion needs an untyped map and the resulting object is the same
 * shape the schema accepts. */
export function withoutOverride(
  style: SectionInstanceStyle | null | undefined,
  axis: "subsection" | "layout" | "policy",
): SectionInstanceStyle {
  const s = style ?? {};
  const next: Record<string, unknown> = { ...s };
  delete next[axis];
  return next as unknown as SectionInstanceStyle;
}
