import type {
  SectionInstanceStyle,
  TextStyle,
  TypographyRole,
} from "@/shared/cv/schema";

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
