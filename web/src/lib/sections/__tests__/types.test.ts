import { describe, it, expect } from "vitest";
import { getFirstZoneId } from "../types";
import type { LayoutConfig } from "../types";

describe("getFirstZoneId", () => {
  it("returns the first zone's id when zones exist", () => {
    const layout: LayoutConfig = {
      zones: [
        { id: "main", styles: { width: "half" } },
        { id: "side", styles: { width: "narrow" } },
      ],
      placement: {},
    };
    expect(getFirstZoneId(layout)).toBe("main");
  });

  it("returns undefined when layout is null", () => {
    expect(getFirstZoneId(null)).toBeUndefined();
  });

  it("returns undefined when layout.zones is empty", () => {
    const layout: LayoutConfig = { zones: [], placement: {} };
    expect(getFirstZoneId(layout)).toBeUndefined();
  });
});
