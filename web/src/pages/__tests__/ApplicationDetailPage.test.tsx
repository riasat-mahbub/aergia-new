import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ApplicationDetailPage from "../ApplicationDetailPage";
import { useApplicationStore } from "../../lib/store/applicationStore";
import { useToastStore } from "../../lib/store/uiStore";
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

vi.mock("../../lib/api/tailoring", () => ({
  createTailoringSession: vi.fn(),
  getTailoringSessionStatus: vi.fn(),
  cancelTailoringSession: vi.fn(),
}));

import * as applicationApi from "../../lib/api/applications";
import * as cvsApi from "../../lib/api/cvs";
import * as tailoringApi from "../../lib/api/tailoring";

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
  useToastStore.setState({ toasts: [] });
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
    expect(screen.getByText("80%", { selector: "p" })).toHaveAttribute("title", "Weighted job-requirement coverage of this CV—not an ATS or hiring probability.");
    expect(screen.getByText("Python FastAPI distributed systems")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open the linked cv/i })).toHaveAttribute("href", "/dashboard/builder/cv-1?application=app-1");
    expect(screen.getByText("Selected Library rows: 1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open\/edit cv/i })).toHaveAttribute("href", "/dashboard/builder/cv-1?application=app-1");
    expect(screen.getByText("Could not fit one page without rewriting content")).toBeInTheDocument();
    expect(screen.getByLabelText("Application status")).toHaveClass("w-full", "min-w-[10rem]", "sm:w-auto");
    expect(screen.getAllByRole("button", { name: "See more" })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "Job" }).closest("section")).toHaveClass("h-60", "md:h-64");
  });

  it("expands the bounded job panel while keeping relevance analysis on the builder", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Example Labs");
    const seeMoreButtons = screen.getAllByRole("button", { name: "See more" });

    await user.click(seeMoreButtons[0]);
    expect(screen.getByRole("button", { name: "See less" })).toHaveAttribute("aria-expanded", "true");

    expect(screen.getByRole("link", { name: /open the linked cv/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open\/edit cv/i })).toBeInTheDocument();
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

  it("creates a scoped local tailoring session for the linked CV", async () => {
    const user = userEvent.setup();
    vi.mocked(tailoringApi.createTailoringSession).mockResolvedValue({
      protocol_version: 1,
      session_id: "session-1",
      application_id: "app-1",
      cv_id: "cv-1",
      code: "test-session-code",
      session_url: "http://localhost:8000/agent/tailor/session-1",
      prompt: "Use the Aergia tailoring skill for this session:\n\nhttp://localhost:8000/agent/tailor/session-1\n\nOne-time session code: test-session-code",
      status: "created",
      expires_at: "2026-08-30T20:00:00Z",
    });
    renderPage();

    await screen.findByText("Example Labs");
    await user.click(screen.getByRole("button", { name: /llm tailoring/i }));

    await waitFor(() => expect(tailoringApi.createTailoringSession).toHaveBeenCalledWith("app-1"));
    expect(screen.getByRole("status")).toHaveTextContent("test-session-code");
    expect(screen.getByRole("status")).toHaveTextContent("Copy this prompt and paste it into Codex, Claude Code, or OpenCode");
    expect(screen.getByRole("button", { name: /copy prompt/i })).toBeInTheDocument();
  });

  it("announces when the tailored CV has been applied", async () => {
    const user = userEvent.setup();
    vi.mocked(tailoringApi.createTailoringSession).mockResolvedValue({
      protocol_version: 1,
      session_id: "session-2",
      application_id: "app-1",
      cv_id: "cv-1",
      code: "test-session-code",
      session_url: "http://localhost:8000/agent/tailor/session-2",
      prompt: "Use the Aergia tailoring skill for this session",
      status: "created",
      expires_at: "2026-08-30T20:00:00Z",
    });
    vi.mocked(tailoringApi.getTailoringSessionStatus).mockResolvedValue({
      protocol_version: 1,
      session_id: "session-2",
      application_id: "app-1",
      cv_id: "cv-1",
      status: "applied",
      expires_at: "2026-08-30T20:00:00Z",
      created_at: "2026-08-30T19:45:00Z",
      exchanged_at: "2026-08-30T19:46:00Z",
      submitted_at: "2026-08-30T19:50:00Z",
      updated_at: "2026-08-30T19:50:01Z",
      attempts: 1,
      reported_gaps: [],
      result: {
        protocol_version: 1,
        session_id: "session-2",
        application_id: "app-1",
        cv_id: "cv-1",
        base_revision: 1,
        new_revision: 2,
        applied_operations: ["replace_description"],
        gaps: [],
        provenance: [],
        before_relevance: { score: 60 },
        relevance: { score: 80 },
      },
    });
    renderPage();

    await screen.findByText("Example Labs");
    await user.click(screen.getByRole("button", { name: /llm tailoring/i }));

    await waitFor(() => expect(useToastStore.getState().toasts).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          message: "Your tailored CV is ready. Relevance has been updated.",
          type: "success",
        }),
      ]),
    ));
    expect(screen.queryByRole("button", { name: /copy prompt/i })).not.toBeInTheDocument();
    expect(screen.getByText("Tailored CV ready")).toBeInTheDocument();
    expect(screen.getByText("Relevance: 60% → 80%")).toBeInTheDocument();
  });
});
