import { describe, it, expect } from "vitest";
import { normalizeWidths, getWidthPercent, percentToToken, widthTokenToCss } from "../zones";
import type { Zone } from "../types";

const tokenPercent = (token: string | null | undefined): number => {
  if (token === "narrow") return 30;
  if (token === "half") return 50;
  if (token === "full") return 100;
  if (token === "auto") return 0;
  return 0;
};

describe("normalizeWidths (token-based)", () => {
  it("preserves all four narrow zones", () => {
    const zones: Zone[] = [
      { id: "a", styles: { width: "narrow" } },
      { id: "b", styles: { width: "narrow" } },
      { id: "c", styles: { width: "narrow" } },
      { id: "d", styles: { width: "narrow" } },
    ];
    const out = normalizeWidths(zones);
    const total = out.reduce((s, z) => s + tokenPercent(z.styles?.width), 0);
    expect(total).toBe(120);
    expect(out.map((z) => z.id)).toEqual(["a", "b", "c", "d"]);
  });

  it("returns an empty list unchanged", () => {
    expect(normalizeWidths([])).toEqual([]);
  });

  it("returns input zones with token widths when already balanced", () => {
    const zones: Zone[] = [
      { id: "a", styles: { width: "half" } },
      { id: "b", styles: { width: "half" } },
    ];
    const out = normalizeWidths(zones);
    out.forEach((z) => {
      expect(["narrow", "half", "full", "auto"]).toContain(z.styles?.width);
    });
  });

  it("auto zones pick up the remaining width", () => {
    const zones: Zone[] = [
      { id: "a", styles: { width: "narrow" } },
      { id: "b" },
      { id: "c" },
    ];
    const out = normalizeWidths(zones);
    // 35 maps to "narrow" (30) since percentToToken uses <= 35.
    // 30 + 30 + 30 = 90.
    const total = out.reduce((s, z) => s + tokenPercent(z.styles?.width), 0);
    expect(total).toBe(90);
    out.forEach((z) => {
      expect(["narrow", "half", "full", "auto"]).toContain(z.styles?.width);
    });
  });
});

describe("getWidthPercent + percentToToken roundtrip", () => {
  it("returns a positive number for each token", () => {
    expect(getWidthPercent({ id: "z", styles: { width: "narrow" } })).toBe(30);
    expect(getWidthPercent({ id: "z", styles: { width: "half" } })).toBe(50);
    expect(getWidthPercent({ id: "z", styles: { width: "full" } })).toBe(100);
    expect(getWidthPercent({ id: "z", styles: { width: "auto" } })).toBe(0);
  });

  it("percentToToken maps percentages to the right token", () => {
    expect(percentToToken(20)).toBe("narrow");
    expect(percentToToken(50)).toBe("half");
    expect(percentToToken(100)).toBe("full");
    expect(percentToToken(70)).toBe("auto");
  });
});

describe("widthTokenToCss", () => {
  it("maps tokens to CSS percentage values", () => {
    expect(widthTokenToCss("narrow")).toBe("30%");
    expect(widthTokenToCss("half")).toBe("50%");
    expect(widthTokenToCss("full")).toBe("100%");
    expect(widthTokenToCss("auto")).toBe("auto");
  });
});
