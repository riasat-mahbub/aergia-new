import type { ProfileData } from "../../lib/sections/types";

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProfileEditor from "../sections/profile/ProfileEditor";
import ExperienceEditor from "../sections/experience/ExperienceEditor";
import EducationEditor from "../sections/education/EducationEditor";
import SkillsEditor from "../sections/skills/SkillsEditor";
import LanguagesEditor from "../sections/languages/LanguagesEditor";
import ResearchEditor from "../sections/research/ResearchEditor";

describe("ProfileEditor", () => {
  const baseData: ProfileData = {
    name: "",
    title: "",
    email: "",
    email_link: true,
    phone: "",
    location: "",
    site_text: "",
    site_url: "",
    summary: "",
    photo_url: "",
    social_links: [],
  };

  it("renders all fields and updates on input", () => {
    const onChange = vi.fn();
    render(<ProfileEditor data={baseData} onChange={onChange} />);

    const nameInput = screen.getAllByRole("textbox")[0];
    fireEvent.change(nameInput, { target: { value: "John" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ name: "John" }));
  });

  it("checks the email_link toggle by default", () => {
    render(<ProfileEditor data={{ ...baseData, email_link: true }} onChange={vi.fn()} />);
    const checkbox = screen.getByRole("checkbox", { name: /make email clickable/i });
    expect(checkbox).toBeChecked();
  });

  it("toggles email_link off and reports the change", () => {
    const onChange = vi.fn();
    render(<ProfileEditor data={baseData} onChange={onChange} />);

    const checkbox = screen.getByRole("checkbox", { name: /make email clickable/i });
    fireEvent.click(checkbox);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ email_link: false }));
  });

  it("updates site_url on input", () => {
    const onChange = vi.fn();
    render(<ProfileEditor data={baseData} onChange={onChange} />);

    const siteUrlInput = screen.getByPlaceholderText("https://example.com");
    fireEvent.change(siteUrlInput, { target: { value: "https://x.dev" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ site_url: "https://x.dev" }));
  });
});

describe("ExperienceEditor", () => {
  it("renders add button and allows adding entries", () => {
    const onChange = vi.fn();
    render(<ExperienceEditor data={[]} onChange={onChange} />);

    fireEvent.click(screen.getByText(/add experience/i));
    expect(onChange).toHaveBeenCalled();
  });

  it("renders existing entries", () => {
    const onChange = vi.fn();
    const data = [{ id: "1", company: "Acme", position: "Dev", start_date: "2020", end_date: null, current: true, location: "NYC", description: "Work" }];
    render(<ExperienceEditor data={data} onChange={onChange} />);

    fireEvent.click(screen.getByText("Acme"));
    expect(screen.getByDisplayValue("Acme")).toBeDefined();
  });
});

describe("EducationEditor", () => {
  it("renders add button", () => {
    render(<EducationEditor data={[]} onChange={vi.fn()} />);
    expect(screen.getByText(/add education/i)).toBeDefined();
  });
});

describe("SkillsEditor", () => {
  it("renders add button", () => {
    render(<SkillsEditor data={[]} onChange={vi.fn()} />);
    expect(screen.getByText(/add skill group/i)).toBeDefined();
  });

  it("removes an individual skill without removing its category", () => {
    const onChange = vi.fn();
    render(
      <SkillsEditor
        data={[{ id: "skills-1", category: "Backend", items: ["Python", "FastAPI"] }]}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByText("Backend"));
    fireEvent.click(screen.getByRole("button", { name: "Remove Python" }));

    expect(onChange).toHaveBeenLastCalledWith([
      { id: "skills-1", category: "Backend", items: ["FastAPI"] },
    ]);
  });
});

describe("LanguagesEditor", () => {
  it("renders with proficiency dropdown", () => {
    const data = [{ id: "1", language: "English", proficiency: "Native" }];
    render(<LanguagesEditor data={data} onChange={vi.fn()} />);

    fireEvent.click(screen.getByText("English"));
    expect(screen.getByDisplayValue("English")).toBeDefined();
    expect(screen.getByDisplayValue("Native")).toBeDefined();
  });
});

describe("ResearchEditor", () => {
  it("renders the add button and adds a new entry", () => {
    const onChange = vi.fn();
    render(<ResearchEditor data={[]} onChange={onChange} />);

    fireEvent.click(screen.getByText(/add research paper/i));
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0] as Array<{ title: string }>;
    expect(lastCall).toHaveLength(1);
    expect(lastCall[0].title).toBe("");
  });

  it("opens an existing paper and edits title + link text", () => {
    const onChange = vi.fn();
    const data = [
      {
        id: "r1",
        title: "Old Title",
        paper_url: "https://doi.org/10.0000/aergia.2026",
        paper_link_text: "DOI",
        description: "Findings",
        publication_date: "2026-06",
        publication_value: "NeurIPS 2024",
      },
    ];
    render(<ResearchEditor data={data} onChange={onChange} />);

    // Accordion title reflects the existing entry's title.
    fireEvent.click(screen.getByText("Old Title"));

    // Title and link-text inputs are both rendered with the existing values.
    expect(screen.getByDisplayValue("Old Title")).toBeDefined();
    expect(screen.getByDisplayValue("DOI")).toBeDefined();

    // Each input change fires onChange with the entry carrying the new value
    // for that field. (The data prop is not updated by the parent between
    // events, so we don't assert both edits in one call.)
    const titleInput = screen.getByDisplayValue("Old Title");
    fireEvent.change(titleInput, { target: { value: "Verified Paper" } });
    const callsAfterTitle = onChange.mock.calls.map((c) => c[0]);
    expect(callsAfterTitle[callsAfterTitle.length - 1][0].title).toBe("Verified Paper");

    const linkTextInput = screen.getByDisplayValue("DOI");
    fireEvent.change(linkTextInput, { target: { value: "arXiv" } });
    const callsAfterLink = onChange.mock.calls.map((c) => c[0]);
    expect(callsAfterLink[callsAfterLink.length - 1][0].paper_link_text).toBe("arXiv");
  });
});
