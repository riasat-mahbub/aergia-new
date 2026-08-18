import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DashboardPage from "../DashboardPage";
import type { Application } from "../../lib/api/applications";

const mockFetchCVs = vi.fn();
const mockFetchLibrary = vi.fn();
const mockFetchApplications = vi.fn();

vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: vi.fn((selector) => selector({
    cvList: [
      {
        id: "cv-1",
        title: "Platform CV",
        template_id: "generic-modern",
        created_at: "2026-01-01",
        updated_at: "2026-01-02",
      },
      {
        id: "cv-2",
        title: "Tailored CV",
        template_id: "generic-modern",
        created_at: "2026-01-01",
        updated_at: "2026-01-03",
        application: {
          id: "app-1",
          company: "Example Labs",
          role: "Platform Engineer",
          status: "interview",
          generation_status: "ready",
          applied_at: "2026-01-01",
        },
      },
    ],
    isLoading: false,
    fetchCVs: mockFetchCVs,
  })),
}));

vi.mock("../../lib/store/libraryStore", () => ({
  useLibraryStore: vi.fn((selector) => selector({
    entries: [{ id: "entry-1" }],
    loaded: true,
    fetchAll: mockFetchLibrary,
  })),
}));

const application: Application = {
  id: "app-1",
  cv_id: "cv-2",
  company: "Example Labs",
  role: "Platform Engineer",
  job_url: null,
  job_description: "Build platform tooling",
  notes: null,
  status: "interview",
  applied_at: "2026-01-01",
  generation_status: "ready",
  generation_error: null,
  extracted_keywords: [],
  relevance: {},
  algorithm_version: "1",
  fits_one_page: true,
  created_at: "2026-01-01",
  updated_at: "2026-01-02",
};

vi.mock("../../lib/store/applicationStore", () => ({
  useApplicationStore: vi.fn((selector) => selector({
    applications: [application],
    isLoading: false,
    loaded: true,
    fetchAll: mockFetchApplications,
  })),
}));

describe("DashboardPage", () => {
  it("summarizes CVs, library, and applications as separate workspace areas", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Recent CVs")).toBeInTheDocument();
    expect(screen.getByText("Platform CV")).toBeInTheDocument();
    expect(screen.getByText("Example Labs")).toBeInTheDocument();
    expect(screen.getByText("1 tailored CV in Applications")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /CVs.*1/i })).toHaveAttribute("href", "/dashboard/cvs");
    expect(screen.getByRole("link", { name: /Library.*1/i })).toHaveAttribute("href", "/dashboard/library");
    expect(screen.getByRole("link", { name: /Applications.*1/i })).toHaveAttribute("href", "/dashboard/applications");
    expect(mockFetchCVs).toHaveBeenCalled();
    expect(mockFetchApplications).not.toHaveBeenCalled();
    expect(mockFetchLibrary).not.toHaveBeenCalled();
  });
});
