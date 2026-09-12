/** Concrete editor data shapes layered on top of the generated wire AST. */

import type { RichTextBlock } from "./schema";

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
  summary?: string | RichTextBlock[];
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
  description?: string | RichTextBlock[];
}

export interface EducationEntry {
  id: string;
  institution?: string;
  degree?: string;
  start_date?: string;
  end_date?: string | null;
  current?: boolean;
  gpa?: string;
  summary?: string | RichTextBlock[];
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
  description?: string | RichTextBlock[];
  tech_stack?: string[];
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
  link_text?: string;
}

export interface ResearchEntry {
  id: string;
  title?: string;
  paper_url?: string;
  paper_link_text?: string;
  description?: string | RichTextBlock[];
  publication_date?: string;
  publication_value?: string;
}
