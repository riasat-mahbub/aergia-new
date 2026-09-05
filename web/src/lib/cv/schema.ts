/**
 * Type-only facade for the generated CV/document schema.
 *
 * `generated/schema.ts` remains the source of truth. This module exists so
 * consumers do not need to know where codegen output lives, while all
 * hand-written editor/domain behavior stays in separate modules.
 */

import type {
  Customizations,
  DateStyle,
  Document,
  Entry,
  FieldBlock,
  GlobalStyles,
  LayoutDefaults,
  LayoutHints,
  PolicyOverrides,
  RenderModel,
  ResolvedZone,
  RichTextBlock,
  RichTextItem,
  Section,
  SectionInstance as GeneratedSectionInstance,
  SectionInstanceStyle as GeneratedSectionInstanceStyle,
  SectionPolicy,
  SubsectionStyle,
  TemplateDetail,
  TemplateListItem,
  TemplateManifest,
  TextRun,
  TextStyle,
  Zone,
  ZoneStyle,
} from "../../generated/schema";

/**
 * The wire style accepts legacy keys while older persisted documents are
 * normalized by the backend. Keep that compatibility at this type boundary;
 * new code should use the generated four-axis fields.
 */
export type SectionInstanceStyle = GeneratedSectionInstanceStyle & {
  [key: string]: unknown;
};

/** Generated section instance with the compatibility style boundary applied. */
export type SectionInstance = Omit<GeneratedSectionInstance, "style"> & {
  style?: SectionInstanceStyle | null;
};

export type {
  Customizations,
  DateStyle,
  Document,
  Entry,
  FieldBlock,
  GlobalStyles,
  LayoutDefaults,
  LayoutHints,
  PolicyOverrides,
  RenderModel,
  ResolvedZone,
  RichTextBlock,
  RichTextItem,
  Section,
  SectionPolicy,
  SubsectionStyle,
  TemplateDetail,
  TemplateListItem,
  TemplateManifest,
  TextRun,
  TextStyle,
  Zone,
  ZoneStyle,
};
