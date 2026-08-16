import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import CvListPage from "../../pages/CvListPage";
import AppLayout from "../common/AppLayout";
import type { CVState } from "../../lib/store/cvStore";
import type { CVListItem } from "../../lib/api/cvs";

const mockFetchCVs = vi.fn();
const mockCreateCV = vi.fn();
const mockDeleteCV = vi.fn();
const mockCopyCV = vi.fn();

const mockCvStoreState = () => ({
  cvList: [],
  isLoading: false,
  fetchCVs: mockFetchCVs,
  createCV: mockCreateCV,
  deleteCV: mockDeleteCV,
  copyCV: mockCopyCV,
});
vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: vi.fn((selector) => {
    const state = mockCvStoreState();
    return selector ? selector(state) : state;
  }),
}));

vi.mock("../../lib/store/authStore", () => ({
  useAuthStore: vi.fn((selector) =>
    selector({
      logout: vi.fn(),
    })
  ),
}));

vi.mock("../../lib/api/client", () => ({
  default: { get: vi.fn().mockResolvedValue({ data: [] }) },
  __esModule: true,
}));

function renderCvList() {
  const router = createMemoryRouter(
    [{ path: "/dashboard", element: <AppLayout><CvListPage /></AppLayout> }],
    { initialEntries: ["/dashboard"] }
  );
  return render(<RouterProvider router={router} />);
}

describe("CvListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no CVs", () => {
    renderCvList();
    expect(screen.getByText(/no cvs yet/i)).toBeDefined();
  });

  it("renders CV cards when list is populated", async () => {
    const cvList: CVListItem[] = [
      {
        id: "1",
        title: "Software Engineer CV",
        template_id: "generic-modern",
        created_at: "2026-01-01",
        updated_at: "2026-01-02",
        application: {
          id: "app-1",
          company: "Example Labs",
          role: "Platform Engineer",
          status: "interview",
          generation_status: "ready",
          applied_at: "2026-01-01",
        },
      },
      {
        id: "2",
        title: "DevOps CV",
        template_id: "generic-minimal",
        created_at: "2026-01-03",
        updated_at: "2026-01-04",
      },
    ];

    vi.mocked(await import("../../lib/store/cvStore")).useCVStore.mockImplementation(
      (selector: (state: CVState) => unknown) => {
        const state = {
          cvList,
          currentCV: null,
          isLoading: false,
          isSaving: false,
          lastSaved: null,
          fetchCVs: mockFetchCVs,
          createCV: mockCreateCV,
          deleteCV: mockDeleteCV,
          copyCV: mockCopyCV,
          loadCV: vi.fn(),
          setIsSaving: vi.fn(),
          setLastSaved: vi.fn(),
          patchCurrentCV: vi.fn(),
        } satisfies CVState;
        return selector ? selector(state) : state;
      }
    );

    renderCvList();

    await waitFor(() => {
      expect(screen.getByText("Software Engineer CV")).toBeDefined();
      expect(screen.getByText("DevOps CV")).toBeDefined();
    });
    expect(screen.getByRole("heading", { name: "Application CVs" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Other CVs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Example Labs.*Platform Engineer/i })).toHaveAttribute(
      "href",
      "/dashboard/applications/app-1",
    );
    expect(screen.getByRole("heading", { name: "Other CVs" }).parentElement).toHaveTextContent("DevOps CV");
  });

  it("shows create dialog when clicking + New CV", async () => {
    renderCvList();
    const user = userEvent.setup();

    await user.click(screen.getByText("+ New CV"));

    expect(screen.getByPlaceholderText("e.g. Software Engineer CV")).toBeDefined();
    expect(screen.getByText("Create")).toBeDefined();
  });

  it("renders logout button", () => {
    renderCvList();
    expect(screen.getByTitle("Logout")).toBeDefined();
  });
});
