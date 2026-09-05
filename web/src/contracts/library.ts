import type { SectionType } from "@/lib/cv/sectionCatalog";
import type { SectionInstance } from "@/lib/cv/schema";

export type LibraryEntryKind =
  | "experience"
  | "education"
  | "skill"
  | "project"
  | "certification"
  | "language"
  | "research";

export interface LibraryEntry {
  id: string;
  kind: LibraryEntryKind;
  payload: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
}

export interface LibraryCloneResponse {
  section_instance: SectionInstance & { type: SectionType };
}

export interface PromoteToLibraryResponse {
  library_id: string;
  promoted: Record<string, number>;
  skipped: string[];
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
