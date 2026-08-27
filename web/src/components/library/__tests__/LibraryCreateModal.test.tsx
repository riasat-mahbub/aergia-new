import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LibraryCreateModal from "../LibraryCreateModal";

vi.mock("../../sections/SectionEditorPanel", () => ({
  default: ({ instance }: { instance: { type: string } }) => (
    <div data-testid="section-editor" data-section-type={instance.type} />
  ),
}));

describe("LibraryCreateModal", () => {
  it("creates the editor with the renderer's plural section type", () => {
    render(<LibraryCreateModal open onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Skills" }));

    expect(screen.getByTestId("section-editor")).toHaveAttribute("data-section-type", "skills");
  });
});
