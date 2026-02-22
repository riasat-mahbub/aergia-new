import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../api/cvs", () => ({
  fetchCVs: vi.fn(),
  fetchCV: vi.fn(),
  createCV: vi.fn(),
  updateCV: vi.fn(),
  deleteCV: vi.fn(),
  copyCV: vi.fn(),
}));

import * as cvsApi from "../../api/cvs";
import { useCVStore } from "../cvStore";

const mockUpdateCV = vi.mocked(cvsApi.updateCV);
const mockFetchCV = vi.mocked(cvsApi.fetchCV);

const profileInstance = {
  id: "sec_profile",
  type: "profile",
  title: "Profile",
  enabled: true,
  data: { name: "", title: "", email: "", phone: "", location: "", summary: "", photo_url: "" },
};

const experienceInstance = {
  id: "sec_experience",
  type: "experience",
  title: "Experience",
  enabled: true,
  data: [],
};

const mockCV = {
  id: "cv_1",
  title: "Test CV",
  description: null,
  template_id: "generic-modern",
  customizations: {},
  sections: [profileInstance, experienceInstance],
  extra_metadata: {},
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("sectionInstanceStore (cvStore instance CRUD)", () => {
  beforeEach(() => {
    useCVStore.setState({ cvList: [], currentCV: mockCV as any, isLoading: false });
    vi.clearAllMocks();
    mockFetchCV.mockResolvedValue(mockCV as any);
  });

  describe("addInstance", () => {
    it("should add a new instance and update CV", async () => {
      mockUpdateCV.mockResolvedValueOnce(mockCV as any);
      mockFetchCV.mockResolvedValueOnce({
        ...mockCV,
        sections: [...mockCV.sections, { id: "sec_skills", type: "skills", title: "Skills", enabled: true, data: [] }],
      } as any);

      await useCVStore.getState().addInstance("skills");

      expect(mockUpdateCV).toHaveBeenCalledOnce();
      const updateArg = mockUpdateCV.mock.calls[0][1];
      expect((updateArg as any).sections.length).toBe(3);
      expect((updateArg as any).sections[2].type).toBe("skills");
      expect(mockFetchCV).toHaveBeenCalledWith("cv_1");
    });
  });

  describe("removeInstance", () => {
    it("should remove an instance by id", async () => {
      mockUpdateCV.mockResolvedValueOnce(mockCV as any);
      mockFetchCV.mockResolvedValueOnce({
        ...mockCV,
        sections: [experienceInstance],
      } as any);

      await useCVStore.getState().removeInstance("sec_profile");

      expect(mockUpdateCV).toHaveBeenCalledOnce();
      const updateArg = mockUpdateCV.mock.calls[0][1];
      expect((updateArg as any).sections.length).toBe(1);
      expect((updateArg as any).sections[0].id).toBe("sec_experience");
    });
  });

  describe("reorderInstances", () => {
    it("should reorder instances by provided ids", async () => {
      mockUpdateCV.mockResolvedValueOnce(mockCV as any);
      mockFetchCV.mockResolvedValueOnce({
        ...mockCV,
        sections: [experienceInstance, profileInstance],
      } as any);

      await useCVStore.getState().reorderInstances(["sec_experience", "sec_profile"]);

      expect(mockUpdateCV).toHaveBeenCalledOnce();
      const updateArg = mockUpdateCV.mock.calls[0][1];
      const sections = (updateArg as any).sections;
      expect(sections[0].id).toBe("sec_experience");
      expect(sections[1].id).toBe("sec_profile");
    });
  });

  describe("toggleInstance", () => {
    it("should toggle enabled state", async () => {
      mockUpdateCV.mockResolvedValueOnce(mockCV as any);
      mockFetchCV.mockResolvedValueOnce({
        ...mockCV,
        sections: [{ ...profileInstance, enabled: false }, experienceInstance],
      } as any);

      await useCVStore.getState().toggleInstance("sec_profile");

      expect(mockUpdateCV).toHaveBeenCalledOnce();
      const updateArg = mockUpdateCV.mock.calls[0][1];
      const sections = (updateArg as any).sections;
      expect(sections[0].enabled).toBe(false);
      expect(sections[1].enabled).toBe(true);
    });
  });

  describe("renameInstance", () => {
    it("should update instance title", async () => {
      mockUpdateCV.mockResolvedValueOnce(mockCV as any);
      mockFetchCV.mockResolvedValueOnce({
        ...mockCV,
        sections: [{ ...profileInstance, title: "New Profile Title" }, experienceInstance],
      } as any);

      await useCVStore.getState().renameInstance("sec_profile", "New Profile Title");

      expect(mockUpdateCV).toHaveBeenCalledOnce();
      const updateArg = mockUpdateCV.mock.calls[0][1];
      const sections = (updateArg as any).sections;
      expect(sections[0].title).toBe("New Profile Title");
    });
  });

  describe("updateInstanceData", () => {
    it("should update instance data", async () => {
      const newData = { name: "John", title: "Dev", email: "john@example.com", phone: "", location: "", summary: "", photo_url: "" };
      mockUpdateCV.mockResolvedValueOnce(mockCV as any);
      mockFetchCV.mockResolvedValueOnce({
        ...mockCV,
        sections: [{ ...profileInstance, data: newData }, experienceInstance],
      } as any);

      await useCVStore.getState().updateInstanceData("sec_profile", newData);

      expect(mockUpdateCV).toHaveBeenCalledOnce();
      const updateArg = mockUpdateCV.mock.calls[0][1];
      const sections = (updateArg as any).sections;
      expect(sections[0].data.name).toBe("John");
      expect(sections[0].data.title).toBe("Dev");
    });
  });
});
