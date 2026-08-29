import { create } from "zustand";
import client, { refreshSession } from "../api/client";
import { forgetAllKeys } from "../llm/keys";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, turnstileToken?: string) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

let hydrationPromise: Promise<void> | null = null;
let authOperation = 0;

function clearLegacyTokenStorage() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isLoading: false,

  hydrate: () => {
    if (hydrationPromise) return hydrationPromise;

    const operation = ++authOperation;
    hydrationPromise = (async () => {
      clearLegacyTokenStorage();
      set({ isLoading: true });
      try {
        const { data } = await client.get("/auth/session");
        if (data?.authenticated === true) {
          if (operation === authOperation) set({ isAuthenticated: true, isLoading: false });
          return;
        }

        await refreshSession();
        if (operation === authOperation) set({ isAuthenticated: true, isLoading: false });
      } catch {
        if (operation === authOperation) set({ isAuthenticated: false, isLoading: false });
      }
    })().finally(() => {
      hydrationPromise = null;
    });
    return hydrationPromise;
  },

  login: async (email: string, password: string) => {
    authOperation += 1;
    set({ isLoading: true });
    try {
      await client.post("/auth/login", { email, password });
      set({ isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isAuthenticated: false, isLoading: false });
      throw error;
    }
  },

  register: async (email: string, password: string, turnstileToken?: string) => {
    set({ isLoading: true });
    try {
      const payload: { email: string; password: string; turnstile_token?: string } = { email, password };
      if (turnstileToken) payload.turnstile_token = turnstileToken;
      await client.post("/auth/register", payload);
      set({ isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    authOperation += 1;
    try {
      await client.post("/auth/logout");
    } catch {
      // Clear local state even when the server is unavailable.
    }
    clearLegacyTokenStorage();
    forgetAllKeys();
    set({ isAuthenticated: false, isLoading: false });
  },
}));
