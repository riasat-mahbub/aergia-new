/**
 * Storage backend invariant guard.
 *
 * This file's ONLY purpose is to assert that LLM keys live in
 * memory and not Web Storage. If a future contributor quietly reintroduces
 * browser persistence, this test fails.
 */

import { describe, expect, it } from "vitest";

import { STORAGE_KEY, saveKeys, loadKeys } from "../keys";

describe("storage backend invariant", () => {
  it("writes to neither sessionStorage nor localStorage", () => {
    window.localStorage.clear();
    window.sessionStorage.clear();

    saveKeys({ openai: "sk-invariant-test" });

    expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(loadKeys()).toEqual({ openai: "sk-invariant-test" });
  });
});
