import { describe, it, expect, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";
import { render, fireEvent, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import BuilderPage from "../BuilderPage";
import type { LayoutConfig } from "../../lib/sections/types";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useBlocker: () => ({ state: "unblocked", proceed: vi.fn(), reset: vi.fn() }),
  };
});

interface MockCV {
  id: string;
  title: string;
  template_id: string;
  sections: unknown[];
  customizations: Record<string, unknown>;
}

const mockLoadCV = vi.fn();
const mockUpdateCV = vi.fn(() => Promise.resolve({}));
const mockPatchCurrentCV = vi.fn();
const mockCurrentCV: MockCV = {
  id: "test-id",
  title: "Test CV",
  template_id: "generic-modern",
  sections: [],
  customizations: {},
};
const mockStoreState = {
  currentCV: mockCurrentCV,
  loadCV: mockLoadCV,
  isLoading: false,
  isSaving: false,
  lastSaved: null,
  updateCV: mockUpdateCV,
  patchCurrentCV: mockPatchCurrentCV,
  error: null,
  setIsSaving: vi.fn(),
  setLastSaved: vi.fn(),
  setError: vi.fn(),
};

vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: Object.assign(vi.fn(() => mockStoreState), {
    getState: () => mockStoreState,
  }),
}));

vi.mock("../../lib/api/cvs", () => ({
  updateCV: vi.fn(() => Promise.resolve({})),
  fetchCV: vi.fn(() => Promise.resolve(mockCurrentCV)),
}));
vi.mock("../../lib/api/templates", () => ({
  fetchTemplate: vi.fn(() => Promise.resolve({
    manifest: { zones: [{ id: "main", styles: { width: "full" } }], placement: { profile: "main" } },
  })),
  fetchSystemTemplates: vi.fn(() => Promise.resolve([])),
}));
vi.mock("../../lib/api/client", () => ({ default: vi.fn() }));
vi.mock("../../lib/api/render", () => ({
  fetchRendererSupport: vi.fn(() => Promise.resolve({
    break_before: "FULL", keep_together: "FULL", keep_with_next: "FULL",
    heading_keeps_with_first: "FULL", feature_skills_inline: "FULL",
    feature_section_underline: "FULL", feature_anchor_styling: "FULL",
  })),
}));
const mockSupportState = {
  support: null,
  loaded: false,
  error: null,
  ensureLoaded: vi.fn(() => Promise.resolve()),
  retry: vi.fn(() => Promise.resolve()),
  reset: vi.fn(),
};
vi.mock("../../lib/store/supportStore", () => ({
  useSupportStore: Object.assign(vi.fn(() => mockSupportState), {
    getState: () => mockSupportState,
    setState: vi.fn(),
  }),
}));
vi.mock("../../lib/store/authStore", () => ({
  useAuthStore: vi.fn(() => ({ token: "t", user: { id: "u" }, logout: vi.fn() })),
}));
vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({
  default: ({ open, onCreate }: { open: boolean; onCreate: (zone: { id: string; label: string; styles: { width: string } }) => void }) =>
    open ? (
      <div>
        <button
          onClick={() =>
            onCreate({ id: "zone_new", label: "New", styles: { width: "40%" } })
          }
        >
          Submit New Zone
        </button>
      </div>
    ) : null,
}));
vi.mock("../../components/layout/SectionZoneView", () => ({
  default: ({ layoutConfig, onLayoutConfigChange }: { layoutConfig: LayoutConfig; onLayoutConfigChange: (next: LayoutConfig) => void }) => (
    <div data-testid="section-zone-view">
      <button
        data-testid="trigger-add-zone"
        onClick={() =>
          onLayoutConfigChange({
            zones: [
              ...layoutConfig.zones,
              { id: "zone_new", label: "New", styles: { width: "narrow" } },
            ],
            placement: layoutConfig.placement,
          })
        }
      >
        Trigger Add Zone
      </button>
      <span data-testid="zone-count">{layoutConfig.zones.length}</span>
    </div>
  ),
}));
vi.mock("../preview/UserTemplateRenderer", () => ({ default: () => <div /> }));
vi.mock("../preview/TemplateSwitcher", () => ({ default: () => <div /> }));
vi.mock("../../components/common/Modal", () => ({
  default: ({ open, children }: { open: boolean; children: ReactNode }) =>
    open ? <div>{children}</div> : null,
}));
vi.mock("../export/ExportPDFButton", () => ({ default: () => <div /> }));
vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DragOverlay: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  closestCenter: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(() => ({})),
  useSensors: vi.fn(() => []),
  useDroppable: () => ({ isOver: false, setNodeRef: vi.fn() }),
}));
vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useSortable: () => ({
    attributes: {}, listeners: {}, setNodeRef: vi.fn(),
    transform: null, transition: null, isDragging: false,
  }),
  arrayMove: (arr: unknown[], from: number, to: number) => {
    const next = [...arr];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    return next;
  },
  verticalListSortingStrategy: vi.fn(),
  horizontalListSortingStrategy: vi.fn(),
}));
vi.mock("@dnd-kit/utilities", () => ({ CSS: { Transform: { toString: () => "" } } }));
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...props }: { children: ReactNode; [k: string]: unknown }) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

function renderBuilder() {
  return render(
    <MemoryRouter initialEntries={["/dashboard/builder/test-id"]}>
      <Routes>
        <Route path="/dashboard/builder/:id" element={<BuilderPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockUpdateCV.mockClear();
  mockLoadCV.mockClear();
  mockPatchCurrentCV.mockClear();
});

describe("T-Step3: drag-drop zone authoring round-trip from customize tab", () => {
  it("renders the SectionZoneView surface in the customize tab", async () => {
    renderBuilder();
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByTestId("section-zone-view")).toBeDefined());
  });

  it("customize tab → SectionZoneView handler → setLocalCustomizations: adding a zone marks the page unsaved", async () => {
    renderBuilder();
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByTestId("section-zone-view")).toBeDefined());

    const initialZoneCount = Number(screen.getByTestId("zone-count").textContent);
    fireEvent.click(screen.getByTestId("trigger-add-zone"));
    const newZoneCount = Number(screen.getByTestId("zone-count").textContent);

    expect(newZoneCount).toBe(initialZoneCount + 1);
    expect(screen.getByText("Unsaved")).toBeDefined();
  });
});
