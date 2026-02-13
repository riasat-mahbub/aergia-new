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

export interface SectionData {
  profile?: ProfileData;
  experience?: ExperienceEntry[];
  education?: EducationEntry[];
  skills?: SkillGroup[];
  projects?: ProjectEntry[];
  languages?: LanguageEntry[];
  certifications?: CertificationEntry[];
}

export interface CVSections {
  order: string[];
  enabled: string[];
  data: SectionData;
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

export const DEFAULT_SECTION_ORDER = [
  "profile",
  "experience",
  "education",
  "skills",
  "projects",
  "languages",
  "certifications",
];

export const DEFAULT_ENABLED = [
  "profile",
  "experience",
  "education",
  "skills",
  "projects",
];
