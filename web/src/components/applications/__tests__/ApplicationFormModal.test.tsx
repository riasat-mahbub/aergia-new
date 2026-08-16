import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ApplicationFormModal from "../ApplicationFormModal";
import { useApplicationStore } from "../../../lib/store/applicationStore";
import type { Application } from "../../../lib/api/applications";

vi.mock("../../../lib/api/applications", () => ({
  createApplication: vi.fn(),
  generateApplication: vi.fn(),
  updateApplication: vi.fn(),
  listApplications: vi.fn(),
  getApplication: vi.fn(),
  deleteApplication: vi.fn(),
  recomputeApplicationRelevance: vi.fn(),
}));

import * as applicationApi from "../../../lib/api/applications";

const pending: Application = {
  id: "app-1",
  cv_id: null,
  company: "Example Labs",
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

const ready: Application = { ...pending, cv_id: "cv-1", generation_status: "ready" };

beforeEach(() => {
  useApplicationStore.setState({ applications: [], currentApplication: null, isLoading: false, isSaving: false, loaded: false });
  vi.clearAllMocks();
});

describe("ApplicationFormModal", () => {
  it("requires the three job fields and does not ask for keywords or a source CV", () => {
    render(<ApplicationFormModal open onClose={vi.fn()} />);
    expect(screen.getByLabelText(/company/i)).toBeRequired();
    expect(screen.getByLabelText(/role/i)).toBeRequired();
    expect(screen.getByLabelText(/job description/i)).toBeRequired();
    expect(screen.queryByLabelText(/keyword|source cv/i)).toBeNull();
  });

  it("creates first, then generates from the same Done action", async () => {
    const user = userEvent.setup();
    const onGenerated = vi.fn();
    vi.mocked(applicationApi.createApplication).mockResolvedValue(pending);
    vi.mocked(applicationApi.generateApplication).mockResolvedValue({ application: ready, cv_id: "cv-1" });
    render(<ApplicationFormModal open onClose={vi.fn()} onGenerated={onGenerated} />);

    await user.type(screen.getByLabelText(/company/i), "Example Labs");
    await user.type(screen.getByLabelText(/role/i), "Engineer");
    await user.type(screen.getByLabelText(/job description/i), "Python FastAPI");
    await user.click(screen.getByRole("button", { name: "Done" }));

    expect(applicationApi.createApplication).toHaveBeenCalledWith({
      company: "Example Labs",
      role: "Engineer",
      job_description: "Python FastAPI",
      job_url: undefined,
      notes: undefined,
    });
    expect(applicationApi.generateApplication).toHaveBeenCalledWith("app-1");
    expect(onGenerated).toHaveBeenCalledWith({ application: ready, cv_id: "cv-1" });
  });
});
