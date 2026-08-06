import { describe, it, expect } from "vitest";
import {
  effectiveSubsection,
  effectiveLayout,
  effectiveStyle,
  isOverridden,
  withoutOverride,
} from "../cascade";

describe("cascade — effective values", () => {
  it("effectiveSubsection layers instance override on top of type default", () => {
    const eff = effectiveSubsection("profile", { text_align: "right" });
    // Profile default is "center"; user override is "right" → wins.
    expect(eff.text_align).toBe("right");
  });

  it("effectiveSubsection returns the type default when override is empty", () => {
    const eff = effectiveSubsection("profile", {});
    expect(eff.text_align).toBe("center");
  });

  it("effectiveLayout applies keep_together default (True) when override is empty", () => {
    // This is the bug the helpers fix: schema default is True, override
    // is undefined → effective value should be True.
    const eff = effectiveLayout("experience", undefined);
    expect(eff.keep_together).toBe(true);
    expect(eff.heading_keeps_with_first).toBe(true);
    expect(eff.orphans).toBe(2);
    expect(eff.widows).toBe(2);
    expect(eff.break_before).toBe(false);
  });

  it("effectiveLayout keeps an explicit override", () => {
    const eff = effectiveLayout("experience", { keep_together: false });
    expect(eff.keep_together).toBe(false);
    expect(eff.heading_keeps_with_first).toBe(true); // default preserved
  });

  it("effectiveStyle layers every axis", () => {
    const eff = effectiveStyle("projects", {
      text: { project: { bold: true } },
      subsection: { text_align: "left" },
      layout: { break_before: true },
      policy: { heading_divider: true },
    });
    expect(eff.text.project?.bold).toBe(true);
    expect(eff.layout.chip_keys).toEqual(["tech"]); // type default preserved
    expect(eff.layout.break_before).toBe(true);    // override applied
    expect(eff.layout.keep_together).toBe(true);   // type default preserved
    expect(eff.policy.entry_layout).toBe("two-column"); // type default
    expect(eff.policy.heading_divider).toBe(true); // override applied
  });

  it("isOverridden returns true when values differ", () => {
    expect(isOverridden({ a: 1 }, { a: 2 })).toBe(true);
    expect(isOverridden({ a: 1 }, { a: 1 })).toBe(false);
  });

  it("withoutOverride removes an axis from a style", () => {
    const next = withoutOverride(
      {
        text: { name: { bold: true } },
        subsection: { text_align: "right" },
        layout: { break_before: true },
        policy: null,
      },
      "subsection",
    );
    expect(next.subsection).toBeUndefined();
    expect(next.text).toBeDefined();
    expect(next.layout).toBeDefined();
  });

  it("withoutOverride handles null/undefined style", () => {
    const next = withoutOverride(undefined, "layout");
    expect(next.layout).toBeUndefined();
  });
});
