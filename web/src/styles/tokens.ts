/**
 * TypeScript mirror of the CSS token system in tokens.css. Use these
 * constants when you need a numeric value in code (gap indicator widths,
 * computed radii, etc.). The CSS variables are the runtime source of
 * truth; this file exists for typed access and a single edit point.
 */

export const spacing = {
  s1: 4,
  s2: 8,
  s3: 12,
  s4: 16,
  s5: 20,
  s6: 24,
  s8: 32,
  s10: 40,
  s12: 48,
} as const;

export const radius = {
  r1: 4,
  r2: 6,
  r3: 8,
  pill: 999,
} as const;

export const typeScale = {
  xs: 11,
  sm: 12,
  base: 13,
  md: 14,
  lg: 16,
  xl: 20,
  "2xl": 28,
} as const;

export const weight = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

export const fonts = {
  prose: "var(--font-prose)",
  ui: "var(--font-ui)",
  mono: "var(--font-mono)",
} as const;

export const surfaces = {
  paper: "var(--paper)",
  paper1: "var(--paper-1)",
  paper2: "var(--paper-2)",
} as const;

export const ink = {
  ink: "var(--ink)",
  ink2: "var(--ink-2)",
  ink3: "var(--ink-3)",
  ink4: "var(--ink-4)",
} as const;

export const rules = {
  rule: "var(--rule)",
  ruleSoft: "var(--rule-soft)",
  ruleStrong: "var(--rule-strong)",
} as const;

export const accent = {
  accent: "var(--accent)",
  accentSoft: "var(--accent-soft)",
} as const;

/** Font tokens — what the panel offers for body and heading font.
 * Mirrors the FontToken Literal in api/app/schema/models.py.
 */
export const FONT_TOKENS = ["sans-serif", "serif", "mono", "display"] as const;
export type FontToken = (typeof FONT_TOKENS)[number];

/** Human-readable labels for font tokens. */
export const FONT_TOKEN_LABELS: Record<FontToken, string> = {
  "sans-serif": "Sans serif",
  serif: "Serif",
  mono: "Monospace",
  display: "Display",
};

/** Section spacing tokens (above, below, between entries). */
export const SECTION_SPACING_TOKENS = ["none", "tight", "comfortable", "loose", "spacious"] as const;
export type SectionSpacingToken = (typeof SECTION_SPACING_TOKENS)[number];

export const SECTION_SPACING_LABELS: Record<SectionSpacingToken, string> = {
  none: "None",
  tight: "Tight",
  comfortable: "Comfortable",
  loose: "Loose",
  spacious: "Spacious",
};

/** Maps a section spacing token to its CSS px value for the live gap
 * indicator in the inspector. Mirrors tokens.py PADDING_TOKEN_VALUES.
 */
export const SECTION_SPACING_PX: Record<SectionSpacingToken, number> = {
  none: 0,
  tight: 12,
  comfortable: 24,
  loose: 32,
  spacious: 32,
};

/** Per-element font size tokens — what the typography row offers.
 * User-language labels, not the schema enum keys.
 */
export const FONT_SIZE_TOKENS = ["xs", "small", "normal", "large", "xl"] as const;
export type FontSizeToken = (typeof FONT_SIZE_TOKENS)[number];

export const FONT_SIZE_LABELS: Record<FontSizeToken, string> = {
  xs: "Tiny",
  small: "Small",
  normal: "Normal",
  large: "Large",
  xl: "Huge",
};

/** Resolved CSS values for font sizes (matches _FONT_SIZE_TO_CSS in
 * api/app/services/renderer/html.py).
 */
export const FONT_SIZE_CSS: Record<FontSizeToken, string> = {
  xs: "0.75rem",
  small: "0.875rem",
  normal: "1rem",
  large: "1.125rem",
  xl: "1.25rem",
};
