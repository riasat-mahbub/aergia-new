import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import ApplicationsPage from "../ApplicationsPage";
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

import * as applicationApi from "../../lib/api/applications";

const ready: Application = {
  id: "ready-1",
  cv_id: "cv-1",
  company: "Example Labs",
  role: "Platform Engineer",
  job_url: null,
  job_description: "Python FastAPI",
  notes: null,
  status: "interview",
  applied_at: "2026-01-01T00:00:00Z",
  generation_status: "ready",
  generation_error: null,
  extracted_keywords: [],
  relevance: {
    score: 75,
    matched_weight: 3,
    total_weight: 4,
    matched_keywords: ["Python"],
    missing_keywords: ["FastAPI"],
    evidence: [],
    algorithm_version: "keyword-v1",
  },
  algorithm_version: "keyword-v1",
  fits_one_page: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

const pending: Application = {
  ...ready,
  id: "pending-1",
  cv_id: null,
  company: "Pending Co",
  role: "Engineer",
  status: "draft",
  generation_status: "pending",
  relevance: {},
  fits_one_page: null,
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}

beforeEach(() => {
  useApplicationStore.setState({ applications: [], currentApplication: null, isLoading: false, isSaving: false, loaded: false });
  vi.clearAllMocks();
});

describe("ApplicationsPage", () => {
  it("renders relevance, linked CV, fit state, and status filters", async () => {
    vi.mocked(applicationApi.listApplications).mockResolvedValue([ready]);
    render(<MemoryRouter><ApplicationsPage /></MemoryRouter>);

    expect(await screen.findByText("Example Labs")).toBeInTheDocument();
    expect(screen.getByText("Relevance 75%")).toBeInTheDocument();
    expect(screen.getByText("One-page fit")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view application/i })).toHaveAttribute("href", "/dashboard/applications/ready-1");
    expect(screen.getByText("CV ready")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toHaveClass("w-full", "min-w-[10rem]", "sm:w-auto");
  });

  it("filters cards by status and retries pending generation", async () => {
    const user = userEvent.setup();
    vi.mocked(applicationApi.listApplications).mockResolvedValue([ready, pending]);
    vi.mocked(applicationApi.generateApplication).mockResolvedValue({ application: { ...pending, cv_id: "cv-2", generation_status: "ready" }, cv_id: "cv-2" });
    render(<MemoryRouter initialEntries={["/dashboard/applications"]}><ApplicationsPage /><LocationProbe /></MemoryRouter>);

    expect(await screen.findByText("Pending Co")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Status"), "draft");
    expect(screen.queryByText("Example Labs")).toBeNull();
    expect(screen.getByText("Pending Co")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate cv/i }));
    await waitFor(() => expect(applicationApi.generateApplication).toHaveBeenCalledWith("pending-1"));
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/dashboard/applications/pending-1"));
  });
});
