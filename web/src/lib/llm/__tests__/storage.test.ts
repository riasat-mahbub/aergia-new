/**
 * Storage backend invariant guard.
 *
 * This file's ONLY purpose is to assert that LLM keys live in
 * ``sessionStorage`` and not ``localStorage``. If a future contributor
 * quietly switches the backend, this test fails.
 */

import { describe, expect, it } from "vitest";

import { STORAGE_KEY, saveKeys, loadKeys } from "../keys";

describe("storage backend invariant", () => {
  it("writes to sessionStorage, not localStorage", () => {
    window.localStorage.clear();
    window.sessionStorage.clear();

    saveKeys({ openai: "sk-invariant-test" });

    expect(window.sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(loadKeys()).toEqual({ openai: "sk-invariant-test" });
  });
});
