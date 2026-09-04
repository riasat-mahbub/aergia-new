import { create } from "zustand";
import * as authApi from "@/services/auth";
import type { AccountTier, RegisterRequest } from "@/contracts/auth";
import { forgetAllKeys } from "@/lib/llm/keys";

interface AuthState {
  isAuthenticated: boolean;
  accountTier: AccountTier | null;
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
  accountTier: null,
  isLoading: false,

  hydrate: () => {
    if (hydrationPromise) return hydrationPromise;

    const operation = ++authOperation;
    hydrationPromise = (async () => {
      clearLegacyTokenStorage();
      set({ isLoading: true });
      try {
        const session = await authApi.getSession();
        if (session.authenticated === true) {
          if (operation === authOperation) {
            set({
              isAuthenticated: true,
              accountTier: session.account_tier,
              isLoading: false,
            });
          }
          return;
        }

        await authApi.refreshAuthenticatedSession();
        const accountTier = await authApi.getAccountTier();
        if (operation === authOperation) set({ isAuthenticated: true, accountTier, isLoading: false });
      } catch {
        if (operation === authOperation) set({ isAuthenticated: false, accountTier: null, isLoading: false });
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
      await authApi.login({ email, password });
      const accountTier = await authApi.getAccountTier();
      set({ isAuthenticated: true, accountTier, isLoading: false });
    } catch (error) {
      set({ isAuthenticated: false, accountTier: null, isLoading: false });
      throw error;
    }
  },

  register: async (email: string, password: string, turnstileToken?: string) => {
    set({ isLoading: true });
    try {
      const payload: RegisterRequest = { email, password };
      if (turnstileToken) payload.turnstile_token = turnstileToken;
      await authApi.register(payload);
      set({ isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: async () => {
    authOperation += 1;
    try {
      await authApi.logout();
    } catch {
      // Clear local state even when the server is unavailable.
    }
    clearLegacyTokenStorage();
    forgetAllKeys();
    set({ isAuthenticated: false, accountTier: null, isLoading: false });
  },
}));
