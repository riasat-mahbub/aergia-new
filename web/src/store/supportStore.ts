import { create } from "zustand";
import { fetchRendererSupport } from "@/services/render";
import type { SupportMap } from "@/contracts/render";

interface SupportState {
  support: SupportMap | null;
  loaded: boolean;
  error: string | null;
  ensureLoaded: () => Promise<void>;
  retry: () => Promise<void>;
  /** Reset the in-memory support state. */
  reset: () => void;
}

export const useSupportStore = create<SupportState>((set, get) => ({
  support: null,
  loaded: false,
  error: null,
  ensureLoaded: async () => {
    if (get().loaded) return;
    try {
      const support = await fetchRendererSupport();
      set({ support, loaded: true, error: null });
    } catch (e) {
      // 401 already redirected by the client interceptor.
      // Other errors: fail open — support=null renders every control.
      set({ support: null, loaded: true, error: String(e) });
    }
  },
  retry: async () => {
    set({ loaded: false, error: null });
    await get().ensureLoaded();
  },
  reset: () => set({ support: null, loaded: false, error: null }),
}));
