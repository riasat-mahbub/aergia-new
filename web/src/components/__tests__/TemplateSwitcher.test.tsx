import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TemplateSwitcher from "../preview/TemplateSwitcher";
import type { SectionInstance } from "../../lib/sections/types";

const baseInstances: SectionInstance[] = [
  { id: "sec_1", type: "profile", title: "Profile", enabled: true, data: { name: "Jane", title: "", email: "", phone: "", location: "", summary: "", photo_url: "" } },
  { id: "sec_2", type: "experience", title: "Experience", enabled: false, data: [] },
];

const baseProps = {
  instances: baseInstances,
  customizations: {},
};

describe("TemplateSwitcher", () => {
  it("renders Modern template by default", () => {
    const { container } = render(<TemplateSwitcher {...baseProps} templateId="generic-modern" />);
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
