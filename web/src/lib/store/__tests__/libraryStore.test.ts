import { describe, it, expect, vi, beforeEach } from "vitest";
import { useLibraryStore, selectByKind } from "../libraryStore";

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

describe("selectByKind", () => {
  it("buckets entries by their kind", () => {
    const entries = [
      { id: "1", kind: "experience" as const, payload: [], created_at: "", updated_at: "" },
      { id: "2", kind: "skill" as const, payload: [], created_at: "", updated_at: "" },
      { id: "3", kind: "experience" as const, payload: [], created_at: "", updated_at: "" },
    ];
    const buckets = selectByKind(entries);
    expect(buckets.experience).toHaveLength(2);
    expect(buckets.skill).toHaveLength(1);
    expect(buckets.education).toHaveLength(0);
  });

  it("buckets Research entries as a supported Library kind", () => {
    const buckets = selectByKind([
      { id: "r1", kind: "research", payload: [], created_at: "", updated_at: "" },
    ]);
    expect(buckets.research).toHaveLength(1);
  });

  it("silently drops entries with unknown kinds (regression: dashboard crash)", () => {
    // At runtime any string can arrive from the API (legacy data,
    // future kinds, upstream drift). The selector must not throw on
    // unknown kinds — the dashboard used to crash with
    // "buckets[e.kind] is undefined" when an entry had an unknown kind.
    const entries = [
      { id: "1", kind: "experience", payload: [], created_at: "", updated_at: "" },
      { id: "2", kind: "research", payload: [], created_at: "", updated_at: "" },
      { id: "3", kind: "extras", payload: [], created_at: "", updated_at: "" },
    ] as never;

    expect(() => selectByKind(entries)).not.toThrow();
    const buckets = selectByKind(entries);
    expect(buckets.experience).toHaveLength(1);
    // Unknown kinds are dropped, not surfaced under any known bucket.
    expect(buckets.research).toHaveLength(1);
    expect(buckets.skill).toHaveLength(0);
    expect(buckets.education).toHaveLength(0);
    expect(Object.keys(buckets).sort()).toEqual([
      "certification",
      "education",
      "experience",
      "language",
      "project",
      "research",
      "skill",
    ]);
  });
});
