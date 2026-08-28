import { create } from "zustand";
import client from "../api/client";
import { forgetAllKeys } from "../llm/keys";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

function clearLegacyTokenStorage() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  isLoading: false,

  hydrate: async () => {
    clearLegacyTokenStorage();
    set({ isLoading: true });
    try {
      const { data } = await client.get("/auth/session");
      set({ isAuthenticated: data?.authenticated === true, isLoading: false });
    } catch {
      set({ isAuthenticated: false, isLoading: false });
    }
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      await client.post("/auth/login", { email, password });
      set({ isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isAuthenticated: false, isLoading: false });
      throw error;
    }
  },

  register: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      await client.post("/auth/register", { email, password });
      set({ isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
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
