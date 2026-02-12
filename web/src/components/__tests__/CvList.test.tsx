import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import CvListPage from "../../pages/CvListPage";

const mockFetchCVs = vi.fn();
const mockCreateCV = vi.fn();
const mockDeleteCV = vi.fn();
const mockCopyCV = vi.fn();

vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: vi.fn((selector) =>
    selector({
      cvList: [],
      isLoading: false,
      fetchCVs: mockFetchCVs,
      createCV: mockCreateCV,
      deleteCV: mockDeleteCV,
      copyCV: mockCopyCV,
    })
  ),
}));

vi.mock("../../lib/store/authStore", () => ({
  useAuthStore: vi.fn((selector) =>
    selector({
      logout: vi.fn(),
    })
  ),
}));

function renderCvList() {
  return render(
    <BrowserRouter>
      <CvListPage />
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
      (selector: any) => selector({
        cvList,
        isLoading: false,
        fetchCVs: mockFetchCVs,
        createCV: mockCreateCV,
        deleteCV: mockDeleteCV,
        copyCV: mockCopyCV,
      })
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

    expect(screen.getByPlaceholderText("CV title...")).toBeDefined();
    expect(screen.getByText("Create")).toBeDefined();
  });

  it("renders logout button", () => {
    renderCvList();
    expect(screen.getByText("Logout")).toBeDefined();
  });
});
