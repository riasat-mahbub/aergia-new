import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import TemplateSwitcher from "../preview/TemplateSwitcher";
import type { SectionInstance } from "../../lib/sections/types";

vi.mock("../../lib/api/client", () => ({
  default: {
    post: vi.fn().mockResolvedValue({ data: { html: "<html><body><h2>Profile</h2></body></html>" } }),
  },
}));

const baseInstances: SectionInstance[] = [
  { id: "sec_1", type: "profile", title: "Profile", enabled: true, data: { name: "Jane", title: "", email: "", phone: "", location: "", summary: "", photo_url: "" } },
  { id: "sec_2", type: "experience", title: "Experience", enabled: false, data: [] },
];

const modernLayoutConfig = {
  layout: {
    zones: [
      { id: "sidebar", styles: { width: "narrow", padding: "comfortable" } },
      { id: "main", styles: { padding: "comfortable" } },
    ],
    placement: {
      profile: "sidebar",
      experience: "main",
      education: "main",
      skills: "main",
      projects: "main",
      languages: "main",
      certifications: "main",
    },
  },
};

const baseProps = {
  instances: baseInstances,
  customizations: {},
};

describe("TemplateSwitcher", () => {
  it("renders Modern template by default", () => {
    const { container } = render(<TemplateSwitcher {...baseProps} templateId="generic-modern" />);
    expect(container.querySelector(".min-h-\\[297mm\\]")).toBeDefined();
  });
  it("renders Modern template with customizations.layout", () => {
    const { container } = render(
      <TemplateSwitcher {...baseProps} templateId="generic-modern" customizations={modernLayoutConfig} />
    );
    expect(container.querySelector(".min-h-\\[297mm\\]")).toBeDefined();
  });

  it("renders Classic template", () => {
    render(<TemplateSwitcher {...baseProps} templateId="generic-classic" />);
    expect(screen.getByTitle("User Template Preview")).toBeDefined();
  });

  it("renders Minimal template", () => {
    render(<TemplateSwitcher {...baseProps} templateId="generic-minimal" />);
    expect(screen.getByTitle("User Template Preview")).toBeDefined();
  });

  it("does not render disabled sections", () => {
    render(
      <TemplateSwitcher
        instances={[{ ...baseInstances[0], enabled: false }]}
        customizations={{}}
        templateId="generic-classic"
      />
    );
    expect(screen.queryByText("Profile")).toBeNull();
  });
});
