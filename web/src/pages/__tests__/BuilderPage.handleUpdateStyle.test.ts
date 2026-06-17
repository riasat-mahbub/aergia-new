import { describe, it, expect } from "vitest";
import { sectionStyleHasValues } from "../BuilderPage";
import type { SectionStyle } from "../../lib/sections/types";

describe("sectionStyleHasValues", () => {
  it("returns true when only field_styles is set with a non-empty pick (regression: per-field typography)", () => {
    // This is the case that fails before the fix and passes after.
    expect(
      sectionStyleHasValues({
        field_styles: { name: { font: "Inter, system-ui, sans-serif" } },
      })
    ).toBe(true);
  });

  it("returns true when only field_styles is set with a size pick", () => {
    expect(
      sectionStyleHasValues({ field_styles: { title: { size: "16pt" } } })
    ).toBe(true);
  });

  it("returns true when only field_styles is set with a weight pick", () => {
    expect(
      sectionStyleHasValues({ field_styles: { summary: { weight: "600" } } })
    ).toBe(true);
  });

  it("returns true when field_styles carries multiple fields", () => {
    expect(
      sectionStyleHasValues({
        field_styles: {
          name: { font: "Inter" },
          title: { size: "14pt", weight: "700" },
        },
      })
    ).toBe(true);
  });

  it("returns false when field_styles is an empty object", () => {
    expect(sectionStyleHasValues({ field_styles: {} })).toBe(false);
  });

  it("returns false when field_styles only contains empty nested objects", () => {
    expect(
      sectionStyleHasValues({ field_styles: { name: {}, title: {} } })
    ).toBe(false);
  });

  it("returns false when field_styles is null", () => {
    // Defensive: a malformed null must not bypass the check.
    expect(
      sectionStyleHasValues({ field_styles: null as unknown as SectionStyle["field_styles"] })
    ).toBe(false);
  });

  it("returns true when section-level font is set (existing behavior preserved)", () => {
    expect(sectionStyleHasValues({ font: "Inter" })).toBe(true);
  });

  it("returns true when section-level color is set (existing behavior preserved)", () => {
    expect(sectionStyleHasValues({ color: "#ff0000" })).toBe(true);
  });

  it("returns true when section-level weight is set (existing behavior preserved)", () => {
    expect(sectionStyleHasValues({ weight: "700" })).toBe(true);
  });

  it("returns true when section-level text_align is set (existing behavior preserved)", () => {
    expect(sectionStyleHasValues({ text_align: "center" })).toBe(true);
  });

  it("returns true when show_title is explicitly false (load-bearing: false is a meaningful user choice)", () => {
    expect(sectionStyleHasValues({ show_title: false })).toBe(true);
  });

  it("returns true when show_title is explicitly true", () => {
    expect(sectionStyleHasValues({ show_title: true })).toBe(true);
  });

  it("returns true when layout is explicitly inline", () => {
    expect(sectionStyleHasValues({ layout: "inline" })).toBe(true);
  });

  it("returns true when layout is explicitly block", () => {
    expect(sectionStyleHasValues({ layout: "block" })).toBe(true);
  });

  it("returns true when row_gap is set (per-profile row spacing)", () => {
    expect(sectionStyleHasValues({ row_gap: "12px" })).toBe(true);
  });

   it("returns true when subsection_gap is set (per-section override beats template var)", () => {
    expect(sectionStyleHasValues({ subsection_gap: "20px" })).toBe(true);
  });

  it("returns false when row_gap is undefined or empty string", () => {
    expect(sectionStyleHasValues({ row_gap: undefined })).toBe(false);
    expect(sectionStyleHasValues({ row_gap: "" })).toBe(false);
  });

  it("returns true when date_style is set (new: per-section date format)", () => {
    expect(
      sectionStyleHasValues({ date_style: { key: "Mon YYYY", rangeSep: " \u2013 " } }),
    ).toBe(true);
  });

  it("returns true when date_style is set alongside other picks", () => {
    expect(
      sectionStyleHasValues({
        color: "#111111",
        date_style: { key: "Month YYYY", rangeSep: " \u2013 " },
      }),
    ).toBe(true);
  });

  it("returns true when section-level and per-field styles are mixed", () => {
    expect(
      sectionStyleHasValues({
        color: "#111111",
        field_styles: { name: { font: "Inter" } },
      })
    ).toBe(true);
  });
});
