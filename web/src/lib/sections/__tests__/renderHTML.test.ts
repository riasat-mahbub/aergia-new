import { describe, it, expect } from "vitest";
import { renderUserTemplateHTML } from "../renderHTML";
import type { SectionInstance, LayoutConfig } from "../types";

const profileInstance: SectionInstance = {
  id: "sec_profile",
  type: "profile",
  title: "Profile",
  enabled: true,
  data: {
    name: "Jane Doe",
    title: "Software Engineer",
    email: "jane@example.com",
    phone: "+1 555-1234",
    location: "Boston, MA",
    summary: "Experienced engineer.",
    photo_url: "",
  },
};

const experienceInstance: SectionInstance = {
  id: "sec_exp",
  type: "experience",
  title: "Experience",
  enabled: true,
  data: [
    { position: "Senior Dev", company: "ACME Corp", start_date: "2020", end_date: "2024" },
  ],
};

const customizations = {};

describe("renderUserTemplateHTML", () => {
  it("replaces all occurrences of zone placeholders (duplicate {{header}} in template)", () => {
    // MIT.html has {{header}} twice: once in a comment, once as actual placeholder
    const layoutTemplate = `<!DOCTYPE html>
<html><head><title>{{name}} — CV</title></head><body>
<!-- Profile auto-maps here because {{header}} is present -->
<div class="header-zone">{{header}}</div>
<div class="main-zone">{{main}}</div>
</body></html>`;

    const instances = [profileInstance, experienceInstance];
    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    // Both {{header}} occurrences should be replaced (comment one + actual placeholder)
    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
    // Rendered content should be present
    expect(result).toContain("Jane Doe");
    expect(result).toContain("ACME Corp");
    // Data variable {{name}} should be preserved
    expect(result).toContain("{{name}}");
  });

  it("renders profile into header zone by default when template has {{header}}", () => {
    const layoutTemplate = '<div class="header-zone">{{header}}</div><div>{{main}}</div>';
    const instances = [profileInstance, experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    expect(result).toContain("Jane Doe");
    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
  });

  it("preserves data variables while replacing zone placeholders", () => {
    const layoutTemplate = '<title>{{name}} — CV</title><div>{{header}}</div><div>{{main}}</div>';
    const instances = [profileInstance, experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    expect(result).toContain("{{name}}"); // data variable preserved
    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
  });

  it("replaces unknown zone placeholders with empty string", () => {
    const layoutTemplate = '<div>{{header}}</div><div>{{main}}</div><div>{{footer}}</div>';
    const instances = [profileInstance, experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
    expect(result).not.toContain("{{footer}}");
    expect(result).toContain("Jane Doe");
  });

  it("handles multiple zone placeholders appearing more than twice", () => {
    const layoutTemplate = '<div>{{header}}</div><span>{{header}}</span><div>{{main}}</div>';
    const instances = [profileInstance, experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
  });

  it("works with layoutConfig zones and placement", () => {
    const layoutTemplate = '<div>{{sidebar}}</div><div>{{main}}</div>';
    const layoutConfig: LayoutConfig = {
      zones: [
        { id: "sidebar", styles: { width: "30%" } },
        { id: "main", styles: { padding: "24px" } },
      ],
      placement: {
        profile: "sidebar",
        experience: "main",
      },
    };
    const instances = [profileInstance, experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate, undefined, layoutConfig);

    expect(result).not.toContain("{{sidebar}}");
    expect(result).not.toContain("{{main}}");
    expect(result).toContain("Jane Doe");
    expect(result).toContain("ACME Corp");
  });

  it("handles empty profile section — header becomes empty", () => {
    const layoutTemplate = '<div class="header-zone">{{header}}</div><div>{{main}}</div>';
    const instances: SectionInstance[] = [experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
    expect(result).toContain("ACME Corp");
  });

  it("handles disabled sections correctly", () => {
    const disabledProfile: SectionInstance = { ...profileInstance, enabled: false };
    const layoutTemplate = '<div>{{header}}</div><div>{{main}}</div>';
    const instances = [disabledProfile, experienceInstance];

    const result = renderUserTemplateHTML(instances, customizations, layoutTemplate);

    expect(result).not.toContain("{{header}}");
    expect(result).not.toContain("{{main}}");
    expect(result).toContain("ACME Corp");
  });

  it("substitutes CSS custom properties", () => {
    const layoutTemplate = '<div style="color: var(--accent);">{{header}}</div>';
    const instances = [profileInstance];
    const customizationsWithColors = { colors: { accent: "#8B0000" } };

    const result = renderUserTemplateHTML(instances, customizationsWithColors, layoutTemplate);

    expect(result).toContain("#8B0000");
    expect(result).not.toContain("var(--accent)");
  });
});
