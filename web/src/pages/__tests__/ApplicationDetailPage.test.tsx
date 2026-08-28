import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ApplicationDetailPage from "../ApplicationDetailPage";
import { useApplicationStore } from "../../lib/store/applicationStore";
import type { Application } from "../../lib/api/applications";

vi.mock("../../lib/api/applications", () => ({
  APPLICATION_STATUSES: ["draft", "applied", "responded", "interview", "offer", "hired", "rejected", "withdrawn"],
  listApplications: vi.fn(),
  getApplication: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
  deleteApplication: vi.fn(),
  generateApplication: vi.fn(),
  recomputeApplicationRelevance: vi.fn(),
}));

vi.mock("../../lib/api/cvs", () => ({
  fetchCV: vi.fn(),
  exportPDF: vi.fn(),
  downloadPDF: vi.fn(),
}));

import * as applicationApi from "../../lib/api/applications";
import * as cvsApi from "../../lib/api/cvs";

const application: Application = {
  id: "app-1",
  cv_id: "cv-1",
  company: "Example Labs",
  role: "Platform Engineer",
  job_url: "https://example.com/job",
  job_description: "Python FastAPI distributed systems",
  notes: "Follow up next week",
  status: "applied",
  applied_at: "2026-01-01T00:00:00Z",
  generation_status: "ready",
  generation_error: null,
  extracted_keywords: [],
  relevance: {
    score: 80,
    matched_weight: 4,
    total_weight: 5,
    matched_keywords: ["Python"],
    missing_keywords: ["PostgreSQL"],
    evidence: [{ keyword: "Python", section_type: "experience", library_entry_id: "lib", source_row_id: "row", field_path: "payload[0].description", snippet: "Python systems" }],
    algorithm_version: "keyword-v1",
  },
  algorithm_version: "keyword-v1",
  fits_one_page: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

beforeEach(() => {
  useApplicationStore.setState({ applications: [], currentApplication: null, isLoading: false, isSaving: false, loaded: false });
  vi.clearAllMocks();
  vi.mocked(applicationApi.getApplication).mockResolvedValue(application);
  vi.mocked(cvsApi.fetchCV).mockResolvedValue({
    id: "cv-1",
    title: "Example Labs — Platform Engineer",
    description: "Tailored",
    template_id: "generic-minimal",
    customizations: {},
    sections: [{ type: "profile" }, { type: "experience" }, { type: "skills" }],
    extra_metadata: { selected_sources: [{ library_entry_id: "lib", source_row_id: "row" }] },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  });
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dashboard/applications/app-1"]}>
      <Routes><Route path="/dashboard/applications/:id" element={<ApplicationDetailPage />} /></Routes>
    </MemoryRouter>,
  );
}

describe("ApplicationDetailPage", () => {
  it("explains relevance, provenance, fit state, and linked CV actions", async () => {
    renderPage();

    expect(await screen.findByText("Example Labs")).toBeInTheDocument();
    expect(screen.getByText("80%", { selector: "p" })).toHaveAttribute("title", "Weighted keyword coverage of this CV against the saved job description—not an ATS or hiring probability.");
    expect(screen.getAllByText("Python").length).toBeGreaterThan(0);
    expect(screen.getByText("Missing: PostgreSQL")).toBeInTheDocument();
    expect(screen.getByText("Selected Library rows: 1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open\/edit cv/i })).toHaveAttribute("href", "/dashboard/builder/cv-1?application=app-1");
    expect(screen.getByText("Could not fit one page without rewriting content")).toBeInTheDocument();
    expect(screen.getByLabelText("Application status")).toHaveClass("w-full", "min-w-[10rem]", "sm:w-auto");
  });

  it("updates status and exports through the existing CV endpoint", async () => {
    const user = userEvent.setup();
    vi.mocked(applicationApi.updateApplication).mockResolvedValue({ ...application, status: "interview" });
    vi.mocked(cvsApi.exportPDF).mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    renderPage();

    await screen.findByText("Example Labs");
    await user.selectOptions(screen.getByLabelText("Application status"), "interview");
    await waitFor(() => expect(applicationApi.updateApplication).toHaveBeenCalledWith("app-1", { status: "interview" }));
    await user.click(screen.getByRole("button", { name: /export pdf/i }));
    await waitFor(() => expect(cvsApi.exportPDF).toHaveBeenCalledWith("cv-1"));
  });
});
