import { describe, it, expect, vi, beforeEach } from "vitest";
import { useLibraryStore } from "../libraryStore";

vi.mock("../../api/library", () => ({
  listLibrary: vi.fn(),
  createLibrary: vi.fn(),
  updateLibrary: vi.fn(),
  deleteLibrary: vi.fn(),
  cloneLibrary: vi.fn(),
  promoteCvToLibrary: vi.fn(),
}));

import * as libraryApi from "../../api/library";

describe("useLibraryStore", () => {
  beforeEach(() => {
    useLibraryStore.setState({ entries: [], isLoading: false, loaded: false });
    vi.clearAllMocks();
  });

  it("fetchAll populates entries and flips loaded", async () => {
    const entries = [
      { id: "a", kind: "experience" as const, payload: [], created_at: "x", updated_at: "x" },
    ];
    vi.mocked(libraryApi.listLibrary).mockResolvedValue(entries as never);

    await useLibraryStore.getState().fetchAll();

    const state = useLibraryStore.getState();
    expect(state.entries).toEqual(entries);
    expect(state.isLoading).toBe(false);
    expect(state.loaded).toBe(true);
  });

  it("create appends the new entry and returns it", async () => {
    const created = { id: "x", kind: "skill" as const, payload: [{ name: "Py" }], created_at: "t", updated_at: "t" };
    vi.mocked(libraryApi.createLibrary).mockResolvedValue(created as never);

    const result = await useLibraryStore.getState().create("skill", [{ name: "Py" }]);

    expect(result.id).toBe("x");
    expect(useLibraryStore.getState().entries).toHaveLength(1);
  });

  it("update replaces the matching entry", async () => {
    const existing = { id: "x", kind: "skill" as const, payload: [{ name: "Py" }], created_at: "t", updated_at: "t" };
    const updated = { ...existing, payload: [{ name: "Rust" }] };
    useLibraryStore.setState({ entries: [existing as never] });
    vi.mocked(libraryApi.updateLibrary).mockResolvedValue(updated as never);

    await useLibraryStore.getState().update("x", [{ name: "Rust" }]);

    expect(useLibraryStore.getState().entries[0].payload).toEqual([{ name: "Rust" }]);
  });

  it("remove drops the entry", async () => {
    const entry = { id: "x", kind: "skill" as const, payload: [], created_at: "t", updated_at: "t" };
    useLibraryStore.setState({ entries: [entry as never] });
    vi.mocked(libraryApi.deleteLibrary).mockResolvedValue(undefined);

    await useLibraryStore.getState().remove("x");

    expect(useLibraryStore.getState().entries).toHaveLength(0);
  });
});
