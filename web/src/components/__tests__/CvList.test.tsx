import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import CvListPage from "../../pages/CvListPage";
import AppLayout from "../common/AppLayout";

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
  return render(
    <BrowserRouter>
      <AppLayout>
        <CvListPage />
      </AppLayout>
    </BrowserRouter>
  );
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
    const cvList = [
      { id: "1", title: "Software Engineer CV", template_id: "generic-modern", created_at: "2026-01-01", updated_at: "2026-01-02" },
      { id: "2", title: "DevOps CV", template_id: "generic-minimal", created_at: "2026-01-03", updated_at: "2026-01-04" },
    ];

    vi.mocked(await import("../../lib/store/cvStore")).useCVStore.mockImplementation(
      (selector: any) => {
        const state = { cvList, isLoading: false, fetchCVs: mockFetchCVs, createCV: mockCreateCV, deleteCV: mockDeleteCV, copyCV: mockCopyCV };
        return selector ? selector(state) : state;
      }
    );

    renderCvList();

    await waitFor(() => {
      expect(screen.getByText("Software Engineer CV")).toBeDefined();
      expect(screen.getByText("DevOps CV")).toBeDefined();
    });
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
