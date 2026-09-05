import type { SectionType } from "@/lib/cv/types";

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

export interface AddEntryToLibraryResponse {
  library_id: string;
  entry_id: string | null;
  created: boolean;
}

export interface AddEntryToLibraryData {
  kind: LibraryEntryKind;
  entry: Record<string, unknown>;
}
