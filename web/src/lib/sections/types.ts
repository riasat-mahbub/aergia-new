export interface ProfileData {
  name: string;
  title: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  photo_url: string;
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

export interface SectionStyle {
  font?: string;
  color?: string;
  weight?: string;
  text_align?: "left" | "right" | "center" | "justify";
  /**
   * Whether the section's heading (e.g. "PROFILE", "EXPERIENCE") renders in
   * the live preview and PDF. `undefined` falls back to the per-section
   * default (profile hides its heading; everything else shows it).
   */
  show_title?: boolean;
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
};

export const SECTION_TYPES = [
  "profile",
  "experience",
  "education",
  "skills",
  "projects",
  "languages",
  "certifications",
] as const;

export function createDefaultSectionData(type: string): any {
  switch (type) {
    case "profile":
      return { name: "", title: "", email: "", phone: "", location: "", summary: "", photo_url: "" };
    case "experience":
      return [];
    case "education":
      return [];
    case "skills":
      return [];
    case "projects":
      return [];
    case "languages":
      return [];
    case "certifications":
      return [];
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
