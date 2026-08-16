import { beforeEach, describe, expect, it, vi } from "vitest";
import { useApplicationStore } from "../applicationStore";
import type { Application } from "../../api/applications";

vi.mock("../../api/applications", () => ({
  listApplications: vi.fn(),
  getApplication: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  deleteApplication: vi.fn(),
  generateApplication: vi.fn(),
  recomputeApplicationRelevance: vi.fn(),
}));

import * as applicationApi from "../../api/applications";

const application: Application = {
  id: "app-1",
  cv_id: null,
  company: "Acme",
  role: "Engineer",
  job_url: null,
  job_description: "Python",
  notes: null,
  status: "draft",
  applied_at: null,
  generation_status: "pending",
  generation_error: null,
  extracted_keywords: [],
  relevance: {},
  algorithm_version: "keyword-v1",
  fits_one_page: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  useApplicationStore.setState({
    applications: [],
    currentApplication: null,
    isLoading: false,
    isSaving: false,
    loaded: false,
  });
  vi.clearAllMocks();
});

describe("useApplicationStore", () => {
  it("returns generated records and updates the list", async () => {
    const generated = { ...application, cv_id: "cv-1", generation_status: "ready" as const };
    vi.mocked(applicationApi.createApplication).mockResolvedValue(application);
    vi.mocked(applicationApi.generateApplication).mockResolvedValue({ application: generated, cv_id: "cv-1" });

    const created = await useApplicationStore.getState().create({ company: "Acme", role: "Engineer", job_description: "Python" });
    const result = await useApplicationStore.getState().generate(created.id);

    expect(result.cv_id).toBe("cv-1");
    expect(useApplicationStore.getState().applications[0]).toEqual(generated);
    expect(useApplicationStore.getState().currentApplication).toEqual(generated);
  });

  it("updates and removes the current application", async () => {
    const updated = { ...application, status: "applied" as const };
    useApplicationStore.setState({ applications: [application], currentApplication: application });
    vi.mocked(applicationApi.updateApplication).mockResolvedValue(updated);
    vi.mocked(applicationApi.deleteApplication).mockResolvedValue(undefined);

    await useApplicationStore.getState().update(application.id, { status: "applied" });
    expect(useApplicationStore.getState().currentApplication?.status).toBe("applied");
    await useApplicationStore.getState().remove(application.id);
    expect(useApplicationStore.getState().applications).toEqual([]);
    expect(useApplicationStore.getState().currentApplication).toBeNull();
  });
});
