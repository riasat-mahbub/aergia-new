import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AddSectionModal from "../sections/AddSectionModal";
import { SECTION_LABELS } from "../../lib/sections/types";

vi.mock("../common/Modal", () => ({
  default: ({ open, children }: any) => (open ? <div>{children}</div> : null),
}));

describe("AddSectionModal", () => {
  it("renders all section types when open", () => {
    render(<AddSectionModal open={true} onClose={vi.fn()} onSelect={vi.fn()} />);

    expect(screen.getByText("Add Section")).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.profile)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.experience)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.education)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.skills)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.projects)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.languages)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.certifications)).toBeDefined();
    expect(screen.getByText(SECTION_LABELS.research)).toBeDefined();
  });

  it("does not render content when closed", () => {
    render(<AddSectionModal open={false} onClose={vi.fn()} onSelect={vi.fn()} />);

    expect(screen.queryByText("Add Section")).toBeNull();
  });

  it("calls onSelect and onClose when a section type is clicked", () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();
    render(<AddSectionModal open={true} onClose={onClose} onSelect={onSelect} />);

    fireEvent.click(screen.getByText(SECTION_LABELS.skills));
    expect(onSelect).toHaveBeenCalledWith("skills");
    expect(onClose).toHaveBeenCalledOnce();
  });
});
