/** Section types — re-exported from the codegen output.

The shape of every wire SectionInstance is now defined in
``api/app/schema/models.py`` and the TypeScript declarations are derived
from it via ``api/scripts/codegen_schema.py``. This file owns only the
domain helpers (id generation, defaults, label maps, placement migration)
and the legacy aliases that downstream code still references.
*/

import type {
  Customizations,
  DateStyle,
  Document,
  Entry,
  FieldBlock,
  LayoutDefaults,
  LayoutHints,
  PolicyOverrides,
  RenderModel,
  ResolvedZone,
  Section,
  SectionInstance,
  SectionInstanceStyle as GeneratedSectionInstanceStyle,
  SectionPolicy,
  SubsectionStyle,
  TemplateManifest,
  TextRun,
  TextStyle,
  Zone,
  ZoneStyle,
} from "../../generated/schema";

/** The wire SectionInstance style is open to legacy keys too — the backend
 * builder normalises the legacy shape (font, color, weight, …) into the
 * three axes. The index signature lets tests and the customize panel keep
 * emitting the legacy keys without TS errors.
 */
export type SectionInstanceStyle = GeneratedSectionInstanceStyle & {
  [key: string]: unknown;
};

export type {
  Customizations,
  DateStyle,
  Document,
  Entry,
  FieldBlock,
  LayoutDefaults,
  LayoutHints,
  PolicyOverrides,
  RenderModel,
  ResolvedZone,
  Section,
  SectionInstance,
  SectionPolicy,
  SubsectionStyle,
  TemplateManifest,
  TextRun,
  TextStyle,
  Zone,
  ZoneStyle,
};

// ---------------------------------------------------------------------------
// Legacy aliases — kept for downstream code that still references the old
// entry interfaces and the legacy style / layout types.
// ---------------------------------------------------------------------------

export interface SectionStyle {
  font?: string;
  color?: string;
  weight?: string;
  text_align?: "left" | "right" | "center" | "justify";
  field_styles?: Record<string, FieldStyle>;
  show_title?: boolean;
  layout?: "block" | "inline";
  date_style?: { key?: string; rangeSep: string };
  subsection_gap?: string;
  row_gap?: string;
  [key: string]: unknown;
}

export interface LayoutConfig {
  zones: Zone[];
  placement: Record<string, string>;
  manifest_version?: 2;
  name?: string;
  description?: string | null;
  layout_defaults?: LayoutDefaults;
  policy_overrides?: PolicyOverrides;
  global_styles?: Record<string, string>;
}

export interface LegacyZone {
  id: string;
  label?: string | null;
  styles?: Record<string, string>;
  assignedSections?: string[];
}

export interface SocialLink {
  label: string;
  url: string;
  icon: string;
}

export interface ProfileData {
  name?: string;
  title?: string;
  email?: string;
  email_link?: boolean;
  phone?: string;
  location?: string;
  site_text?: string;
  site_url?: string;
  summary?: string;
  photo_url?: string;
  social_links: SocialLink[];
}

export interface ExperienceEntry {
  id: string;
  company?: string;
  position?: string;
  start_date?: string;
  end_date?: string | null;
  current?: boolean;
  location?: string;
  description?: string;
}

export interface EducationEntry {
  id: string;
  institution?: string;
  degree?: string;
  start_date?: string;
  end_date?: string | null;
  current?: boolean;
  gpa?: string;
  summary?: string;
}

export interface SkillGroup {
  id: string;
  category?: string;
  items: string[];
}

export interface ProjectEntry {
  id: string;
  name?: string;
  url?: string;
  link_text?: string;
  start_date?: string;
  end_date?: string | null;
  description?: string;
  tech_stack: string[];
}

export interface LanguageEntry {
  id: string;
  language?: string;
  proficiency?: string;
}

export interface CertificationEntry {
  id: string;
  name?: string;
  issuer?: string;
  date?: string;
  credential_url?: string;
}

export interface ResearchEntry {
  id: string;
  title?: string;
  paper_url?: string;
  paper_link_text?: string;
  description?: string;
  publication_date?: string;
  publication_value?: string;
}

export interface FieldStyle {
  font?: string;
  size?: string;
  weight?: string;
}

export type DateStyleKey = DateStyle["key"];

export interface AssetItem {
  id: string;
  name: string;
  data: string;
  type: "image" | "other";
}

// ---------------------------------------------------------------------------
// Domain helpers
// ---------------------------------------------------------------------------

export const SECTION_LABELS: Record<string, string> = {
  profile: "Profile",
  experience: "Experience",
  education: "Education",
  skills: "Skills",
  projects: "Projects",
  languages: "Languages",
  certifications: "Certifications",
  research: "Research",
};

export const SECTION_TYPES = [
  "profile",
  "experience",
  "education",
  "skills",
  "projects",
  "languages",
  "certifications",
  "research",
] as const;

export type SectionType = (typeof SECTION_TYPES)[number];

export function generateInstanceId(): string {
  return `sec_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createDefaultSectionData(type: string): unknown {
  switch (type) {
    case "profile":
      return {
        name: "",
        title: "",
        email: "",
        email_link: true,
        phone: "",
        location: "",
        site_text: "",
        site_url: "",
        summary: "",
        photo_url: "",
        social_links: [],
      };
    case "experience":
      return [
        {
          id: generateInstanceId(),
          company: "",
          position: "",
          start_date: "",
          end_date: null,
          current: false,
          location: "",
          description: "",
        },
      ];
    case "education":
      return [
        {
          id: generateInstanceId(),
          institution: "",
          degree: "",
          start_date: "",
          end_date: null,
          current: false,
          gpa: "",
          summary: "",
        },
      ];
    case "skills":
      return [{ id: generateInstanceId(), category: "", items: [] }];
    case "projects":
      return [
        {
          id: generateInstanceId(),
          name: "",
          url: "",
          link_text: "",
          start_date: "",
          end_date: null,
          description: "",
          tech_stack: [],
        },
      ];
    case "languages":
      return [
        {
          id: generateInstanceId(),
          language: "",
          proficiency: "Intermediate",
        },
      ];
    case "certifications":
      return [
        {
          id: generateInstanceId(),
          name: "",
          issuer: "",
          date: "",
          credential_url: "",
        },
      ];
    case "research":
      return [
        {
          id: generateInstanceId(),
          title: "",
          paper_url: "",
          paper_link_text: "",
          description: "",
          publication_date: "",
          publication_value: "",
        },
      ];
    default:
      return {};
  }
}

export function createDefaultInstance(type: string): SectionInstance {
  return {
    id: generateInstanceId(),
    type,
    title: SECTION_LABELS[type] || type,
    enabled: true,
    data: createDefaultSectionData(type) as SectionInstance["data"],
  };
}

export function getDefaultInstances(): SectionInstance[] {
  return [createDefaultInstance("profile")];
}

/** Manifest placement is keyed by section type, not instance id. */
export function getFirstZoneId(
  manifest: TemplateManifest | LayoutConfig | null | undefined,
): string | undefined {
  return manifest?.zones?.[0]?.id;
}

// ---------------------------------------------------------------------------
// Placement migration — converts old type-keyed placement to instance-keyed.
// ---------------------------------------------------------------------------

function isTypeBasedPlacement(placement: Record<string, string>): boolean {
  const keys = Object.keys(placement);
  if (keys.length === 0) return false;
  return keys.some((k) => !k.startsWith("sec_"));
}

export function migratePlacement(
  manifest: TemplateManifest | LayoutConfig | null | undefined,
  instances: SectionInstance[],
): TemplateManifest | LayoutConfig | null | undefined {
  if (!manifest) return manifest;
  const placement = manifest.placement || {};
  if (!isTypeBasedPlacement(placement)) return manifest;
  const newPlacement: Record<string, string> = {};
  for (const inst of instances) {
    const zoneId = placement[inst.type];
    if (zoneId) newPlacement[inst.id] = zoneId;
  }
  return { ...manifest, placement: newPlacement };
}
