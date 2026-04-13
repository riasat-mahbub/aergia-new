import { create } from "zustand";
import { persist, PersistOptions } from "zustand/middleware";
import * as templatesApi from "../api/templates";

interface UserTemplate {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
  layout_config: Record<string, any>;
  section_schema: Record<string, any>;
  default_customizations: Record<string, any> | null;
  content: string;
  is_user_template: boolean;
  is_system: boolean;
  user_id: string | null;
  created_at: string;
}

interface UserTemplateStore {
  templates: UserTemplate[];
  isLoading: boolean;
  error: string | null;
  
  fetchUserTemplates: () => Promise<void>;
    uploadTemplate: (name: string, layout_template: string, layout_config?: Record<string, unknown>) => Promise<void>;
  deleteTemplate: (id: string) => Promise<void>;
  getTemplateById: (id: string) => UserTemplate | undefined;
}

const useUserTemplateStore = create<UserTemplateStore>()(
  (set, get) => ({
    templates: [],
    isLoading: false,
    error: null,
    
    fetchUserTemplates: async () => {
      set({ isLoading: true, error: null });
      try {
        const templates = await templatesApi.fetchUserTemplates();
        set({ templates });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : "Failed to fetch templates" });
      } finally {
        set({ isLoading: false });
      }
    },
    
    uploadTemplate: async (name: string, layout_template: string, layout_config?: Record<string, unknown>) => {
      set({ isLoading: true, error: null });
      try {
        const newTemplate = await templatesApi.uploadUserTemplate({ name, layout_template, layout_config });
        set({ templates: [...get().templates, newTemplate] });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : "Failed to upload template" });
        throw error;
      } finally {
        set({ isLoading: false });
      }
    },
    
    deleteTemplate: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        await templatesApi.deleteUserTemplate(id);
        set({ templates: get().templates.filter(t => t.id !== id) });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : "Failed to delete template" });
        throw error;
      } finally {
        set({ isLoading: false });
      }
    },
    
    getTemplateById: (id: string) => {
      return get().templates.find(t => t.id === id);
    },
  })
);

export default useUserTemplateStore;