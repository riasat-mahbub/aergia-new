import { create } from "zustand";
import * as cvsApi from "@/features/cvs";
import type { CVDetail } from "@/features/cvs";

export interface BuilderDocumentState {
  currentCV: CVDetail | null;
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: Date | null;

  loadCV: (id: string) => Promise<void>;
  setIsSaving: (saving: boolean) => void;
  setLastSaved: (date: Date) => void;
}

/** Builder-only document and persistence status. It is never shared with dashboard list views. */
export const useBuilderDocumentStore = create<BuilderDocumentState>((set) => ({
  currentCV: null,
  isLoading: false,
  isSaving: false,
  lastSaved: null,

  loadCV: async (id) => {
    set({ isLoading: true, currentCV: null, isSaving: false, lastSaved: null });
    try {
      const currentCV = await cvsApi.fetchCV(id);
      set({ currentCV, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  setIsSaving: (saving) => set({ isSaving: saving }),
  setLastSaved: (date) => set({ lastSaved: date }),
}));
