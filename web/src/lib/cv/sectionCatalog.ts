/** Pure section catalog and default-data factories used by editor surfaces. */

import type { SectionInstance } from "./schema";

export const SECTION_LABELS: Record<string, string> = {
  profile: "Profile",
  experience: "Experience",
  education: "Education",
  skills: "Skills",
  projects: "Projects",
  languages: "Languages",
  certifications: "Certifications",
  research: "Research",
  extras: "Extras",
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
  "extras",
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
        summary: [],
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
          description: [],
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
          summary: [],
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
          description: [],
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
    case "extras":
      return [
        {
          id: generateInstanceId(),
          title: "New Section",
          fields: [],
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
