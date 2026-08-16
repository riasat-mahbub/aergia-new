import { create } from "zustand";
import * as applicationApi from "../api/applications";
import type {
  Application,
  ApplicationCreateData,
  ApplicationGenerateResponse,
  ApplicationUpdateData,
} from "../api/applications";

interface ApplicationState {
  applications: Application[];
  currentApplication: Application | null;
  isLoading: boolean;
  isSaving: boolean;
  loaded: boolean;
  fetchAll: () => Promise<void>;
  fetch: (id: string) => Promise<Application | null>;
  create: (input: ApplicationCreateData) => Promise<Application>;
  update: (id: string, input: ApplicationUpdateData) => Promise<Application>;
  remove: (id: string) => Promise<void>;
  generate: (id: string) => Promise<ApplicationGenerateResponse>;
  recompute: (id: string) => Promise<Application>;
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

  fetchAll: async () => {
    set({ isLoading: true });
    try {
      const applications = await applicationApi.listApplications();
      set({ applications, isLoading: false, loaded: true });
    } catch {
      set({ isLoading: false, loaded: true });
    }
  },

  fetch: async (id) => {
    set({ isLoading: true });
    try {
      const application = await applicationApi.getApplication(id);
      set((state) => ({
        currentApplication: application,
        applications: replaceApplication(state.applications, application),
        isLoading: false,
        loaded: true,
      }));
      return application;
    } catch {
      set({ currentApplication: null, isLoading: false, loaded: true });
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

  generate: async (id) => {
    set({ isSaving: true });
    try {
      const result = await applicationApi.generateApplication(id);
      set((state) => ({
        applications: replaceApplication(state.applications, result.application),
        currentApplication: result.application,
        isSaving: false,
      }));
      return result;
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
}));
