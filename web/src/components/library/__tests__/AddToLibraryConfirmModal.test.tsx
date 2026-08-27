import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AddToLibraryConfirmModal from "../AddToLibraryConfirmModal";

describe("AddToLibraryConfirmModal", () => {
  const onConfirm = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    onConfirm.mockReset();
    onClose.mockReset();
  });

  it("renders no content when closed (inner body mounts only when open)", () => {
    const { container } = render(
      <AddToLibraryConfirmModal
        open={false}
        onClose={onClose}
        onConfirm={onConfirm}
      />,
    );
    expect(container.textContent).not.toContain("Add to library");
  });

  it("shows title, entry label, and copy when open", () => {
    render(
      <AddToLibraryConfirmModal
        open
        onClose={onClose}
        onConfirm={onConfirm}
        entryLabel="BS in CS"
      />,
    );
    expect(screen.getByRole("heading", { name: /add to library/i })).toBeInTheDocument();
    expect(screen.getByText(/BS in CS/)).toBeInTheDocument();
    expect(screen.getByText(/BS in CS/)).toBeInTheDocument();
  });

  it("falls back to generic copy when no entryLabel is given", () => {
    render(
      <AddToLibraryConfirmModal open onClose={onClose} onConfirm={onConfirm} />,
    );
    expect(screen.getByText(/Copy this entry to your Library/)).toBeInTheDocument();
  });

  it("calls onConfirm when Add to library is clicked", async () => {
    const user = userEvent.setup();
    onConfirm.mockResolvedValue(undefined);
    render(
      <AddToLibraryConfirmModal open onClose={onClose} onConfirm={onConfirm} />,
    );
    await user.click(screen.getByRole("button", { name: /add to library/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onClose when Cancel is clicked", async () => {
    const user = userEvent.setup();
    render(
      <AddToLibraryConfirmModal open onClose={onClose} onConfirm={onConfirm} />,
    );
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
