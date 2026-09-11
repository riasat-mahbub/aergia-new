import type {
  SectionInstanceStyle,
  TextStyle,
  TypographyRole,
} from "@/shared/cv/schema";
import { FONT_TOKENS, SECTION_SPACING_TOKENS } from "@/styles/tokens";
import type { SectionSpacingToken } from "@/styles/tokens";

export function cleanStyle(style: SectionInstanceStyle): SectionInstanceStyle {
  const next = { ...style } as Record<string, unknown>;
  for (const key of ["subsection", "layout", "typography", "policy", "text"]) {
    const value = next[key];
    if (value && typeof value === "object" && Object.keys(value as object).length === 0) delete next[key];
  }
  return next as SectionInstanceStyle;
}

export function updateAxis<K extends "subsection" | "layout" | "policy">(
  style: SectionInstanceStyle,
  axis: K,
  partial: Partial<NonNullable<SectionInstanceStyle[K]>>,
): SectionInstanceStyle {
  const current = { ...((style[axis] ?? {}) as object), ...partial } as Record<string, unknown>;
  for (const [key, value] of Object.entries(current)) {
    if (value === null || value === undefined || value === "") delete current[key];
  }
  return cleanStyle({ ...style, [axis]: current });
}

export function updateTypographyAxis(
  style: SectionInstanceStyle,
  role: "heading" | "body",
  partial: Partial<TypographyRole>,
): SectionInstanceStyle {
  const typography: { heading?: TypographyRole | null; body?: TypographyRole | null } = {
    ...(style.typography ?? {}),
  };
  const current: Record<string, unknown> = { ...(typography[role] ?? {}) };
  for (const [key, value] of Object.entries(partial)) {
    if (value === null || value === undefined || value === "") delete current[key];
    else current[key] = value;
  }
  if (Object.keys(current).length === 0) delete typography[role];
  else typography[role] = current as TypographyRole;
  return cleanStyle({ ...style, typography });
}

export function updateTextStyle(
  style: SectionInstanceStyle,
  key: string,
  value: TextStyle | undefined,
): SectionInstanceStyle {
  const next = { ...(style.text ?? {}) };
  if (value === undefined || Object.keys(value).length === 0) delete next[key];
  else next[key] = value;
  return cleanStyle({ ...style, text: next });
}

export function fontTokenFromLegacyValue(value: string | null | undefined): string | null {
  if (!value) return null;
  if ((FONT_TOKENS as readonly string[]).includes(value)) return value;
  if (/mono|monospace/i.test(value)) return "mono";
  if (/Georgia|Crimson|serif/i.test(value)) return "serif";
  if (/Inter|system-ui|sans-serif/i.test(value)) return "sans-serif";
  return null;
}

export function spacingTokenToSpacingToken(raw: string | null | undefined): SectionSpacingToken | null {
  if (!raw) return null;
  if ((SECTION_SPACING_TOKENS as readonly string[]).includes(raw)) {
    return raw as SectionSpacingToken;
  }
  const px = parseInt(raw);
  if (Number.isNaN(px)) return null;
  if (px <= 6) return "none";
  if (px <= 18) return "tight";
  if (px <= 28) return "comfortable";
  if (px <= 34) return "loose";
  return "spacious";
}
