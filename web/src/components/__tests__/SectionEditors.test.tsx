import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProfileEditor from "../sections/profile/ProfileEditor";
import ExperienceEditor from "../sections/experience/ExperienceEditor";
import EducationEditor from "../sections/education/EducationEditor";
import SkillsEditor from "../sections/skills/SkillsEditor";
import LanguagesEditor from "../sections/languages/LanguagesEditor";

describe("ProfileEditor", () => {
  it("renders all fields and updates on input", () => {
    const onChange = vi.fn();
    render(<ProfileEditor data={{ name: "", title: "", email: "", phone: "", location: "", summary: "", photo_url: "" }} onChange={onChange} />);

    const nameInput = screen.getByLabelText(/full name/i);
    fireEvent.change(nameInput, { target: { value: "John" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ name: "John" }));
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
});

describe("LanguagesEditor", () => {
  it("renders with proficiency dropdown", () => {
    const data = [{ id: "1", language: "English", proficiency: "Native" }];
    render(<LanguagesEditor data={data} onChange={vi.fn()} />);

    expect(screen.getByDisplayValue("English")).toBeDefined();
    expect(screen.getByDisplayValue("Native")).toBeDefined();
  });
});
