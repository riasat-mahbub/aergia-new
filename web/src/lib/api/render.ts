import client from "./client";

export const SUPPORT_VALUES = ["FULL", "BEST_EFFORT", "NONE"] as const;
export type SupportLevelValue = (typeof SUPPORT_VALUES)[number];

/**
 * Feature → renderer-capability level. Codegen-derived names listed below;
 * if a future renderer adds new fields, list them here too. The runtime
 * shape is permissive (`Record<string, SupportLevelValue>`); the typed
 * view is just documentation.
 */
export interface SupportMap {
  break_before: SupportLevelValue;
  keep_with_next: SupportLevelValue;
  keep_together: SupportLevelValue;
  heading_keeps_with_first: SupportLevelValue;
  feature_skills_inline: SupportLevelValue;
  feature_section_underline: SupportLevelValue;
  feature_anchor_styling: SupportLevelValue;
}

export type SupportField = keyof SupportMap;

/**
 * `RendererSupport` is declared on the backend as a Python @dataclass and
 * is not part of the codegen output (which only carries Pydantic models).
 * The shape below mirrors `api/app/services/renderer/support.py`. The
 * runtime endpoint returns the dataclass field-by-field as JSON.
 */
export type RendererSupport = SupportMap;

export async function fetchRendererSupport(): Promise<SupportMap> {
  const { data } = await client.get("/render/support");
  return data as SupportMap;
}
