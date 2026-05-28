import { describe, it, expect } from "vitest";
import { normalizeWidths } from "../zones";
import type { Zone } from "../types";

describe("normalizeWidths (zone-only layout)", () => {
  it("normalizes a flat four-zone list so widths sum to 100", () => {
    const zones: Zone[] = [
      { id: "a", styles: { width: "30%" } },
      { id: "b", styles: { width: "30%" } },
      { id: "c", styles: { width: "30%" } },
      { id: "d", styles: { width: "30%" } },
    ];
    const out = normalizeWidths(zones);
    const total = out.reduce((s, z) => s + parseInt(z.styles?.width || "0"), 0);
    expect(total).toBe(100);
    // All four ids preserved in order.
    expect(out.map((z) => z.id)).toEqual(["a", "b", "c", "d"]);
  });

  it("returns an empty list unchanged", () => {
    expect(normalizeWidths([])).toEqual([]);
  });

  it("returns input zones unchanged when widths already sum to 100", () => {
    const zones: Zone[] = [
      { id: "a", styles: { width: "60%" } },
      { id: "b", styles: { width: "40%" } },
    ];
    const out = normalizeWidths(zones);
    expect(out.map((z) => z.styles?.width)).toEqual(["60%", "40%"]);
  });

  it("divides an empty-width list evenly", () => {
    const zones: Zone[] = [
      { id: "a" },
      { id: "b" },
    ];
    const out = normalizeWidths(zones);
    const total = out.reduce((s, z) => s + parseInt(z.styles?.width || "0"), 0);
    expect(total).toBe(100);
  });
});
