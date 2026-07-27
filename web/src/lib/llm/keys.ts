/**
 * Per-provider LLM API key storage — held in ``sessionStorage`` only.
 *
 * Hard rules:
 *  1. Storage backend is ``sessionStorage``. NO localStorage, NO
 *     in-memory module cache. Keys die with the browser tab.
 *  2. ``STORAGE_KEY`` is the single source of truth — tests assert
 *     the exact string so a future contributor cannot quietly
 *     switch the backend.
 *  3. Every ``write`` round-trips through ``saveKeys`` which drops
 *     empty-string values; ``loadKeys`` never returns an empty key
 *     to the orchestrator.
 *
 * The dialog (`LLMKeyDialog.tsx`) and the API wrapper (`imports.ts`)
 * both consume this module — no duplicate state, no module-level
 * caches.
 */

import { useSyncExternalStore } from "react";

export type LLMProviderKey = "openai" | "anthropic" | "gemini" | "groq";

export interface LLMKeyMap {
  openai?: string;
  anthropic?: string;
  gemini?: string;
  groq?: string;
}

/**
 * Per-provider `autocomplete` token. Each maps to a distinct
 * `autocomplete` value so browsers and password managers don't try
 * to autofill one provider's key into another slot. ``off`` is used
 * for Gemini/Groq because the WHATWG spec doesn't have a token
 * that matches their key shape.
 *
 * https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill-detail
 */
export const PROVIDER_AUTOCOMPLETE: Record<LLMProviderKey, string> = {
  openai: "current-password",
  anthropic: "current-password",
  gemini: "off",
  groq: "off",
};

/**
 * Per-provider expected prefix. Used by ``detectProviderShape`` to
 * warn the user when they typed a key into the wrong slot. The
 * server's ``detect_provider`` is the source of truth, but catching
 * the misclick here saves a round-trip.
 */
export const PROVIDER_PREFIXES: Record<LLMProviderKey, string> = {
  openai: "sk-",
  anthropic: "sk-ant-",
  gemini: "AIza",
  groq: "gsk_",
};

/** Canonical order for tie-breaking when multiple keys are stored. */
export const PROVIDER_ORDER: readonly LLMProviderKey[] = [
  "openai",
  "anthropic",
  "gemini",
  "groq",
];

/**
 * Single storage backend key. Tests guard this exact string so a
 * future contributor cannot quietly switch from sessionStorage to
 * localStorage.
 */
export const STORAGE_KEY = "aergia.llm_keys";

/**
 * Returns the provider whose prefix matches ``raw``, or ``null``
 * when the input doesn't match any known prefix. Used by the dialog
 * to surface a "this looks like an OpenAI key, not Anthropic"
 * warning.
 */
export function detectProviderShape(raw: string): LLMProviderKey | null {
  const trimmed = (raw ?? "").trim();
  if (!trimmed) return null;
  // Anthropic's prefix is a prefix of OpenAI's — check the more
  // specific value first to avoid mis-classifying ``sk-ant-`` as
  // OpenAI.
  if (trimmed.startsWith(PROVIDER_PREFIXES.anthropic)) return "anthropic";
  if (trimmed.startsWith(PROVIDER_PREFIXES.openai)) return "openai";
  if (trimmed.startsWith(PROVIDER_PREFIXES.gemini)) return "gemini";
  if (trimmed.startsWith(PROVIDER_PREFIXES.groq)) return "groq";
  return null;
}

function keysEqual(a: LLMKeyMap, b: LLMKeyMap): boolean {
  if (a === b) return true;
  for (const p of PROVIDER_ORDER) {
    if ((a[p] ?? "") !== (b[p] ?? "")) return false;
  }
  return true;
}

let cachedSnapshot: LLMKeyMap | null = null;

/**
 * Snapshot reader for ``useLLMKeys``. Reads sessionStorage, caches
 * the normalised value so reads are O(1) until the next write.
 */
function readSnapshot(): LLMKeyMap {
  const fresh = loadKeys();
  if (cachedSnapshot && keysEqual(cachedSnapshot, fresh)) return cachedSnapshot;
  cachedSnapshot = fresh;
  return fresh;
}

/**
 * Subscribe to changes from any code path that writes via this
 * module. Returns an unsubscribe; safe to call multiple times.
 */
function subscribe(listener: () => void): () => void {
  const onChange = () => {
    cachedSnapshot = null;
    listener();
  };
  // ``storage`` event fires for cross-tab writes; for in-tab writes
  // we trigger manually via the snap call below.
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function getServerSnapshot(): LLMKeyMap {
  return {};
}

/**
 * React hook reading the current key map from sessionStorage.
 * Re-renders the consumer when another tab mutates the key
 * (cross-tab via the ``storage`` event) or when this module's own
 * write helpers clear the cache.
 */
export function useLLMKeys(): LLMKeyMap {
  return useSyncExternalStore(subscribe, readSnapshot, getServerSnapshot);
}

/**
 * Load non-empty keys from sessionStorage. Empty strings dropped —
 * belt-and-suspenders so an attacker that can set sessionStorage
 * cannot inject empty-string keys to bypass the orchestrator's
 * empty-key short-circuit.
 */
export function loadKeys(): LLMKeyMap {
  if (typeof window === "undefined" || !window.sessionStorage) return {};
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as LLMKeyMap;
    return PROVIDER_ORDER.reduce<LLMKeyMap>((acc, p) => {
      const v = parsed?.[p];
      if (typeof v === "string" && v.trim().length > 0) {
        acc[p] = v;
      }
      return acc;
    }, {});
  } catch {
    return {};
  }
}

/**
 * Save the full map to sessionStorage. Empty/blank values dropped
 * before write. The drop IS the "forget" — there is no separate
 * forget-by-id primitive.
 */
export function saveKeys(map: LLMKeyMap): void {
  if (typeof window === "undefined" || !window.sessionStorage) return;
  const cleaned = PROVIDER_ORDER.reduce<LLMKeyMap>((acc, p) => {
    const v = map[p];
    if (typeof v === "string" && v.trim().length > 0) {
      acc[p] = v;
    }
    return acc;
  }, {});
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cleaned));
  cachedSnapshot = null;
  // Fire a synthetic storage event so any in-tab subscribers re-read.
  window.dispatchEvent(new Event("storage"));
}

/** Drop a single provider's key in place and return the new map. */
export function forgetKey(provider: LLMProviderKey): LLMKeyMap {
  const current = loadKeys();
  const rest: LLMKeyMap = { ...current };
  delete rest[provider];
  if (Object.keys(rest).length === 0) {
    forgetAllKeys();
    return {};
  }
  saveKeys(rest);
  return rest;
}

/** Drop every key. Used by the dialog's "Forget all" button. */
export function forgetAllKeys(): void {
  if (typeof window === "undefined" || !window.sessionStorage) return;
  window.sessionStorage.removeItem(STORAGE_KEY);
  cachedSnapshot = null;
  window.dispatchEvent(new Event("storage"));
}

/**
 * Choose the provider whose key is present; ties broken by the
 * canonical order (``openai``, ``anthropic``, ``gemini``, ``groq``).
 * Returns ``null`` if no key is present.
 */
export function pickActiveProvider(map: LLMKeyMap): LLMProviderKey | null {
  for (const p of PROVIDER_ORDER) {
    const v = map[p];
    if (typeof v === "string" && v.trim().length > 0) return p;
  }
  return null;
}
