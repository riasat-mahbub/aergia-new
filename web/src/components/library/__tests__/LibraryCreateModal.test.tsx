import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import LibraryCreateModal from "../LibraryCreateModal";

vi.mock("../../sections/SectionEditorPanel", () => ({
  default: ({ instance, mode }: { instance: { type: string }; mode?: string }) => (
    <div data-testid="section-editor" data-section-type={instance.type} data-editor-mode={mode} />
  ),
}));

describe("LibraryCreateModal", () => {
  it("creates the editor with the renderer's plural section type", () => {
    render(<LibraryCreateModal open onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: "Skills" }));

    expect(screen.getByTestId("library-create-form")).toHaveClass("w-full", "min-w-0");
    expect(screen.getByTestId("library-create-form")).not.toHaveClass("w-[min(640px,90vw)]");
    expect(screen.getByTestId("section-editor")).toHaveAttribute("data-section-type", "skills");
    expect(screen.getByTestId("section-editor")).toHaveAttribute("data-editor-mode", "section");
  });

  it("uses the compact editor mode for an existing library entry", () => {
    render(
      <LibraryCreateModal
        open
        onClose={vi.fn()}
        entry={{
          id: "library-1",
          kind: "skill",
          payload: [{ id: "skill-1", category: "Frontend", items: ["TypeScript"] }],
          created_at: "2026-01-01",
          updated_at: "2026-01-02",
        }}
      />,
    );

    expect(screen.getByTestId("section-editor")).toHaveAttribute("data-editor-mode", "library");
    expect(screen.queryByRole("button", { name: "Change type" })).not.toBeInTheDocument();
  });
});
