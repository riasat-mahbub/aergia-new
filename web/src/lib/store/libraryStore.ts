import { create } from "zustand";
import * as libraryApi from "../api/library";
import type { LibraryEntry, LibraryEntryKind } from "../api/library";

// ─── Selectors ──────────────────────────────────────────────────────
//
// `selectByKind` is a pure helper that buckets entries by their kind.
// Exported as a free function so tests and components can call it
// directly without subscribing to the store.

export function selectByKind(entries: LibraryEntry[]): Record<LibraryEntryKind, LibraryEntry[]> {
  const buckets: Record<LibraryEntryKind, LibraryEntry[]> = {
    experience: [],
    education: [],
    skill: [],
    project: [],
    certification: [],
    language: [],
  };
  for (const e of entries) {
    buckets[e.kind].push(e);
  }
  return buckets;
}

export function countByKind(entries: LibraryEntry[]): Record<LibraryEntryKind, number> {
  const buckets = selectByKind(entries);
  const out = {} as Record<LibraryEntryKind, number>;
  (Object.keys(buckets) as LibraryEntryKind[]).forEach((k) => {
    out[k] = buckets[k].length;
  });
  return out;
}

// ─── Store ──────────────────────────────────────────────────────────

interface LibraryState {
  entries: LibraryEntry[];
  isLoading: boolean;
  loaded: boolean;

  fetchAll: () => Promise<void>;
  create: (
    kind: LibraryEntryKind,
    payload: Array<Record<string, unknown>>,
  ) => Promise<LibraryEntry>;
  update: (id: string, payload: Array<Record<string, unknown>>) => Promise<void>;
  remove: (id: string) => Promise<void>;
  cloneToSection: (id: string) => Promise<LibraryEntry>;
}
export const useLibraryStore = create<LibraryState>((set) => ({
  entries: [],
  isLoading: false,
  loaded: false,

  fetchAll: async () => {
    set({ isLoading: true });
    try {
      const entries = await libraryApi.listLibrary();
      set({ entries, isLoading: false, loaded: true });
    } catch {
      set({ isLoading: false, loaded: true });
    }
  },

  create: async (kind, payload) => {
    const entry = await libraryApi.createLibrary(kind, payload);
    set((s) => ({ entries: [...s.entries, entry] }));
    return entry;
  },

  update: async (id, payload) => {
    const updated = await libraryApi.updateLibrary(id, payload);
    set((s) => ({
      entries: s.entries.map((e) => (e.id === id ? updated : e)),
    }));
  },

  remove: async (id) => {
    await libraryApi.deleteLibrary(id);
    set((s) => ({ entries: s.entries.filter((e) => e.id !== id) }));
  },

  cloneToSection: async (id) => {
    // cloneToSection on the API returns the full SectionInstance payload,
    // not a LibraryEntry. The caller (LibraryPicker) is responsible for
    // inserting the result into the CV store. This method returns the
    // raw response; see libraryApi.cloneLibrary for the full shape.
    return (await libraryApi.cloneLibrary(id)) as unknown as LibraryEntry;
  },
}));

// ─── Re-export the API surface for components that prefer the store
// namespace over importing `lib/api/library` directly. ───────────────

export const libraryApiMethods = libraryApi;
