import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TemplateSwitcher from "../preview/TemplateSwitcher";
import type { SectionInstance, LayoutConfig } from "../../lib/sections/types";

const baseInstances: SectionInstance[] = [
  { id: "sec_1", type: "profile", title: "Profile", enabled: true, data: { name: "Jane", title: "", email: "", phone: "", location: "", summary: "", photo_url: "" } },
  { id: "sec_2", type: "experience", title: "Experience", enabled: false, data: [] },
];

const modernLayoutConfig: LayoutConfig = {
  zones: [
    { id: "sidebar", styles: { width: "30%", padding: "24px" } },
    { id: "main", styles: { padding: "24px" } },
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

  it("renders Modern template with layoutConfig", () => {
    const { container } = render(
      <TemplateSwitcher {...baseProps} templateId="generic-modern" layoutConfig={modernLayoutConfig} />
    );
    expect(container.querySelector(".min-h-\\[297mm\\]")).toBeDefined();
  });

  it("renders Classic template", () => {
    render(<TemplateSwitcher {...baseProps} templateId="generic-classic" />);
    expect(screen.getByText("Profile")).toBeDefined();
  });

  it("renders Minimal template", () => {
    render(<TemplateSwitcher {...baseProps} templateId="generic-minimal" />);
    expect(screen.getByText("Profile")).toBeDefined();
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
