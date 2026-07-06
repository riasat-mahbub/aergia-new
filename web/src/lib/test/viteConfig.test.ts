import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const CONFIG_PATH = resolve(__dirname, "..", "..", "..", "vite.config.ts");

function extractTestInclude(source: string): string[] | undefined {
  // Match `test: { ... include: [ ... ] ... }` block and return the array of string literals.
  // Focused text check, not a full TS parse, so it stays independent of
  // the React plugin / esbuild invariant.
  const block = source.match(/test\s*:\s*\{[\s\S]*?include\s*:\s*\[([\s\S]*?)\]/);
  if (!block) return undefined;
  const inner = block[1];
  return Array.from(inner.matchAll(/["']([^"']+)["']/g)).map((m) => m[1]);
}

describe("Vite config — test discovery", () => {
  it("locks Vitest discovery to web/src tests via test.include", () => {
    const source = readFileSync(CONFIG_PATH, "utf-8");
    const include = extractTestInclude(source);
    expect(include).toEqual(["src/**/*.test.{ts,tsx}"]);
  });
});
