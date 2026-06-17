import type { SocialIconKey } from "./socialIcons";

export interface SocialLink {
  /** User-defined visible text. */
  label: string;
  /** Absolute URL the link points to. Normalized via `normalize_url_scheme` on the backend. */
  url: string;
  /** One of the 13 keys in `socialIcons.tsx`. */
  icon: SocialIconKey;
}

export interface ProfileData {
  name: string;
  title: string;
  email: string;
  email_link: boolean;
  phone: string;
  location: string;
  site_text: string;
  site_url: string;
  summary: string;
  photo_url: string;
  social_links: SocialLink[];
}

export interface ExperienceEntry {
  id: string;
  company: string;
  position: string;
  start_date: string;
  end_date: string | null;
  current: boolean;
  location: string;
  description: string;
}

export interface EducationEntry {
  id: string;
  institution: string;
  degree: string;
  start_date: string;
  end_date: string | null;
  current: boolean;
  gpa: string;
  summary: string;
}

export interface SkillGroup {
  id: string;
  category: string;
  items: string[];
}

export interface ProjectEntry {
  id: string;
  name: string;
  url: string;
  link_text: string;
  start_date: string;
  end_date: string | null;
  description: string;
  tech_stack: string[];
}
export interface LanguageEntry {
  id: string;
  language: string;
  proficiency: string;
}

export interface CertificationEntry {
  id: string;
  name: string;
  issuer: string;
  date: string;
  credential_url: string;
}

export interface ResearchEntry {
  id: string;
  title: string;
  paper_url: string;
  paper_link_text: string;
  description: string;
  publication_date: string;
  publication_value: string;
}


export interface FieldStyle {
  font?: string;
  size?: string;
  weight?: string;
}

export type DateStyleKey =
  | "YYYY-MM"
  | "YYYY/MM"
  | "MM/YYYY"
  | "MM-YYYY"
  | "MM.YYYY"
  | "YYYY.MM"
  | "Mon YYYY"
  | "Month YYYY"
  | "YYYY"
  | "Mon-YYYY";

export interface DateStyle {
  /** One of the 10 preset keys in `DATE_STYLE_OPTIONS` (web/src/lib/sections/DateField.tsx). */
  key: DateStyleKey;
  /** Separator used when joining two formatted dates into a range. */
  rangeSep: string;
}

export interface SectionStyle {
  font?: string;
  color?: string;
  weight?: string;
  text_align?: "left" | "right" | "center" | "justify";
  field_styles?: Record<string, FieldStyle>;
  /** Whether the section heading renders; undefined uses the section default. */
  show_title?: boolean;
  /**
   * Per-section layout variant. Currently only meaningful for the `skills`
   * section type, where `block` is the default and `inline` renders the
   * category and its items on one line as plain text.
   */
  layout?: "block" | "inline";
  /**
   * Per-section date display format. Only meaningful for sections that
   * include date fields (experience, education, projects, certifications,
   * research). Undefined leaves the default `YYYY-MM` rendering.
   */
  date_style?: DateStyle;
  /**
   * Per-section gap between entries inside multi-entry sections (experience,
   * education, projects, skills, certifications, research, languages).
   * Accepts any CSS length string; the UI clamps to 0–24 px. Undefined
   * falls through to the template's `--subsection-gap` CSS var.
   */
  subsection_gap?: string;
  /**
   * Per-section gap between rows inside the Profile section (name, title,
   * contact, social links, summary). Accepts any CSS length string; the UI
   * clamps to 0–24 px. Undefined falls through to the template's `--row-gap`
   * CSS var.
   */
  row_gap?: string;
}

export interface SectionInstance {
  id: string;
  type: string;
  title: string;
  enabled: boolean;
  data: any;
  style?: SectionStyle;
}

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

export function createDefaultSectionData(type: string): any {
  switch (type) {
    case "profile":
      return { name: "", title: "", email: "", email_link: true, phone: "", location: "", site_text: "", site_url: "", summary: "", photo_url: "", social_links: [] };
    case "experience":
      return [{ id: generateInstanceId(), company: "", position: "", start_date: "", end_date: null, current: false, location: "", description: "" }];
    case "education":
      return [{ id: generateInstanceId(), institution: "", degree: "", start_date: "", end_date: null, current: false, gpa: "", summary: "" }];
    case "skills":
      return [{ id: generateInstanceId(), category: "", items: [] }];
    case "projects":
      return [{ id: generateInstanceId(), name: "", url: "", link_text: "", start_date: "", end_date: null, description: "", tech_stack: [] }];
    case "languages":
      return [{ id: generateInstanceId(), language: "", proficiency: "Intermediate" }];
    case "certifications":
      return [{ id: generateInstanceId(), name: "", issuer: "", date: "", credential_url: "" }];
    case "research":
      return [{
        id: generateInstanceId(),
        title: "",
        paper_url: "",
        paper_link_text: "",
        description: "",
        publication_date: "",
        publication_value: "",
      }];
    default:
      return {};
  }
}
export function generateInstanceId(): string {
  return `sec_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createDefaultInstance(type: string): SectionInstance {
  return {
    id: generateInstanceId(),
    type,
    title: SECTION_LABELS[type] || type,
    enabled: true,
    data: createDefaultSectionData(type),
  };
}

export interface Zone {
  id: string;
  label?: string;
  styles?: Record<string, string>;
  /** Legacy field kept on disk for backward-compat with stored JSON. Not read by the layout. */
  assignedSections?: string[];
}

export interface AssetItem {
  id: string;
  name: string;
  data: string;
  type: "image" | "other";
}

export interface LayoutConfig {
  zones: Zone[];
  /** Maps section instanceId → zoneId (per-instance placement). Falls back to type→zoneId for old CVs. */
  placement: Record<string, string>;
}

export function getFirstZoneId(layout: LayoutConfig | null | undefined): string | undefined {
  return layout?.zones?.[0]?.id;
}

export function getDefaultInstances(): SectionInstance[] {
  return [createDefaultInstance("profile")];
}

/** Detect if a placement map is in old format (type→zoneId) vs new (instanceId→zoneId). */
function isTypeBasedPlacement(placement: Record<string, string>): boolean {
  const keys = Object.keys(placement);
  if (keys.length === 0) return false;
  return keys.some((k) => !k.startsWith("sec_"));
}

/** Convert old type-based placement to instance-based placement. */
export function migratePlacement(
  layoutConfig: LayoutConfig,
  instances: SectionInstance[],
): LayoutConfig {
  if (!isTypeBasedPlacement(layoutConfig.placement)) return layoutConfig;
  const oldPlacement = layoutConfig.placement;
  const newPlacement: Record<string, string> = {};
  for (const inst of instances) {
    const zoneId = oldPlacement[inst.type];
    if (zoneId) newPlacement[inst.id] = zoneId;
  }
  return { ...layoutConfig, placement: newPlacement };
}
