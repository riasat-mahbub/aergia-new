import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AddToLibraryButton from "../AddToLibraryButton";
import { addEntryToLibrary } from "../../../lib/api/library";

vi.mock("../../../lib/api/library", () => ({
  addEntryToLibrary: vi.fn(),
}));

vi.mock("../../../lib/store/libraryStore", () => ({
  useLibraryStore: (selector: (state: { fetchAll: () => Promise<void> }) => unknown) =>
    selector({ fetchAll: vi.fn().mockResolvedValue(undefined) }),
}));

vi.mock("../../../lib/store/uiStore", () => ({
  useToastStore: (selector: (state: { addToast: (...args: unknown[]) => void }) => unknown) =>
    selector({ addToast: vi.fn() }),
}));

describe("AddToLibraryButton", () => {
  beforeEach(() => {
    vi.mocked(addEntryToLibrary).mockReset();
  });

  it("posts the selected CV entry when the confirmation is accepted", async () => {
    vi.mocked(addEntryToLibrary).mockResolvedValue({
      library_id: "library-1",
      entry_id: "library-entry-1",
      created: true,
    });

    const user = userEvent.setup();
    const buttonProps = {
      cvId: "cv-1",
      sectionId: "section-exp",
      entryId: "experience-1",
      entryLabel: "Acme",
      kind: "experience" as const,
      entryData: {
        id: "experience-1",
        company: "Current Company",
        position: "Lead Engineer",
      },
    };
    render(<AddToLibraryButton {...buttonProps} />);

    await user.click(screen.getByRole("button", { name: /add to library/i }));
    const confirmButtons = screen.getAllByRole("button", { name: /add to library/i });
    await user.click(confirmButtons[confirmButtons.length - 1]);

    expect(addEntryToLibrary).toHaveBeenCalledWith(
      "cv-1",
      "section-exp",
      "experience-1",
      { kind: "experience", entry: buttonProps.entryData },
    );
  });
});
