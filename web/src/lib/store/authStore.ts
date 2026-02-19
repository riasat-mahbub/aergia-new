import { create } from "zustand";
import client from "../api/client";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,

  hydrate: () => {
    const accessToken = localStorage.getItem("access_token");
    const refreshToken = localStorage.getItem("refresh_token");
    set({
      accessToken,
      refreshToken,
      isAuthenticated: !!accessToken,
    });
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      const { data } = await client.post("/auth/login", { email, password });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
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
      // proceed with local logout even if server call fails
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  },
}));
