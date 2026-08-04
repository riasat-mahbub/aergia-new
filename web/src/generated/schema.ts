// This file is generated. Do not edit by hand.
// Source: api/app/schema/models.py (sha256:3cb4537a95a76f5e)

export interface CVLayout {
  "placement"?: Record<string, string>;
  "zones"?: Array<Zone>;
}

export interface CVRow {
  "zones": Array<string>;
}

export interface Customizations {
  "accent_color"?: (string) | null;
  "body_font"?: (("sans-serif" | "serif" | "mono" | "display")) | null;
  "default_text_align"?: (("left" | "right" | "center" | "justify")) | null;
  "flags"?: Record<string, boolean>;
  "heading_font"?: (("sans-serif" | "serif" | "mono" | "display")) | null;
  "layout"?: (CVLayout) | null;
  "per_section"?: Record<string, SectionInstanceStyle>;
  "spacing"?: (("compact" | "comfortable" | "minimal")) | null;
}

export interface DateStyle {
  "key"?: string;
  "rangeSep"?: string;
}

export interface Document {
  "sections": Array<Section>;
}

export interface Entry {
  "fields": Array<FieldBlock>;
  "id": string;
}

export interface FieldBlock {
  "align"?: (string) | null;
  "group"?: (string) | null;
  "icon"?: (string) | null;
  "key": string;
  "runs": Array<TextRun>;
}

export interface GlobalStyles {
  "accent_color"?: (string) | null;
  "body_font"?: (("sans-serif" | "serif" | "mono" | "display")) | null;
  "heading_font"?: (("sans-serif" | "serif" | "mono" | "display")) | null;
}

export interface LayoutDefaults {
  "spacing"?: ("compact" | "comfortable" | "minimal");
}

export interface LayoutHints {
  "break_before"?: boolean;
  "chip_keys"?: (Array<string>) | null;
  "date_style"?: (DateStyle) | null;
  "font_family"?: (string) | null;
  "heading_keeps_with_first"?: boolean;
  "keep_together"?: boolean;
  "orphans"?: number;
  "widows"?: number;
}

export interface PolicyOverrides {
  "by_type"?: Record<string, SectionPolicy>;
}

export interface RenderModel {
  "body_font": string;
  "css_vars": Record<string, string>;
  "heading_font": string;
  "link_styles": string;
  "print_styles": string;
  "sections": Record<string, Section>;
  "zones": Array<ResolvedZone>;
}

export interface ResolvedZone {
  "id": string;
  "section_ids": Array<string>;
  "styles": Record<string, string>;
}

export interface Section {
  "enabled"?: boolean;
  "entries"?: Array<Entry>;
  "fields"?: Array<FieldBlock>;
  "id": string;
  "layout"?: (LayoutHints) | null;
  "policy"?: (SectionPolicy) | null;
  "subsection"?: (SubsectionStyle) | null;
  "title": string;
  "type": string;
}

export interface SectionInstance {
  "data"?: Array<unknown> | Record<string, unknown>;
  "enabled"?: boolean;
  "id": string;
  "style"?: (SectionInstanceStyle) | null;
  "title": string;
  "type": string;
}

export interface SectionInstanceStyle {
  "layout"?: (LayoutHints) | null;
  "policy"?: (SectionPolicy) | null;
  "subsection"?: (SubsectionStyle) | null;
  "text"?: Record<string, TextStyle>;
}

export interface SectionPolicy {
  "show_title"?: boolean;
  "skill_variant"?: (("block" | "inline")) | null;
}

export interface SubsectionStyle {
  "background_color"?: (string) | null;
  "section_color"?: (string) | null;
  "spacing_after"?: (string) | null;
  "spacing_before"?: (string) | null;
  "text_align"?: (("left" | "right" | "center" | "justify")) | null;
}

export interface TemplateDetail {
  "description": (string) | null;
  "id": string;
  "manifest"?: (Record<string, unknown>) | null;
  "name": string;
  "preview_image_url": (string) | null;
}

export interface TemplateListItem {
  "description": (string) | null;
  "id": string;
  "name": string;
  "preview_image_url": (string) | null;
}

export interface TemplateManifest {
  "description"?: (string) | null;
  "global_styles"?: GlobalStyles;
  "layout_defaults"?: LayoutDefaults;
  "manifest_version"?: number;
  "name": string;
  "placement"?: Record<string, string>;
  "policy_overrides"?: PolicyOverrides;
  "zones"?: Array<Zone>;
}

export interface TextRun {
  "style"?: (TextStyle) | null;
  "text": string;
}

export interface TextStyle {
  "bold"?: boolean;
  "color"?: (string) | null;
  "font_size"?: (("xs" | "small" | "normal" | "large" | "xl")) | null;
  "italic"?: boolean;
  "link"?: (string) | null;
  "strike"?: boolean;
  "underline"?: boolean;
}

export interface Zone {
  "id": string;
  "label"?: (string) | null;
  "styles"?: ZoneStyle;
}

export interface ZoneStyle {
  "background"?: (string) | null;
  "padding"?: (("none" | "tight" | "comfortable" | "loose" | "spacious")) | null;
  "width"?: (("narrow" | "half" | "full" | "auto")) | null;
}
