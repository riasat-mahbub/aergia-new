import client from "./client";
import type {
  AddEntryToLibraryData,
  AddEntryToLibraryResponse,
  LibraryCloneResponse,
  LibraryEntry,
  LibraryEntryKind,
  PromoteToLibraryResponse,
} from "@/contracts/library";

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
