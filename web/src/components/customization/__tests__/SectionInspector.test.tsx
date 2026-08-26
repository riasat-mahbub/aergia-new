import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SectionInspector from "../SectionInspector";
import type { SectionInstance } from "../../../lib/sections/types";

const baseInstance = (overrides: Partial<SectionInstance>): SectionInstance => ({
  id: "s1",
  type: "profile",
  title: "Profile",
  enabled: true,
  data: { name: "Alex", email: "alex@example.com" },
  ...overrides,
});

describe("SectionInspector", () => {
  it("renders a mini-preview with the section title", () => {
    render(<SectionInspector instance={baseInstance({})} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getByLabelText("Profile preview")).toBeDefined();
  });

  it("renders Heading, Spacing, Typography groups for profile", () => {
    render(<SectionInspector instance={baseInstance({})} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getByText("Heading")).toBeDefined();
    expect(screen.getByText("Spacing")).toBeDefined();
    expect(screen.getByText("Typography")).toBeDefined();
  });

  it("hides Show heading / Underline heading for profile (which always hides)", () => {
    render(<SectionInspector instance={baseInstance({ type: "profile" })} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.queryByLabelText("Show heading")).toBeNull();
    expect(screen.queryByLabelText("Underline heading")).toBeNull();
  });

  it("shows Show heading for non-profile sections", () => {
    render(<SectionInspector instance={baseInstance({ type: "experience", data: [{ position: "Eng" }] })} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getByLabelText("Show heading")).toBeDefined();
  });

  it("writes subsection.section_color when the heading color changes", async () => {
    const onChange = vi.fn();
    render(<SectionInspector instance={baseInstance({})} onChange={onChange} documentAccent={null} documentBodyFont={null} />);
    const inputs = screen.getAllByPlaceholderText("#RRGGBB");
    await userEvent.type(inputs[0], "#ff0000");
    await userEvent.tab();
    const calls = onChange.mock.calls;
    expect(calls.some((c) => JSON.stringify(c[0]).includes('"section_color":"#ff0000"'))).toBe(true);
  });

  it("shows Text align for every non-profile section type (the four-type gate is gone)", () => {
    for (const type of ["experience", "education", "projects", "research", "skills", "certifications", "extras", "languages"]) {
      const inst = baseInstance({ type, data: type === "skills" ? [{ category: "X", items: ["a"] }] : [{ x: 1 }] });
      const { unmount } = render(<SectionInspector instance={inst} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
      expect(screen.getByText("Alignment")).toBeDefined();
      unmount();
    }
  });

  it("disables Text align chips with a tooltip when the section is two-column", () => {
    const inst = baseInstance({
      type: "projects",
      data: [{ name: "P" }],
      style: { policy: { entry_layout: "two-column", show_title: true, heading_divider: false, skill_variant: null } },
    });
    render(<SectionInspector instance={inst} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    const centerBtn = screen.getByRole("radio", { name: "Center" });
    expect(centerBtn).toHaveAttribute("disabled");
  });

  it("shows Page break for non-profile sections", () => {
    render(<SectionInspector instance={baseInstance({ type: "experience", data: [{ position: "X" }] })} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getByText("Page break")).toBeDefined();
    expect(screen.getByLabelText("Start on a new page")).toBeDefined();
  });

  it("writes layout.break_before when the toggle flips", async () => {
    const onChange = vi.fn();
    render(<SectionInspector instance={baseInstance({ type: "experience", data: [{ position: "X" }] })} onChange={onChange} documentAccent={null} documentBodyFont={null} />);
    await userEvent.click(screen.getByLabelText("Start on a new page"));
    const calls = onChange.mock.calls;
    expect(calls.some((c) => JSON.stringify(c[0]).includes('"break_before":true'))).toBe(true);
  });

  it("writes spacing_before when the picker changes", async () => {
    const onChange = vi.fn();
    render(<SectionInspector instance={baseInstance({ type: "experience", data: [{ position: "X" }] })} onChange={onChange} documentAccent={null} documentBodyFont={null} />);
    const tightChips = screen.getAllByRole("radio", { name: "Tight" });
    await userEvent.click(tightChips[0]);
    const calls = onChange.mock.calls;
    expect(calls.some((c) => JSON.stringify(c[0]).includes('"spacing_before":"tight"'))).toBe(true);
  });

  it("renders TypographyRow per actual field, filtering missing fields", () => {
    const inst = baseInstance({ type: "experience", data: [{ position: "Eng", company: "Acme" }] });
    render(<SectionInspector instance={inst} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getAllByText("Position").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Company").length).toBeGreaterThanOrEqual(1);
  });


  it("renders Dates group with date format select for date-bearing sections", () => {
    const inst = baseInstance({ type: "experience", data: [{ position: "Eng" }] });
    render(<SectionInspector instance={inst} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getByText("Dates")).toBeDefined();
    expect(screen.getByLabelText("Date format")).toBeDefined();
    const select = screen.getByLabelText("Date format") as HTMLSelectElement;
    expect(select.options).toHaveLength(11);
  });

  it("hides Dates group for sections that don't carry dates (profile, skills, languages, extras)", () => {
    for (const type of ["profile", "skills", "languages", "extras"] as const) {
      const { unmount } = render(
        <SectionInspector instance={baseInstance({ type })} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />
      );
      expect(screen.queryByText("Dates")).toBeNull();
      unmount();
    }
  });

  it("writes layout.date_style when the format select changes", async () => {
    const onChange = vi.fn();
    render(<SectionInspector instance={baseInstance({ type: "experience" })} onChange={onChange} documentAccent={null} documentBodyFont={null} />);
    await userEvent.selectOptions(screen.getByLabelText("Date format"), "Mon YYYY");
    const calls = onChange.mock.calls;
    expect(calls.some((c) => {
      const payload = c[0] as { layout?: { date_style?: { key?: string } } };
      return payload?.layout?.date_style?.key === "Mon YYYY";
    })).toBe(true);
  });

  it("clears layout.date_style when the format select is reset to Default", async () => {
    const onChange = vi.fn();
    render(
      <SectionInspector
        instance={baseInstance({ type: "experience", style: { layout: { date_style: { key: "Mon YYYY", rangeSep: " – " } } } } as any)}
        onChange={onChange}
        documentAccent={null}
        documentBodyFont={null}
      />
    );
    await userEvent.selectOptions(screen.getByLabelText("Date format"), "");
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0] as { layout?: { date_style?: unknown } };
    expect(lastCall?.layout?.date_style).toBeNull();
  });
  it("renders TypographyRow redirect for rich text fields", () => {
    const inst = baseInstance({ type: "experience", data: [{ position: "Eng", description: "Hello" }] });
    render(<SectionInspector instance={inst} onChange={vi.fn()} documentAccent={null} documentBodyFont={null} />);
    expect(screen.getByText(/Rich text field/i)).toBeDefined();
  });
});
