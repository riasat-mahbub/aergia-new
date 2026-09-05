import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { createStore, type StoreApi } from "zustand/vanilla";
import { useStore } from "zustand";
import * as authApi from "@/features/authentication/api/auth";
import type { AccountTier, RegisterRequest, SessionResponse } from "@/features/authentication/types";
import { forgetAllKeys } from "@/features/llm-credentials";

export interface AuthState {
  isAuthenticated: boolean;
  accountTier: AccountTier | null;
  isLoading: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, turnstileToken?: string) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export type AuthStore = StoreApi<AuthState>;

function clearLegacyTokenStorage() {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function snapshotToState(snapshot: SessionResponse): Pick<AuthState, "isAuthenticated" | "accountTier"> {
  return {
    isAuthenticated: snapshot.authenticated,
    accountTier: snapshot.account_tier,
  };
}

export function createAuthStore(initialSession: SessionResponse): AuthStore {
  let hydrationPromise: Promise<void> | null = null;
  let authOperation = 0;

  return createStore<AuthState>((set) => ({
    ...snapshotToState(initialSession),
    isLoading: false,

    hydrate: () => {
      if (hydrationPromise) return hydrationPromise;
      const operation = ++authOperation;
      hydrationPromise = (async () => {
        clearLegacyTokenStorage();
        set({ isLoading: true });
        try {
          const session = await authApi.getSession();
          if (session.authenticated) {
            if (operation === authOperation) {
              set({ ...snapshotToState(session), isLoading: false });
            }
            return;
          }
          await authApi.refreshAuthenticatedSession();
          const accountTier = await authApi.getAccountTier();
          if (operation === authOperation) {
            set({ isAuthenticated: true, accountTier, isLoading: false });
          }
        } catch {
          if (operation === authOperation) {
            set({ isAuthenticated: false, accountTier: null, isLoading: false });
          }
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
        // Clear local state even when the API is unavailable.
      }
      clearLegacyTokenStorage();
      forgetAllKeys();
      set({ isAuthenticated: false, accountTier: null, isLoading: false });
    },
  }));
}

const AuthStoreContext = createContext<AuthStore | null>(null);

export function AuthStoreProvider({ initialSession, children }: {
  initialSession: SessionResponse;
  children: ReactNode;
}) {
  const [store] = useState(() => createAuthStore(initialSession));
  useEffect(() => {
    store.setState({ ...snapshotToState(initialSession), isLoading: false });
  }, [initialSession, store]);
  return <AuthStoreContext.Provider value={store}>{children}</AuthStoreContext.Provider>;
}

export function useAuthStore<T>(selector: (state: AuthState) => T): T {
  const store = useContext(AuthStoreContext);
  if (!store) throw new Error("useAuthStore must be used inside AuthStoreProvider");
  return useStore(store, selector);
}
