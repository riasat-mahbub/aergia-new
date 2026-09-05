import type { SectionInstanceStyle } from "@/shared/cv/schema";

/**
 * A style object carries a meaningful user pick iff at least one of its
 * three axes (including per-field typography) is set.
 */
export function sectionStyleHasValues(style: SectionInstanceStyle): boolean {
  return Boolean(
    (style.layout && Object.keys(style.layout).length > 0) ||
      (style.subsection && Object.keys(style.subsection).length > 0) ||
      (style.policy && Object.keys(style.policy).length > 0) ||
      (style.text && Object.keys(style.text).length > 0),
  );
}
