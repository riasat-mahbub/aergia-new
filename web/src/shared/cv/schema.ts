/**
 * Type-only facade for the generated CV/document schema.
 *
 * `generated/schema.ts` remains the source of truth. This module exists so
 * consumers do not need to know where codegen output lives, while all
 * hand-written editor/domain behavior stays in separate modules.
 */

import type {
  CVLayout,
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
  SectionTypography,
  SubsectionStyle,
  TemplateDetail,
  TemplateListItem,
  TemplateManifest,
  TextRun,
  TextStyle,
  TypographyRole,
  Zone,
  ZoneStyle,
} from "../../generated/schema";

/** Canonical generated style shape used by the editor and API. */
export type SectionInstanceStyle = GeneratedSectionInstanceStyle;

/** Canonical generated section instance. */
export type SectionInstance = GeneratedSectionInstance;

export type {
  CVLayout,
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
  SectionTypography,
  SubsectionStyle,
  TemplateDetail,
  TemplateListItem,
  TemplateManifest,
  TextRun,
  TextStyle,
  TypographyRole,
  Zone,
  ZoneStyle,
};
