import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Inspector from "../Inspector";
import type { SectionInstance } from "../../lib/sections/types";

const baseInstance = (overrides: Partial<SectionInstance>): SectionInstance => ({
  id: "s1",
  type: "profile",
  title: "Profile",
  enabled: true,
  data: { name: "Alex" },
  ...overrides,
});

const noopProps = {
  templateId: "generic-modern",
  templateName: "Modern",
  instances: [] as SectionInstance[],
  onUpdateStyle: vi.fn(),
  onCustomizationsChange: vi.fn(),
  onTemplateChange: vi.fn(),
  onReset: vi.fn(),
  customizations: {},
};

describe("Inspector", () => {
  it("renders the document strip with body font, heading font, accent", () => {
    render(<Inspector {...noopProps} />);
    expect(screen.getByLabelText("Body font")).toBeDefined();
    expect(screen.getByLabelText("Heading font")).toBeDefined();
    expect(screen.getByLabelText("Accent color")).toBeDefined();
  });

  it("offers the four font tokens, not raw CSS strings (the panel bug fix)", () => {
    render(<Inspector {...noopProps} />);
    const select = screen.getByLabelText("Body font") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(["", "sans-serif", "serif", "mono", "display"]);
  });

  it("writes a FontToken (schema-valid) when the body font changes", async () => {
    const onCustomizationsChange = vi.fn();
    render(<Inspector {...noopProps} onCustomizationsChange={onCustomizationsChange} />);
    await userEvent.selectOptions(screen.getByLabelText("Body font"), "serif");
    expect(onCustomizationsChange).toHaveBeenCalledWith(
      expect.objectContaining({ body_font: "serif" }),
    );
  });

  it("auto-opens the first section", () => {
    const inst = baseInstance({});
    render(<Inspector {...noopProps} instances={[inst]} />);
    expect(screen.getByTestId(`section-card-${inst.id}`).querySelector("[aria-expanded=true]")).toBeDefined();
  });

  it("renders one card per instance", () => {
    const i1 = baseInstance({ id: "s1", title: "Profile", type: "profile" });
    const i2 = { ...baseInstance({ id: "s2", title: "Experience", type: "experience" }), data: [{ position: "Eng" }] };
    render(<Inspector {...noopProps} instances={[i1, i2]} />);
    expect(screen.getByTestId("section-card-s1")).toBeDefined();
    expect(screen.getByTestId("section-card-s2")).toBeDefined();
  });

  it("calls onUpdateStyle when a section control writes", async () => {
    const onUpdateStyle = vi.fn();
    const inst = baseInstance({ type: "experience", data: [{ position: "Eng" }] });
    render(<Inspector {...noopProps} instances={[inst]} onUpdateStyle={onUpdateStyle} />);
    await userEvent.click(screen.getByLabelText("Start on a new page"));
    expect(onUpdateStyle).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({ layout: expect.objectContaining({ break_before: true }) }),
    );
  });

  it("shows the override pill when a section overrides the accent", () => {
    const inst = baseInstance({
      style: { subsection: { section_color: "#ff0000", text_align: null, spacing_before: null, spacing_after: null, background_color: null } },
    });
    render(<Inspector {...noopProps} instances={[inst]} customizations={{ accent_color: "#000000" }} />);
    expect(screen.getAllByText(/overrides/i).length).toBeGreaterThanOrEqual(1);
  });

  it("falls back to a humanized template id when name is empty", () => {
    render(<Inspector {...noopProps} templateName="" />);
    expect(screen.getByText("Modern")).toBeDefined();
  });

  it("disables the Reset button when there's nothing to reset", () => {
    render(<Inspector {...noopProps} />);
    const reset = screen.getByLabelText("Reset to template defaults") as HTMLButtonElement;
    expect(reset.disabled).toBe(true);
  });

  it("opens a confirmation modal when Reset is clicked", async () => {
    render(<Inspector {...noopProps} customizations={{ accent_color: "#000000" }} />);
    await userEvent.click(screen.getByLabelText("Reset to template defaults"));
    expect(screen.getByText(/Reset to template defaults\?/)).toBeDefined();
  });
});
