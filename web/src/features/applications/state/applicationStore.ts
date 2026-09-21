import { create } from "zustand";
import * as applicationApi from "@/features/applications/api/applications";
import type {
  Application,
  ApplicationCreateData,
  ApplicationUpdateData,
} from "@/features/applications/types";

interface ApplicationState {
  applications: Application[];
  currentApplication: Application | null;
  isLoading: boolean;
  isSaving: boolean;
  loaded: boolean;
  error: string | null;
  fetchAll: () => Promise<void>;
  fetch: (id: string) => Promise<Application | null>;
  create: (input: ApplicationCreateData) => Promise<Application>;
  update: (id: string, input: ApplicationUpdateData) => Promise<Application>;
  remove: (id: string) => Promise<void>;
  recompute: (id: string) => Promise<Application>;
  scan: (id: string) => Promise<Application>;
}

function replaceApplication(applications: Application[], updated: Application): Application[] {
  const exists = applications.some((application) => application.id === updated.id);
  return exists
    ? applications.map((application) => (application.id === updated.id ? updated : application))
    : [updated, ...applications];
}

export const useApplicationStore = create<ApplicationState>((set) => ({
  applications: [],
  currentApplication: null,
  isLoading: false,
  isSaving: false,
  loaded: false,
  error: null,

  fetchAll: async () => {
    set({ isLoading: true, error: null });
    try {
      const applications = await applicationApi.listApplications();
      set({ applications, isLoading: false, loaded: true, error: null });
    } catch {
      set({
        isLoading: false,
        loaded: true,
        error: "Unable to load applications. Please try again.",
      });
    }
  },

  fetch: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const application = await applicationApi.getApplication(id);
      set((state) => ({
        currentApplication: application,
        applications: replaceApplication(state.applications, application),
        isLoading: false,
        loaded: true,
        error: null,
      }));
      return application;
    } catch {
      set({
        currentApplication: null,
        isLoading: false,
        loaded: true,
        error: "Unable to load this application. Please try again.",
      });
      return null;
    }
  },

  create: async (input) => {
    set({ isSaving: true });
    try {
      const application = await applicationApi.createApplication(input);
      set((state) => ({
        applications: [application, ...state.applications.filter((item) => item.id !== application.id)],
        currentApplication: application,
        isSaving: false,
      }));
      return application;
    } catch (error) {
      set({ isSaving: false });
      throw error;
    }
  },

  update: async (id, input) => {
    set({ isSaving: true });
    try {
      const application = await applicationApi.updateApplication(id, input);
      set((state) => ({
        applications: replaceApplication(state.applications, application),
        currentApplication: state.currentApplication?.id === id ? application : state.currentApplication,
        isSaving: false,
      }));
      return application;
    } catch (error) {
      set({ isSaving: false });
      throw error;
    }
  },

  remove: async (id) => {
    set({ isSaving: true });
    try {
      await applicationApi.deleteApplication(id);
      set((state) => ({
        applications: state.applications.filter((application) => application.id !== id),
        currentApplication: state.currentApplication?.id === id ? null : state.currentApplication,
        isSaving: false,
      }));
    } catch (error) {
      set({ isSaving: false });
      throw error;
    }
  },

  recompute: async (id) => {
    const application = await applicationApi.recomputeApplicationRelevance(id);
    set((state) => ({
      applications: replaceApplication(state.applications, application),
      currentApplication: state.currentApplication?.id === id ? application : state.currentApplication,
    }));
    return application;
  },

  scan: async (id) => {
    set({ isSaving: true });
    try {
      const application = await applicationApi.scanApplication(id);
      set((state) => ({
        applications: replaceApplication(state.applications, application),
        currentApplication: state.currentApplication?.id === id ? application : state.currentApplication,
        isSaving: false,
      }));
      return application;
    } catch (error) {
      set({ isSaving: false });
      throw error;
    }
  },
}));
