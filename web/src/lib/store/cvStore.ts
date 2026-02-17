import { create } from "zustand";
import * as cvsApi from "../api/cvs";

interface CVState {
  cvList: cvsApi.CVListItem[];
  currentCV: cvsApi.CVDetail | null;
  isLoading: boolean;

  fetchCVs: () => Promise<void>;
  createCV: (title: string, template_id?: string) => Promise<cvsApi.CVDetail>;
  deleteCV: (id: string) => Promise<void>;
  copyCV: (id: string) => Promise<void>;
  loadCV: (id: string) => Promise<void>;
}

export const useCVStore = create<CVState>((set, get) => ({
  cvList: [],
  currentCV: null,
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
    const currentCV = await cvsApi.fetchCV(id);
    set({ currentCV });
  },
}));
