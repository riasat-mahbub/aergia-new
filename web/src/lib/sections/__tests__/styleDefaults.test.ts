import { describe, it, expect } from "vitest";
import {
  SECTION_POLICY_DEFAULTS,
  defaultPolicyFor,
  defaultSubsectionFor,
  defaultLayoutFor,
  defaultStyleFor,
  TEXT_STYLE_DEFAULTS,
} from "../styleDefaults";

describe("styleDefaults — schema mirror", () => {
  it("TEXT_STYLE_DEFAULTS match the TextStyle schema (every bool is False, color/size null)", () => {
    expect(TEXT_STYLE_DEFAULTS.bold).toBe(false);
    expect(TEXT_STYLE_DEFAULTS.italic).toBe(false);
    expect(TEXT_STYLE_DEFAULTS.underline).toBe(false);
    expect(TEXT_STYLE_DEFAULTS.strike).toBe(false);
    expect(TEXT_STYLE_DEFAULTS.color).toBeNull();
    expect(TEXT_STYLE_DEFAULTS.link).toBeNull();
    expect(TEXT_STYLE_DEFAULTS.font_size).toBeNull();
  });

  it("every known section type has a policy default", () => {
    for (const t of [
      "profile", "experience", "education", "skills", "projects",
      "languages", "certifications", "research", "extras",
    ]) {
      expect(SECTION_POLICY_DEFAULTS[t]).toBeDefined();
    }
  });

  it("profile policy hides the title; every other default shows it", () => {
    expect(defaultPolicyFor("profile").show_title).toBe(false);
    expect(defaultPolicyFor("experience").show_title).toBe(true);
    expect(defaultPolicyFor("education").show_title).toBe(true);
    expect(defaultPolicyFor("skills").show_title).toBe(true);
    expect(defaultPolicyFor("projects").show_title).toBe(true);
    expect(defaultPolicyFor("languages").show_title).toBe(true);
    expect(defaultPolicyFor("certifications").show_title).toBe(true);
    expect(defaultPolicyFor("research").show_title).toBe(true);
    expect(defaultPolicyFor("extras").show_title).toBe(true);
  });

  it("defaults visible section headings to underlined", () => {
    expect(defaultPolicyFor("profile").heading_divider).toBe(true);
    expect(defaultPolicyFor("experience").heading_divider).toBe(true);
    expect(defaultPolicyFor("skills").heading_divider).toBe(true);
  });

  it("skills policy defaults skill_variant to 'block'", () => {
    expect(defaultPolicyFor("skills").skill_variant).toBe("block");
  });

  it("projects/research/certifications default entry_layout to 'two-column'", () => {
    expect(defaultPolicyFor("projects").entry_layout).toBe("two-column");
    expect(defaultPolicyFor("research").entry_layout).toBe("two-column");
    expect(defaultPolicyFor("certifications").entry_layout).toBe("two-column");
  });

  it("every other section defaults entry_layout to 'stack'", () => {
    expect(defaultPolicyFor("experience").entry_layout).toBe("stack");
    expect(defaultPolicyFor("education").entry_layout).toBe("stack");
  });

  it("profile subsection defaults text_align to 'center'", () => {
    expect(defaultSubsectionFor("profile").text_align).toBe("center");
    expect(defaultSubsectionFor("experience").text_align).toBeNull();
  });

  it("projects layout defaults chip_keys to ['tech']; nothing else has chip_keys", () => {
    expect(defaultLayoutFor("projects").chip_keys).toEqual(["tech"]);
    expect(defaultLayoutFor("experience").chip_keys).toBeNull();
    expect(defaultLayoutFor("skills").chip_keys).toBeNull();
  });

  it("layout defaults preserve keep_together=True schema default for every section", () => {
    for (const t of ["profile", "experience", "skills", "projects", "extras"]) {
      expect(defaultLayoutFor(t).keep_together).toBe(true);
      expect(defaultLayoutFor(t).heading_keeps_with_first).toBe(true);
    }
  });

  it("unknown section types return sane defaults, not crashes", () => {
    expect(defaultPolicyFor("unknown").show_title).toBe(true);
    expect(defaultPolicyFor("unknown").entry_layout).toBe("stack");
    expect(defaultSubsectionFor("unknown").text_align).toBeNull();
    expect(defaultLayoutFor("unknown").keep_together).toBe(true);
  });

  it("defaultStyleFor returns the layered shape", () => {
    const s = defaultStyleFor("profile");
    expect(s.text).toEqual({});
    expect(s.subsection!.text_align).toBe("center");
    expect(s.policy!.show_title).toBe(false);
    expect(s.layout).toBeDefined();
  });
});
