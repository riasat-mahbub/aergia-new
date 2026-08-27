import client from "./client";

export type SupportLevelValue = "FULL" | "BEST_EFFORT" | "NONE";

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
  keep_entry_together: SupportLevelValue;
  feature_skills_inline: SupportLevelValue;
  feature_section_underline: SupportLevelValue;
  feature_anchor_styling: SupportLevelValue;
}



export async function fetchRendererSupport(): Promise<SupportMap> {
  const { data } = await client.get("/render/support");
  return data as SupportMap;
}
