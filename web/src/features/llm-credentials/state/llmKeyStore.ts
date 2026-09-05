import { create } from "zustand";
import type { LLMKeyMap, LLMProviderKey } from "@/features/llm-credentials/types";
import { PROVIDER_ORDER } from "@/features/llm-credentials/domain/providers";

interface LLMKeyState {
  keys: LLMKeyMap;
  saveKeys: (map: LLMKeyMap) => void;
  forgetKey: (provider: LLMProviderKey) => LLMKeyMap;
  forgetAllKeys: () => void;
}

function cleanKeys(map: LLMKeyMap): LLMKeyMap {
  return PROVIDER_ORDER.reduce<LLMKeyMap>((cleaned, provider) => {
    const value = map[provider];
    if (typeof value === "string" && value.trim()) cleaned[provider] = value;
    return cleaned;
  }, {});
}

/**
 * Short-lived, in-memory credential state. Deliberately no persist middleware:
 * keys must disappear on reload and are cleared after an import or logout.
 */
export const useLLMKeyStore = create<LLMKeyState>((set, get) => ({
  keys: {},

  saveKeys: (map) => set({ keys: cleanKeys(map) }),

  forgetKey: (provider) => {
    const next = { ...get().keys };
    delete next[provider];
    set({ keys: next });
    return { ...next };
  },

  forgetAllKeys: () => set({ keys: {} }),
}));

export function useLLMKeys(): LLMKeyMap {
  return useLLMKeyStore((state) => state.keys);
}

export function loadKeys(): LLMKeyMap {
  return { ...useLLMKeyStore.getState().keys };
}

export function saveKeys(map: LLMKeyMap): void {
  useLLMKeyStore.getState().saveKeys(map);
}

export function forgetKey(provider: LLMProviderKey): LLMKeyMap {
  return useLLMKeyStore.getState().forgetKey(provider);
}

export function forgetAllKeys(): void {
  useLLMKeyStore.getState().forgetAllKeys();
}
