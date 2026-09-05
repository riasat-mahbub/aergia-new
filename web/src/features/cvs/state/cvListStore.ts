import { create } from "zustand";
import * as cvsApi from "@/features/cvs/api/cvs";
import type { CVDetail, CVListItem, CVSections } from "@/features/cvs/types";

export interface CVListState {
  cvList: CVListItem[];
  isLoading: boolean;

  fetchCVs: () => Promise<void>;
  createCV: (title: string, template_id?: string, sections?: CVSections) => Promise<CVDetail>;
  deleteCV: (id: string) => Promise<void>;
  copyCV: (id: string) => Promise<void>;
}

/** Dashboard-owned list state. Builder document state lives with the builder route. */
export const useCVListStore = create<CVListState>((set, get) => ({
  cvList: [],
  isLoading: false,

  fetchCVs: async () => {
    set({ isLoading: true });
    try {
      const cvList = await cvsApi.fetchCVs();
      set({ cvList, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createCV: async (title, template_id, sections) => {
    const cv = await cvsApi.createCV({
      title,
      template_id,
      ...(sections !== undefined ? { sections } : {}),
    });
    await get().fetchCVs();
    return cv;
  },

  deleteCV: async (id) => {
    await cvsApi.deleteCV(id);
    await get().fetchCVs();
  },

  copyCV: async (id) => {
    await cvsApi.copyCV(id);
    await get().fetchCVs();
  },
}));
