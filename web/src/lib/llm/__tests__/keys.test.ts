/**
 * Tests for the LLM key storage primitives.
 *
 * Locks the contract:
 *  - ``STORAGE_KEY`` is the literal string "aergia.llm_keys".
 *  - All read/write paths use ``sessionStorage`` (NOT ``localStorage``).
 *  - Empty strings are stripped on save and load.
 *  - ``pickActiveProvider`` follows the canonical tie-break order.
 */

import { describe, expect, it } from "vitest";

import {
  PROVIDER_AUTOCOMPLETE,
  PROVIDER_PREFIXES,
  STORAGE_KEY,
  detectProviderShape,
  forgetAllKeys,
  forgetKey,
  loadKeys,
  pickActiveProvider,
  saveKeys,
  type LLMKeyMap,
  type LLMProviderKey,
} from "../keys";

describe("storage backend", () => {
  it("uses sessionStorage — backend key is 'aergia.llm_keys'", () => {
    expect(STORAGE_KEY).toBe("aergia.llm_keys");
  });

  it("saveKeys writes through sessionStorage and loadKeys reads it back", () => {
    saveKeys({ openai: "sk-round-trip-key" });
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBe(
      JSON.stringify({ openai: "sk-round-trip-key" })
    );
    expect(loadKeys()).toEqual({ openai: "sk-round-trip-key" });
  });

  it("forgetAllKeys wipes sessionStorage in one call", () => {
    saveKeys({ openai: "sk-still-here", gemini: "AIza-round-trip" });
    forgetAllKeys();
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(loadKeys()).toEqual({});
  });

  it("saveKeys drops empty strings and whitespace before writing", () => {
    saveKeys({ openai: "sk-real", anthropic: "   ", gemini: "" });
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    expect(raw).toBe(JSON.stringify({ openai: "sk-real" }));
    expect(loadKeys()).toEqual({ openai: "sk-real" });
  });

  it("loadKeys returns {} when no value is stored", () => {
    window.sessionStorage.clear();
    expect(loadKeys()).toEqual({});
  });

  it("loadKeys returns {} on malformed JSON instead of throwing", () => {
    window.sessionStorage.setItem(STORAGE_KEY, "{not-json");
    expect(loadKeys()).toEqual({});
  });
});

describe("detectProviderShape", () => {
  it("matches each known prefix", () => {
    expect(detectProviderShape("sk-abc")).toBe("openai");
    expect(detectProviderShape("sk-ant-xyz")).toBe("anthropic");
    expect(detectProviderShape("AIzaSyTest")).toBe("gemini");
    expect(detectProviderShape("gsk_abc")).toBe("groq");
  });

  it("returns null for empty, whitespace, or unknown prefix", () => {
    expect(detectProviderShape("")).toBeNull();
    expect(detectProviderShape("   ")).toBeNull();
    expect(detectProviderShape("totally-not-a-key")).toBeNull();
  });

  it("doesn't misclassify an Anthropic key as OpenAI", () => {
    expect(detectProviderShape("sk-ant-abcdef")).toBe("anthropic");
  });
});

describe("pickActiveProvider", () => {
  it("returns the only present provider", () => {
    expect(pickActiveProvider({ openai: "sk-1" })).toBe("openai");
  });

  it("breaks ties by canonical order", () => {
    const map: LLMKeyMap = {
      groq: "gsk_1",
      openai: "sk-1",
      gemini: "AIza",
      anthropic: "sk-ant-1",
    };
    expect(pickActiveProvider(map)).toBe("openai");
  });

  it("returns null when no key is present", () => {
    expect(pickActiveProvider({})).toBeNull();
  });

  it("treats empty/whitespace keys as missing", () => {
    expect(pickActiveProvider({ openai: "   " })).toBeNull();
  });
});

describe("forgetKey", () => {
  it("drops only the specified provider and persists the rest", () => {
    saveKeys({ openai: "sk-keep", gemini: "AIza-keep" });
    const next = forgetKey("openai");
    expect(next).toEqual({ gemini: "AIza-keep" });
    expect(loadKeys()).toEqual({ gemini: "AIza-keep" });
  });

  it("clears sessionStorage entirely when dropping the last key", () => {
    saveKeys({ openai: "sk-only" });
    forgetKey("openai");
    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});

describe("PROVIDER_AUTOCOMPLETE / PROVIDER_PREFIXES tables", () => {
  it("covers every provider", () => {
    const providers: LLMProviderKey[] = [
      "openai",
      "anthropic",
      "gemini",
      "groq",
    ];
    for (const p of providers) {
      expect(PROVIDER_AUTOCOMPLETE[p]).toBeTruthy();
      expect(PROVIDER_PREFIXES[p]).toBeTruthy();
    }
  });
});
