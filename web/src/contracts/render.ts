export type SupportLevelValue = "FULL" | "BEST_EFFORT" | "NONE";

/** Feature-to-renderer capability levels returned by the render support API. */
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
