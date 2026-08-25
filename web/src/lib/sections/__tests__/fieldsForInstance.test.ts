import { describe, it, expect } from "vitest";
import { fieldsForInstance } from "../fieldsForInstance";
import type { SectionInstance } from "../types";

const baseInstance = (overrides: Partial<SectionInstance>): SectionInstance => ({
  id: "s1",
  type: "profile",
  title: "Profile",
  enabled: true,
  data: {},
  ...overrides,
});

describe("fieldsForInstance — runtime field list", () => {
  it("returns the correct keys for profile (social, not social_links)", () => {
    const inst = baseInstance({
      type: "profile",
      data: { name: "Alex", email: "a@b.c", social_links: [{ label: "GH", url: "x" }] },
    });
    const rows = fieldsForInstance(inst);
    const keys = rows.map((r) => r.key);
    expect(keys).toContain("name");
    expect(keys).toContain("email");
    expect(keys).toContain("social");
    expect(keys).not.toContain("social_links");
  });

  it("returns no rows for fields the user has not filled", () => {
    const inst = baseInstance({ type: "profile", data: { name: "Alex" } });
    const rows = fieldsForInstance(inst);
    expect(rows.map((r) => r.key)).toEqual(["name"]);
  });

  it("flags summary as rich text", () => {
    const inst = baseInstance({
      type: "profile",
      data: { name: "Alex", summary: "Hello world" },
    });
    const rows = fieldsForInstance(inst);
    const summary = rows.find((r) => r.key === "summary");
    expect(summary?.isRichText).toBe(true);
  });

  it("includes experience fields the old static table missed (location)", () => {
    const inst = baseInstance({
      type: "experience",
      data: [{ position: "Engineer", company: "Acme", location: "Remote", start_date: "2020-01", end_date: null, current: true }],
    });
    const rows = fieldsForInstance(inst);
    const keys = rows.map((r) => r.key);
    expect(keys).toContain("position");
    expect(keys).toContain("company");
    expect(keys).toContain("location");
    expect(keys).toContain("date");
  });

  it("lists certifications (the old static table omitted the section)", () => {
    const inst = baseInstance({
      type: "certifications",
      data: [{ name: "AWS SA", issuer: "AWS", date: "2024-01", credential_url: "https://x", link_text: "Credential" }],
    });
    const rows = fieldsForInstance(inst);
    const keys = rows.map((r) => r.key);
    expect(keys).toContain("certification");
    expect(keys).toContain("issuer");
    expect(keys).toContain("date");
    expect(keys).toContain("link");
  });

  it("aggregates skills tags into a single 'tag' row", () => {
    const inst = baseInstance({
      type: "skills",
      data: [{ category: "Languages", items: ["TS", "JS", "Python", "Go"] }],
    });
    const rows = fieldsForInstance(inst);
    const tags = rows.find((r) => r.key === "tag");
    expect(tags).toBeDefined();
    expect(tags?.aggregated).toBe(true);
    // Sample is the first 3 joined
    expect(tags?.sample).toContain("TS");
  });

  it("returns empty array for unknown types", () => {
    const inst = baseInstance({ type: "exotic" as unknown as SectionInstance["type"], data: {} });
    expect(fieldsForInstance(inst)).toEqual([]);
  });

  it("returns empty when data is empty", () => {
    const inst = baseInstance({ type: "experience", data: [] });
    expect(fieldsForInstance(inst)).toEqual([]);
  });

  it("falls back to a generic date sample when no real dates are in the data", () => {
    const inst = baseInstance({
      type: "experience",
      data: [{ position: "X" }],
    });
    const rows = fieldsForInstance(inst);
    const date = rows.find((r) => r.key === "date");
    expect(date?.sample).toMatch(/2024/);
  });
});
