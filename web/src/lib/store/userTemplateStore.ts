import { create } from "zustand";
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
  /**
   * Legacy HTML upload path. Kept for the template-selector modal's
   * file-upload affordance: the user drops an .html file and we POST a
   * minimal v2 manifest wrapping it.
   */
  uploadTemplate: (name: string, htmlContent: string) => Promise<void>;
  createTemplate: (data: templatesApi.UserTemplateCreate) => Promise<void>;
  deleteTemplate: (id: string) => Promise<void>;
  getTemplateById: (id: string) => UserTemplate | undefined;
}

function htmlToManifest(htmlContent: string): Record<string, unknown> {
  return {
    manifest_version: 2,
    name: "HTML upload",
    zones: [{ id: "main", styles: { width: "100%" } }],
    placement: {
      profile: "main",
      experience: "main",
      education: "main",
      skills: "main",
      projects: "main",
      languages: "main",
      certifications: "main",
      research: "main",
    },
    layout_defaults: { spacing: "comfortable" },
    policy_overrides: { by_type: {} },
    global_styles: {},
    layout_template: htmlContent,
  } as Record<string, unknown>;
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

    uploadTemplate: async (name: string, htmlContent: string) => {
      set({ isLoading: true, error: null });
      try {
        const manifest = htmlToManifest(htmlContent);
        const newTemplate = await templatesApi.uploadUserTemplate({ name, manifest });
        set({ templates: [...get().templates, newTemplate] });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : "Failed to upload template" });
        throw error;
      } finally {
        set({ isLoading: false });
      }
    },

    createTemplate: async (data) => {
      set({ isLoading: true, error: null });
      try {
        const newTemplate = await templatesApi.uploadUserTemplate(data);
        set({ templates: [...get().templates, newTemplate] });
      } catch (error) {
        set({ error: error instanceof Error ? error.message : "Failed to create template" });
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
