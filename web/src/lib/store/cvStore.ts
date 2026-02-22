import { create } from "zustand";
import * as cvsApi from "../api/cvs";
import type { SectionInstance } from "../sections/types";
import { createDefaultInstance, getDefaultInstances } from "../sections/types";

interface CVState {
  cvList: cvsApi.CVListItem[];
  currentCV: cvsApi.CVDetail | null;
  isLoading: boolean;

  fetchCVs: () => Promise<void>;
  createCV: (title: string, template_id?: string) => Promise<cvsApi.CVDetail>;
  deleteCV: (id: string) => Promise<void>;
  copyCV: (id: string) => Promise<void>;
  loadCV: (id: string) => Promise<void>;

  addInstance: (type: string) => Promise<void>;
  removeInstance: (id: string) => Promise<void>;
  reorderInstances: (ids: string[]) => Promise<void>;
  toggleInstance: (id: string) => Promise<void>;
  renameInstance: (id: string, title: string) => Promise<void>;
  updateInstanceData: (id: string, data: any) => Promise<void>;
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

  addInstance: async (type: string) => {
    const { currentCV, loadCV } = get();
    if (!currentCV?.id) return;
    const instances: SectionInstance[] = (currentCV.sections as SectionInstance[]) || [];
    const updated = [...instances, createDefaultInstance(type)];
    await cvsApi.updateCV(currentCV.id, { sections: updated });
    await loadCV(currentCV.id);
  },

  removeInstance: async (id: string) => {
    const { currentCV, loadCV } = get();
    if (!currentCV?.id) return;
    const instances: SectionInstance[] = (currentCV.sections as SectionInstance[]) || [];
    const updated = instances.filter((i) => i.id !== id);
    await cvsApi.updateCV(currentCV.id, { sections: updated });
    await loadCV(currentCV.id);
  },

  reorderInstances: async (ids: string[]) => {
    const { currentCV, loadCV } = get();
    if (!currentCV?.id) return;
    const instances: SectionInstance[] = (currentCV.sections as SectionInstance[]) || [];
    const reordered = ids.map((itemId) => instances.find((i) => i.id === itemId)).filter(Boolean) as SectionInstance[];
    await cvsApi.updateCV(currentCV.id, { sections: reordered });
    await loadCV(currentCV.id);
  },

  toggleInstance: async (id: string) => {
    const { currentCV, loadCV } = get();
    if (!currentCV?.id) return;
    const instances: SectionInstance[] = (currentCV.sections as SectionInstance[]) || [];
    const updated = instances.map((i) =>
      i.id === id ? { ...i, enabled: !i.enabled } : i
    );
    await cvsApi.updateCV(currentCV.id, { sections: updated });
    await loadCV(currentCV.id);
  },

  renameInstance: async (id: string, title: string) => {
    const { currentCV, loadCV } = get();
    if (!currentCV?.id) return;
    const instances: SectionInstance[] = (currentCV.sections as SectionInstance[]) || [];
    const updated = instances.map((i) =>
      i.id === id ? { ...i, title } : i
    );
    await cvsApi.updateCV(currentCV.id, { sections: updated });
    await loadCV(currentCV.id);
  },

  updateInstanceData: async (id: string, data: any) => {
    const { currentCV, loadCV } = get();
    if (!currentCV?.id) return;
    const instances: SectionInstance[] = (currentCV.sections as SectionInstance[]) || [];
    const updated = instances.map((i) =>
      i.id === id ? { ...i, data } : i
    );
    await cvsApi.updateCV(currentCV.id, { sections: updated });
    await loadCV(currentCV.id);
  },
}));
