/**
 * TypeScript mirror of the schema defaults in
 * api/app/schema/models.py + api/app/services/renderer/policy.py.
 *
 * The inspector uses these so checkboxes and inputs show the *effective*
 * value — `override ?? default` — instead of `undefined` when the user
 * hasn't touched the field. Without this, "keep_together" shows
 * unchecked even though the schema applies True, which makes the panel
 * lie about state.
 *
 * Drift risk: every change to the Python defaults must be mirrored
 * here. The companion test (styleDefaults.test.ts) walks both shapes
 * and asserts equality for every key, so drift fails the suite.
 *
 * Why every field is populated explicitly: the generated TypeScript
 * shape marks all Pydantic fields as optional (`?:`). Defaults are
 * applied at validation time, not at the type level. The cascade
 * helper spreads the type default first, then the override, so the
 * effective value is correct only when the default is fully populated.
 */

import type {
  LayoutHints,
  SectionInstanceStyle,
  SectionPolicy,
  SubsectionStyle,
  TextStyle,
} from "../../generated/schema";

/** Per-section-type policy defaults. Mirrors SECTION_POLICIES in
 * api/app/services/renderer/policy.py. */
export const SECTION_POLICY_DEFAULTS: Record<string, SectionPolicy> = {
  profile: { show_title: false, heading_divider: false, skill_variant: null, entry_layout: "stack" },
  experience: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "stack" },
  education: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "stack" },
  skills: { show_title: true, heading_divider: false, skill_variant: "block", entry_layout: "stack" },
  projects: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "two-column" },
  languages: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "stack" },
  certifications: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "two-column" },
  research: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "two-column" },
  extras: { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "stack" },
};

/** Per-section-type subsection defaults. Mirrors
 * builders/_default_subsection — profile gets centered text alignment,
 * everything else starts empty. */
export const SUBSECTION_DEFAULTS: Record<string, SubsectionStyle> = {
  profile: { text_align: "center", spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  experience: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  education: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  skills: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  projects: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  languages: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  certifications: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  research: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
  extras: { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null },
};

/** Per-section-type layout defaults. Mirrors builders/_default_layout
 * + LayoutHints defaults. Projects gets chip_keys=["tech"]; everything
 * else has keep_together / heading_keeps_with_first = True (the
 * schema's page-flow defaults). */
export const LAYOUT_DEFAULTS: Record<string, LayoutHints> = {
  profile: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  experience: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  education: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  skills: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  projects: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: ["tech"] },
  languages: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  certifications: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  research: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
  extras: { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null },
};

/** Field-level defaults applied per TextRun. Mirrors TextStyle in
 * models.py: every bool starts False, color/size null. The renderer
 * only emits a declaration when a field is truthy. */
export const TEXT_STYLE_DEFAULTS: TextStyle = {
  bold: false,
  italic: false,
  underline: false,
  strike: false,
  color: null,
  link: null,
  font_size: null,
};

/** Returns the type-level policy for a section, or a sane default if
 * the type is unknown. Use this in the inspector instead of
 * `selectedStyle.policy ?? {}` so the effective value is correct. */
export function defaultPolicyFor(sectionType: string): SectionPolicy {
  return SECTION_POLICY_DEFAULTS[sectionType] ?? { show_title: true, heading_divider: false, skill_variant: null, entry_layout: "stack" };
}

export function defaultSubsectionFor(sectionType: string): SubsectionStyle {
  return SUBSECTION_DEFAULTS[sectionType] ?? { text_align: null, spacing_before: null, spacing_after: null, background_color: null, section_color: null };
}

export function defaultLayoutFor(sectionType: string): LayoutHints {
  return LAYOUT_DEFAULTS[sectionType] ?? { font_family: null, date_style: null, break_before: false, keep_together: true, heading_keeps_with_first: true, orphans: 2, widows: 2, chip_keys: null };
}

/** SectionInstanceStyle defaults — what every axis looks like when the
 * user has never touched the section. Used as the "no override"
 * baseline. */
export function defaultStyleFor(sectionType: string): SectionInstanceStyle {
  return {
    text: {},
    subsection: defaultSubsectionFor(sectionType),
    layout: defaultLayoutFor(sectionType),
    policy: defaultPolicyFor(sectionType),
  };
}
