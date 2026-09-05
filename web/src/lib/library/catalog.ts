import type { LibraryEntryKind } from "@/contracts/library";
import type { SectionType } from "@/lib/cv/sectionCatalog";

/** Pure library/editor vocabulary shared by views and API adapters. */
export const LIBRARY_KIND_TO_SECTION_TYPE: Record<LibraryEntryKind, SectionType> = {
  experience: "experience",
  education: "education",
  skill: "skills",
  project: "projects",
  certification: "certifications",
  language: "languages",
  research: "research",
};

export const SECTION_TYPE_TO_LIBRARY_KIND: Partial<Record<SectionType, LibraryEntryKind>> = {
  experience: "experience",
  education: "education",
  skills: "skill",
  projects: "project",
  certifications: "certification",
  languages: "language",
  research: "research",
};

export function sectionTypeForLibraryKind(kind: LibraryEntryKind): SectionType {
  return LIBRARY_KIND_TO_SECTION_TYPE[kind];
}

export function libraryKindForSectionType(sectionType: string): LibraryEntryKind | undefined {
  return SECTION_TYPE_TO_LIBRARY_KIND[sectionType as SectionType];
}

export function isLibraryKind(kind: string): kind is LibraryEntryKind {
  return (LIBRARY_KINDS as readonly string[]).includes(kind);
}

export const LIBRARY_KIND_LABELS: Record<LibraryEntryKind, string> = {
  experience: "Experiences",
  education: "Education",
  skill: "Skills",
  project: "Projects",
  certification: "Certifications",
  language: "Languages",
  research: "Research",
};

export const LIBRARY_KINDS: readonly LibraryEntryKind[] = [
  "experience",
  "education",
  "skill",
  "project",
  "certification",
  "language",
  "research",
];
