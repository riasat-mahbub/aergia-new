import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import LibraryPicker from "../LibraryPicker";
import { useLibraryStore } from "../../../lib/store/libraryStore";

// Preserve the real module's exports and only stub the API call we
// don't want to hit during render. Full module mocks drop helpers
// like LIBRARY_KIND_LABELS.
vi.mock("../../../lib/api/library", async () => {
  const actual =
    await vi.importActual<typeof import("../../../lib/api/library")>(
      "../../../lib/api/library",
    );
  return { ...actual, cloneLibrary: vi.fn() };
});

import { cloneLibrary } from "../../../lib/api/library";

const mockOnPick = vi.fn();
const mockOnClose = vi.fn();

function renderPicker() {
  return render(
    <LibraryPicker
      open
      onClose={mockOnClose}
      kind="education"
      onPick={mockOnPick}
    />,
  );
}

describe("LibraryPicker defensive guards", () => {
  beforeEach(() => {
    mockOnPick.mockClear();
    mockOnClose.mockClear();
    vi.mocked(cloneLibrary).mockReset();
  });

  it("renders entries from a normal entries array", () => {
    useLibraryStore.setState({
      entries: [
        {
          id: "x",
          kind: "education",
          payload: [{ title: "BS in CS" }],
          created_at: "",
          updated_at: "",
        },
      ],
      isLoading: false,
      loaded: true,
    });
    renderPicker();
    expect(screen.getByText("BS in CS")).toBeInTheDocument();
  });

  it("renders the empty state when entries is an empty array", () => {
    useLibraryStore.setState({ entries: [], isLoading: false, loaded: true });
    renderPicker();
    expect(screen.getByText(/No library entries yet/i)).toBeInTheDocument();
  });

  it("does not throw when entries is undefined (regression: dashboard crash)", () => {
    // Runtime-only state shape; the test passes undefined even though
    // the type says LibraryEntry[].
    useLibraryStore.setState({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      entries: undefined as any,
      isLoading: false,
      loaded: true,
    });
    expect(() => renderPicker()).not.toThrow();
    expect(screen.getByText(/No library entries yet/i)).toBeInTheDocument();
  });

  it("does not throw when entries is a non-array object (regression: library crash)", () => {
    useLibraryStore.setState({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      entries: { wrong: "shape" } as any,
      isLoading: false,
      loaded: true,
    });
    expect(() => renderPicker()).not.toThrow();
    expect(screen.getByText(/No library entries yet/i)).toBeInTheDocument();
  });
});
