import { describe, it, expect } from "vitest";
import {
  profileSchema,
  projectEntrySchema,
  certificationEntrySchema,
  researchEntrySchema,
  urlSchema,
  sectionInstanceSchema,
  customizationsSchema,
  templateManifestSchema,
} from "../sections";

describe("urlSchema", () => {
  it("accepts an empty string", () => {
    expect(urlSchema.safeParse("").success).toBe(true);
  });

  it("accepts https:// URLs", () => {
    expect(urlSchema.safeParse("https://aergia.dev").success).toBe(true);
  });

  it("accepts http:// URLs", () => {
    expect(urlSchema.safeParse("http://insecure.example.com").success).toBe(true);
  });

  it("accepts mailto: URLs", () => {
    expect(urlSchema.safeParse("mailto:foo@bar.com").success).toBe(true);
  });

  it("accepts tel: URLs", () => {
    expect(urlSchema.safeParse("tel:+1234567890").success).toBe(true);
  });

  it("accepts ftp:// URLs", () => {
    expect(urlSchema.safeParse("ftp://files.example.com").success).toBe(true);
  });

  it("rejects bare domains — the user-facing bug", () => {
    // Chromium's print pipeline silently drops <a href> annotations when the
    // href is missing a scheme. The validator must catch this at form time.
    const result = urlSchema.safeParse("rmahbub.com");
    expect(result.success).toBe(false);
    expect(result.error!.issues[0].message).toMatch(/scheme/i);
  });

  it("rejects www.-prefixed domains without scheme", () => {
    expect(urlSchema.safeParse("www.example.com").success).toBe(false);
  });

  it("rejects paths without a scheme", () => {
    expect(urlSchema.safeParse("example.com/page").success).toBe(false);
  });
});

describe("profileSchema.site_url", () => {
  const baseProfile = {
    name: "Alice",
    title: "Engineer",
    email: "alice@example.com",
    email_link: true,
    phone: "+1 555",
    location: "Remote",
    site_text: "Site",
    summary: "Hi",
    photo_url: "",
  };

  it("accepts a valid https site_url", () => {
    const r = profileSchema.safeParse({ ...baseProfile, site_url: "https://aergia.dev" });
    expect(r.success).toBe(true);
  });

  it("accepts an empty site_url (the field is optional)", () => {
    const r = profileSchema.safeParse({ ...baseProfile, site_url: "" });
    expect(r.success).toBe(true);
  });

  it("rejects a bare-domain site_url and pins the error to site_url", () => {
    const r = profileSchema.safeParse({ ...baseProfile, site_url: "rmahbub.com" });
    expect(r.success).toBe(false);
    const paths = r.error!.issues.map((i) => i.path.join("."));
    expect(paths).toContain("site_url");
  });
});

describe("projectEntrySchema.url", () => {
  const baseProject = {
    id: "p1",
    name: "CV Builder",
    link_text: "github",
    start_date: "2025",
    end_date: null,
    description: "Tooling",
    tech_stack: [],
  };

  it("accepts a valid https URL", () => {
    expect(projectEntrySchema.safeParse({ ...baseProject, url: "https://github.com/x/y" }).success).toBe(true);
  });

  it("accepts an empty URL (field is optional)", () => {
    expect(projectEntrySchema.safeParse({ ...baseProject, url: "" }).success).toBe(true);
  });

  it("rejects a bare-domain project URL", () => {
    const r = projectEntrySchema.safeParse({ ...baseProject, url: "github.com/x/y" });
    expect(r.success).toBe(false);
    expect(r.error!.issues.map((i) => i.path.join("."))).toContain("url");
  });
});

describe("certificationEntrySchema.credential_url", () => {
  const baseCert = {
    id: "c1",
    name: "AWS",
    issuer: "Amazon",
    date: "2024",
  };

  it("accepts an empty credential_url (field is optional)", () => {
    expect(certificationEntrySchema.safeParse({ ...baseCert, credential_url: "" }).success).toBe(true);
  });

  it("rejects a bare-domain credential URL", () => {
    const r = certificationEntrySchema.safeParse({ ...baseCert, credential_url: "aws.amazon.com/cert" });
    expect(r.success).toBe(false);
    expect(r.error!.issues.map((i) => i.path.join("."))).toContain("credential_url");
  });

  it("accepts a fully-qualified credential URL", () => {
    expect(
      certificationEntrySchema.safeParse({ ...baseCert, credential_url: "https://aws.amazon.com/cert" }).success,
    ).toBe(true);
  });
});

describe("researchEntrySchema", () => {
  const baseResearch = {
    id: "r1",
    paper_url: "",
    paper_link_text: "",
    publication_date: "",
    publication_value: "",
  };

  it("requires a non-empty title", () => {
    const r = researchEntrySchema.safeParse({ ...baseResearch, title: "", description: "Findings" });
    expect(r.success).toBe(false);
    expect(r.error!.issues.map((i) => i.path.join("."))).toContain("title");
  });

  it("requires a non-empty description", () => {
    const r = researchEntrySchema.safeParse({ ...baseResearch, title: "Title", description: "" });
    expect(r.success).toBe(false);
    expect(r.error!.issues.map((i) => i.path.join("."))).toContain("description");
  });

  it("accepts empty paper_url, link text, and date (all optional)", () => {
    expect(
      researchEntrySchema.safeParse({ ...baseResearch, title: "Paper", description: "Findings" }).success,
    ).toBe(true);
  });

  it("accepts a valid https URL", () => {
    expect(
      researchEntrySchema.safeParse({
        ...baseResearch,
        title: "Paper",
        description: "Findings",
        paper_url: "https://doi.org/10.0000/aergia.2026",
        paper_link_text: "DOI",
        publication_date: "2026-06",
      }).success,
    ).toBe(true);
  });

  it("rejects a bare-domain paper_url with the standard URL-scheme message", () => {
    const r = researchEntrySchema.safeParse({
      ...baseResearch,
      title: "Paper",
      description: "Findings",
      paper_url: "example.org/paper",
    });
    expect(r.success).toBe(false);
    expect(r.error!.issues.map((i) => i.path.join("."))).toContain("paper_url");
  });
});


describe("sectionInstanceSchema three-axis style", () => {
  it("accepts a three-axis style on a profile section", () => {
    const r = sectionInstanceSchema.safeParse({
      id: "p1", type: "profile", title: "Profile", enabled: true, data: {},
      style: {
        layout: { font_family: "Inter", break_before: true },
        subsection: { text_align: "left", section_color: "#ff0000" },
        policy: { show_title: true },
        text: { name: { font_size: "small", bold: true } },
      },
    });
    expect(r.success).toBe(true);
  });

  it("rejects legacy top-level keys on style", () => {
    const r = sectionInstanceSchema.safeParse({
      id: "p1", type: "profile", title: "P", enabled: true, data: {},
      style: { font: "Inter" as any },
    });
    expect(r.success).toBe(false);
  });

  it("rejects unknown inner-axis keys (strict)", () => {
    const r = sectionInstanceSchema.safeParse({
      id: "p1", type: "profile", title: "P", enabled: true, data: {},
      style: { layout: { not_a_field: true } as any },
    });
    expect(r.success).toBe(false);
  });

  it("accepts missing style", () => {
    const r = sectionInstanceSchema.safeParse({
      id: "p1", type: "profile", title: "P", enabled: true, data: {},
    });
    expect(r.success).toBe(true);
  });
});

describe("customizationsSchema canonical", () => {
  it("accepts canonical fields", () => {
    const r = customizationsSchema.safeParse({
      accent_color: "#aabbcc",
      body_font: "sans-serif",
      spacing: "compact",
      per_section: { p1: { layout: { font_family: "Inter, system-ui, sans-serif" } } },
    });
    expect(r.success).toBe(true);
  });

  it("rejects legacy top-level colors", () => {
    const r = customizationsSchema.safeParse({ colors: { accent: "#aabbcc" } });
    expect(r.success).toBe(false);
  });
  it("rejects legacy top-level fonts", () => {
    const r = customizationsSchema.safeParse({ fonts: { body: "Inter" } });
    expect(r.success).toBe(false);
  });
});
describe("templateManifestSchema (v2)", () => {
  it("accepts the canonical v2 shape", () => {
    const r = templateManifestSchema.safeParse({
      manifest_version: 2,
      name: "Modern",
      zones: [{ id: "main" }],
      placement: { profile: "main" },
      global_styles: { accent_color: "#2563eb" },
    });
    expect(r.success).toBe(true);
  });

  it("rejects manifest_version: 1", () => {
    const r = templateManifestSchema.safeParse({
      manifest_version: 1,
      name: "Old",
      zones: [],
      placement: {},
    });
    expect(r.success).toBe(false);
  });

  it("rejects a global_styles value that is not a string", () => {
    const r = templateManifestSchema.safeParse({
      manifest_version: 2,
      name: "X",
      global_styles: { accent_color: 42 },
    });
    expect(r.success).toBe(false);
  });
});