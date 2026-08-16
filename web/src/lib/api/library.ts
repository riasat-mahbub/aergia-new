import client from "./client";

// ─── Library types ──────────────────────────────────────────────────
//
// LibraryEntryKind + LibraryEntryResponse are declared here as plain TS
// types rather than imported from `../generated/schema` because the
// codegen script only scans `app.schema.models`. The HTTP wire shapes
// live in `app.schemas.library` and are not picked up by design
// (per Phase A2 / plan assumption A8).
//
// If/when the codegen script is extended to scan `app.schemas.*`,
// these declarations can be replaced with imports from the generated
// file.

import type { SectionType } from "../sections/types";

export type LibraryEntryKind =
  | "experience"
  | "education"
  | "skill"
  | "project"
  | "certification"
  | "language"
  | "research";

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

export interface LibraryEntry {
  id: string;
  kind: LibraryEntryKind;
  payload: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
}

export interface LibraryCloneResponse {
  section_instance: {
    id: string;
    type: SectionType;
    title: string;
    enabled: boolean;
    data: unknown;
    style: unknown;
  };
}

export interface PromoteToLibraryResponse {
  library_id: string;
  promoted: Record<string, number>;
  skipped: string[];
}

// ─── API surface ────────────────────────────────────────────────────

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

export interface AddEntryToLibraryResponse {
  library_id: string;
  entry_id: string | null;
  created: boolean;
}

export interface AddEntryToLibraryData {
  kind: LibraryEntryKind;
  entry: Record<string, unknown>;
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
