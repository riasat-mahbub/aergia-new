/**
 * Short-lived LLM API key state.
 *
 * Keys never enter localStorage, sessionStorage, cookies, URL parameters, or
 * an auth store. They live only in page JavaScript memory and are explicitly
 * cleared after an import, logout, or user-requested forget.
 */

import { useSyncExternalStore } from "react";

export type LLMProviderKey = "openai" | "anthropic" | "gemini" | "groq";

export interface LLMKeyMap {
  openai?: string;
  anthropic?: string;
  gemini?: string;
  groq?: string;
}

/** API keys are not account passwords; prevent password-manager cross-fill. */
export const PROVIDER_AUTOCOMPLETE: Record<LLMProviderKey, string> = {
  openai: "off",
  anthropic: "off",
  gemini: "off",
  groq: "off",
};

export const PROVIDER_PREFIXES: Record<LLMProviderKey, string> = {
  openai: "sk-",
  anthropic: "sk-ant-",
  gemini: "AIza",
  groq: "gsk_",
};

export const PROVIDER_ORDER: readonly LLMProviderKey[] = [
  "openai",
  "anthropic",
  "gemini",
  "groq",
];

/** Kept as a compatibility export; no browser storage uses this key. */
export const STORAGE_KEY = "aergia.llm_keys";

let currentKeys: LLMKeyMap = {};
let snapshot: LLMKeyMap = {};
const listeners = new Set<() => void>();

function notify(): void {
  snapshot = { ...currentKeys };
  listeners.forEach((listener) => listener());
}

function cleanKeys(map: LLMKeyMap): LLMKeyMap {
  return PROVIDER_ORDER.reduce<LLMKeyMap>((acc, provider) => {
    const value = map[provider];
    if (typeof value === "string" && value.trim()) acc[provider] = value;
    return acc;
  }, {});
}

export function detectProviderShape(raw: string): LLMProviderKey | null {
  const trimmed = (raw ?? "").trim();
  if (!trimmed) return null;
  if (trimmed.startsWith(PROVIDER_PREFIXES.anthropic)) return "anthropic";
  if (trimmed.startsWith(PROVIDER_PREFIXES.openai)) return "openai";
  if (trimmed.startsWith(PROVIDER_PREFIXES.gemini)) return "gemini";
  if (trimmed.startsWith(PROVIDER_PREFIXES.groq)) return "groq";
  return null;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getServerSnapshot(): LLMKeyMap {
  return {};
}

export function useLLMKeys(): LLMKeyMap {
  return useSyncExternalStore(subscribe, () => snapshot, getServerSnapshot);
}

export function loadKeys(): LLMKeyMap {
  return { ...currentKeys };
}

export function saveKeys(map: LLMKeyMap): void {
  currentKeys = cleanKeys(map);
  notify();
}

export function forgetKey(provider: LLMProviderKey): LLMKeyMap {
  const next = { ...currentKeys };
  delete next[provider];
  currentKeys = next;
  notify();
  return { ...currentKeys };
}

export function forgetAllKeys(): void {
  currentKeys = {};
  notify();
}

export function pickActiveProvider(map: LLMKeyMap): LLMProviderKey | null {
  for (const provider of PROVIDER_ORDER) {
    const value = map[provider];
    if (typeof value === "string" && value.trim()) return provider;
  }
  return null;
}
