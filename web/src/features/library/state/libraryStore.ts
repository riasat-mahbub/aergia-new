import { create } from "zustand";
import * as libraryApi from "@/features/library/api/library";
import type { LibraryEntry, LibraryEntryKind } from "@/features/library/types";

interface LibraryState {
  entries: LibraryEntry[];
  isLoading: boolean;
  loaded: boolean;
  error: string | null;

  fetchAll: () => Promise<void>;
  create: (
    kind: LibraryEntryKind,
    payload: Array<Record<string, unknown>>,
  ) => Promise<LibraryEntry>;
  update: (id: string, payload: Array<Record<string, unknown>>) => Promise<LibraryEntry>;
  remove: (id: string) => Promise<void>;
}
export const useLibraryStore = create<LibraryState>((set) => ({
  entries: [],
  isLoading: false,
  loaded: false,
  error: null,

  fetchAll: async () => {
    set({ isLoading: true, error: null });
    try {
      const entries = await libraryApi.listLibrary();
      set({ entries, isLoading: false, loaded: true, error: null });
    } catch {
      set({
        isLoading: false,
        loaded: true,
        error: "Unable to load the library. Please try again.",
      });
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
    return updated;
  },

  remove: async (id) => {
    await libraryApi.deleteLibrary(id);
    set((s) => ({ entries: s.entries.filter((e) => e.id !== id) }));
  },

}));
