import { describe, it, expect, vi, beforeEach } from "vitest";
import { useSupportStore } from "../supportStore";
import * as renderApi from "../../api/render";

vi.mock("../../api/render", () => ({ fetchRendererSupport: vi.fn() }));

const FULL_SUPPORT = {
  break_before: "FULL",
  keep_with_next: "FULL",
  keep_together: "FULL",
  keep_entry_together: "FULL",
  heading_keeps_with_first: "FULL",
  feature_skills_inline: "FULL",
  feature_section_underline: "FULL",
  feature_anchor_styling: "FULL",
} as const;

describe("supportStore", () => {
  beforeEach(() => {
    useSupportStore.getState().reset();
    vi.clearAllMocks();
  });

  it("ensureLoaded populates support on first call", async () => {
    vi.mocked(renderApi.fetchRendererSupport).mockResolvedValueOnce(FULL_SUPPORT);
    await useSupportStore.getState().ensureLoaded();
    expect(useSupportStore.getState().loaded).toBe(true);
    expect(useSupportStore.getState().support?.break_before).toBe("FULL");
  });

  it("ensureLoaded does not refetch on second call", async () => {
    vi.mocked(renderApi.fetchRendererSupport).mockResolvedValueOnce(FULL_SUPPORT);
    await useSupportStore.getState().ensureLoaded();
    await useSupportStore.getState().ensureLoaded();
    expect(renderApi.fetchRendererSupport).toHaveBeenCalledTimes(1);
  });

  it("failures store support=null with error populated (fail-open)", async () => {
    vi.mocked(renderApi.fetchRendererSupport).mockRejectedValueOnce(new Error("network"));
    await useSupportStore.getState().ensureLoaded();
    expect(useSupportStore.getState().support).toBeNull();
    expect(useSupportStore.getState().error).toMatch(/network/);
    expect(useSupportStore.getState().loaded).toBe(true);
  });

  it("retry refetches after a failure", async () => {
    vi.mocked(renderApi.fetchRendererSupport)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(FULL_SUPPORT);
    await useSupportStore.getState().ensureLoaded();
    await useSupportStore.getState().retry();
    expect(useSupportStore.getState().support?.break_before).toBe("FULL");
    expect(useSupportStore.getState().error).toBeNull();
  });
});
