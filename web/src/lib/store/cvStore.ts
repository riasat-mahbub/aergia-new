import { create } from "zustand";
import * as cvsApi from "../api/cvs";
import type { SectionInstance } from "../sections/types";
import { createDefaultInstance } from "../sections/types";

interface CVState {
  cvList: cvsApi.CVListItem[];
  currentCV: cvsApi.CVDetail | null;
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: Date | null;

  fetchCVs: () => Promise<void>;
  createCV: (title: string, template_id?: string) => Promise<cvsApi.CVDetail>;
  deleteCV: (id: string) => Promise<void>;
  copyCV: (id: string) => Promise<void>;
  loadCV: (id: string) => Promise<void>;
  setIsSaving: (saving: boolean) => void;
  setLastSaved: (date: Date) => void;
  patchCurrentCV: (data: Partial<cvsApi.CVDetail>) => void;
}

export const useCVStore = create<CVState>((set, get) => ({
  cvList: [],
  currentCV: null,
  isLoading: false,
  isSaving: false,
  lastSaved: null,

  fetchCVs: async () => {
    set({ isLoading: true });
    try {
      const cvList = await cvsApi.fetchCVs();
      set({ cvList, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createCV: async (title: string, template_id?: string) => {
    const cv = await cvsApi.createCV({ title, template_id });
    await get().fetchCVs();
    return cv;
  },

  deleteCV: async (id: string) => {
    await cvsApi.deleteCV(id);
    await get().fetchCVs();
  },

  copyCV: async (id: string) => {
    await cvsApi.copyCV(id);
    await get().fetchCVs();
  },

  loadCV: async (id: string) => {
    set({ isLoading: true });
    try {
      const currentCV = await cvsApi.fetchCV(id);
      set({ currentCV, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  setIsSaving: (saving: boolean) => set({ isSaving: saving }),

  setLastSaved: (date: Date) => set({ lastSaved: date }),

  patchCurrentCV: (data: Partial<cvsApi.CVDetail>) => {
    const current = get().currentCV;
    if (current) {
      set({ currentCV: { ...current, ...data } });
    }
  },
}));
