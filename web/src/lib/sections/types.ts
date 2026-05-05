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
  assignedSections?: string[];
  row?: number; // zones with same row share 100% width horizontally; different rows stack vertically
}

export interface AssetItem {
  id: string;
  name: string;
  data: string;
  type: "image" | "other";
}

export interface LayoutConfig {
  zones: Zone[];
  placement: Record<string, string>;
  rowHeights?: Record<number, string>; // row number → height% string, e.g. { 0: "60%", 1: "40%" }
}

export function getDefaultInstances(): SectionInstance[] {
  return [createDefaultInstance("profile")];
}
