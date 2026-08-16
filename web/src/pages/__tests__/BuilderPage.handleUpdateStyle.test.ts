import { describe, it, expect } from "vitest";
import { applicationMatchesCv, sectionStyleHasValues } from "../BuilderPage";
import type { SectionInstanceStyle } from "../../lib/sections/types";

describe("sectionStyleHasValues (three-axis)", () => {
  it("returns false for an empty style object (no axes populated)", () => {
    expect(sectionStyleHasValues({})).toBe(false);
  });

  it("returns true when only layout is populated", () => {
    expect(
      sectionStyleHasValues({ layout: { font_family: "Inter" } } as SectionInstanceStyle),
    ).toBe(true);
  });

  it("returns true when only subsection is populated", () => {
    expect(
      sectionStyleHasValues({
        subsection: { section_color: "#ff0000" },
      } as SectionInstanceStyle),
    ).toBe(true);
  });

  it("returns true when only policy is populated (show_title explicit)", () => {
    expect(
      sectionStyleHasValues({ policy: { show_title: false } } as SectionInstanceStyle),
    ).toBe(true);
  });

  it("returns true when only text is populated (per-field style)", () => {
    expect(
      sectionStyleHasValues({
        text: { name: { font_size: "small" } },
      } as SectionInstanceStyle),
    ).toBe(true);
  });

  it("returns false when each axis is an empty object", () => {
    expect(
      sectionStyleHasValues({
        layout: {},
        subsection: {},
        policy: {},
        text: {},
      } as unknown as SectionInstanceStyle),
    ).toBe(false);
  });


  it("text[key] entries with at least one TextStyle key count as a meaningful pick", () => {
    expect(
      sectionStyleHasValues({ text: { name: { bold: true } } } as SectionInstanceStyle),
    ).toBe(true);
  });
});


describe("applicationMatchesCv", () => {
  it("accepts only the application linked to the current CV", () => {
    expect(applicationMatchesCv({ cv_id: "cv-1" } as never, "cv-1")).toBe(true);
    expect(applicationMatchesCv({ cv_id: "cv-2" } as never, "cv-1")).toBe(false);
    expect(applicationMatchesCv(null, "cv-1")).toBe(false);
  });
});