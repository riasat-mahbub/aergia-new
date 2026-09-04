import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LibraryCreateModal from "../LibraryCreateModal";
describe("LibraryCreateModal editor defaults", () => {
  beforeEach(() => {
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the skills editor with complete default group data", async () => {
    const user = userEvent.setup();
    render(<LibraryCreateModal open onClose={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Skills" }));
    await user.click(screen.getByText("New Skill Group"));

    expect(screen.getByPlaceholderText("Category (e.g. Frontend)"))
      .toBeInTheDocument();
  });

  it("uses complete defaults when an initial library kind is provided", () => {
    render(<LibraryCreateModal open onClose={vi.fn()} initialKind="skill" />);

    expect(screen.getByText("New Skill Group")).toBeInTheDocument();
  });

  it("renders an existing entry as a field-only edit form", () => {
    render(
      <LibraryCreateModal
        open
        onClose={vi.fn()}
        entry={{
          id: "library-1",
          kind: "skill",
          payload: [{ id: "skill-1", category: "Frontend", items: [] }],
          created_at: "2026-01-01",
          updated_at: "2026-01-02",
        }}
      />,
    );

    expect(screen.getByDisplayValue("Frontend")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add skill group/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Remove")).not.toBeInTheDocument();
    expect(screen.queryByText("Change type")).not.toBeInTheDocument();
  });
});
