import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../api/cvs", () => ({
  fetchCVs: vi.fn(),
  fetchCV: vi.fn(),
  createCV: vi.fn(),
  deleteCV: vi.fn(),
  copyCV: vi.fn(),
}));

import * as cvsApi from "../../api/cvs";
import { useCVStore } from "../cvStore";

const mockFetchCVs = vi.mocked(cvsApi.fetchCVs);
const mockCreateCV = vi.mocked(cvsApi.createCV);
const mockDeleteCV = vi.mocked(cvsApi.deleteCV);
const mockCopyCV = vi.mocked(cvsApi.copyCV);

const fakeCVs = [
  { id: "1", title: "CV One", template_id: "generic-modern", created_at: "2026-01-01", updated_at: "2026-01-02" },
  { id: "2", title: "CV Two", template_id: "generic-classic", created_at: "2026-01-03", updated_at: "2026-01-04" },
];

describe("cvStore", () => {
  beforeEach(() => {
    useCVStore.setState({ cvList: [], currentCV: null, isLoading: false });
    vi.clearAllMocks();
  });

  describe("fetchCVs", () => {
    it("should populate cvList on success", async () => {
      mockFetchCVs.mockResolvedValueOnce(fakeCVs);

      await useCVStore.getState().fetchCVs();

      expect(useCVStore.getState().cvList).toEqual(fakeCVs);
    });

    it("should set isLoading false on error", async () => {
      mockFetchCVs.mockRejectedValueOnce(new Error("Network error"));

      await useCVStore.getState().fetchCVs();

      expect(useCVStore.getState().isLoading).toBe(false);
    });
  });

  describe("createCV", () => {
    it("should refetch CV list after creation", async () => {
      mockCreateCV.mockResolvedValueOnce({ id: "3" } as any);
      mockFetchCVs.mockResolvedValueOnce(fakeCVs);

      await useCVStore.getState().createCV("New CV");

      expect(mockCreateCV).toHaveBeenCalledWith({ title: "New CV" });
      expect(mockFetchCVs).toHaveBeenCalledOnce();
    });
  });

  describe("deleteCV", () => {
    it("should call delete and refetch", async () => {
      mockDeleteCV.mockResolvedValueOnce(undefined);
      mockFetchCVs.mockResolvedValueOnce([fakeCVs[1]]);

      await useCVStore.getState().deleteCV("1");

      expect(mockDeleteCV).toHaveBeenCalledWith("1");
      expect(mockFetchCVs).toHaveBeenCalledOnce();
    });
  });

  describe("copyCV", () => {
    it("should call copy and refetch", async () => {
      mockCopyCV.mockResolvedValueOnce({ id: "3", title: "CV One (Copy)" } as any);
      mockFetchCVs.mockResolvedValueOnce([...fakeCVs, { id: "3", title: "CV One (Copy)" } as any]);

      await useCVStore.getState().copyCV("1");

      expect(mockCopyCV).toHaveBeenCalledWith("1");
      expect(mockFetchCVs).toHaveBeenCalledOnce();
    });
  });
});
