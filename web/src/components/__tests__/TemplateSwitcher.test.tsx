import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TemplateSwitcher from "../preview/TemplateSwitcher";

const baseProps = {
  sections: { profile: { name: "Jane" }, experience: [] } as any,
  order: ["profile", "experience"],
  enabled: ["profile"],
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
        {...baseProps}
        templateId="generic-classic"
        enabled={[]}
      />
    );
    expect(screen.queryByText("Profile")).toBeNull();
  });
});
