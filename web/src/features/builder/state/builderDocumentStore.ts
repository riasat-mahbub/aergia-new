import { create } from "zustand";
import * as cvsApi from "@/features/cvs";
import type { CVDetail } from "@/features/cvs";

export interface BuilderDocumentState {
  currentCV: CVDetail | null;
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  error: string | null;

  loadCV: (id: string) => Promise<void>;
  setIsSaving: (saving: boolean) => void;
  setLastSaved: (date: Date) => void;
}

/** Builder-only document and persistence status. It is never shared with dashboard list views. */
export const useBuilderDocumentStore = create<BuilderDocumentState>((set) => {
  let loadGeneration = 0;

  return {
    currentCV: null,
    isLoading: false,
    isSaving: false,
    lastSaved: null,
    error: null,

    loadCV: async (id) => {
      const generation = ++loadGeneration;
      set({ isLoading: true, currentCV: null, isSaving: false, lastSaved: null, error: null });
      try {
        const currentCV = await cvsApi.fetchCV(id);
        if (generation !== loadGeneration) return;
        if (currentCV.id !== id) {
          set({ isLoading: false, error: "Unable to load this CV. Please try again." });
          return;
        }
        set({ currentCV, isLoading: false, error: null });
      } catch {
        if (generation !== loadGeneration) return;
        set({ isLoading: false, error: "Unable to load this CV. Please try again." });
      }
    },

    setIsSaving: (saving) => set({ isSaving: saving }),
    setLastSaved: (date) => set({ lastSaved: date }),
  };
});
