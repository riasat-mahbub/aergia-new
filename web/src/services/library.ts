import client from "./client";
import type { SectionType } from "@/lib/sections/types";
import type {
  AddEntryToLibraryData,
  AddEntryToLibraryResponse,
  LibraryCloneResponse,
  LibraryEntry,
  LibraryEntryKind,
  PromoteToLibraryResponse,
} from "@/contracts/library";

// Runtime mappings belong to the library domain service because they are
// used to translate API kinds into editor section types.
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

export const LIBRARY_KINDS: LibraryEntryKind[] = [
  "experience",
  "education",
  "skill",
  "project",
  "certification",
  "language",
  "research",
];

export async function listLibrary(kind?: LibraryEntryKind): Promise<LibraryEntry[]> {
  const { data } = await client.get("/library", { params: kind ? { kind } : {} });
  return data;
}

export async function createLibrary(
  kind: LibraryEntryKind,
  payload: Array<Record<string, unknown>>,
): Promise<LibraryEntry> {
  const { data } = await client.post("/library", { kind, payload });
  return data;
}

export async function updateLibrary(
  id: string,
  payload: Array<Record<string, unknown>>,
): Promise<LibraryEntry> {
  const { data } = await client.patch(`/library/${id}`, { payload });
  return data;
}

export async function deleteLibrary(id: string): Promise<void> {
  await client.delete(`/library/${id}`);
}

export async function cloneLibrary(id: string): Promise<LibraryCloneResponse> {
  const { data } = await client.post(`/library/${id}/clone`);
  return data;
}

export async function promoteCvToLibrary(cvId: string): Promise<PromoteToLibraryResponse> {
  const { data } = await client.post(`/cvs/${cvId}/promote-to-library`);
  return data;
}

export async function addEntryToLibrary(
  cvId: string,
  sectionId: string,
  entryId: string,
  payload: AddEntryToLibraryData,
): Promise<AddEntryToLibraryResponse> {
  const { data } = await client.post(
    `/cvs/${cvId}/sections/${sectionId}/entries/${entryId}/add-to-library`,
    payload,
  );
  return data;
}
