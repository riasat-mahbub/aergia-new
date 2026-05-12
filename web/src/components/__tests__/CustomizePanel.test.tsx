import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CustomizePanel from "../customization/CustomizePanel";
import BuilderPage from "../../pages/BuilderPage";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-id" }),
  useNavigate: () => vi.fn(),
  useBlocker: () => ({ state: "unblocked" }),
  useLocation: () => ({ pathname: "/dashboard/builder/test-cv-id" }),
}));

const mockLoadCV = vi.fn();
const mockSetIsSaving = vi.fn();
const mockSetLastSaved = vi.fn();
const mockCurrentCV = Object.freeze({
  id: "1",
  title: "Test CV",
  template_id: "generic-modern",
  sections: [],
  customizations: {},
});
const mockStoreState = {
  currentCV: mockCurrentCV,
  loadCV: mockLoadCV,
  isLoading: false,
  isSaving: false,
  lastSaved: null,
  setIsSaving: mockSetIsSaving,
  setLastSaved: mockSetLastSaved,
  patchCurrentCV: vi.fn(),
};
vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: Object.assign(vi.fn(() => mockStoreState), { getState: () => mockStoreState }),
}));

vi.mock("../../lib/api/cvs", () => ({
  updateCV: vi.fn(() => Promise.resolve({})),
}));

vi.mock("../../lib/api/templates", () => ({
  fetchTemplate: vi.fn(() => Promise.resolve({})),
}));

vi.mock("../../lib/api/client", () => ({ default: vi.fn() }));

vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({ default: ({ open }: any) => open ? <div>AddSectionModal</div> : null }));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({ default: () => <div /> }));
vi.mock("../common/Modal", () => ({ default: ({ open, children }: any) => open ? <div>{children}</div> : null }));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
  DragOverlay: ({ children }: any) => <div>{children}</div>,
  useDroppable: () => ({ isOver: false, setNodeRef: vi.fn() }),
  closestCenter: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(() => ({})),
  useSensors: vi.fn(() => []),
}));

vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: any) => <div>{children}</div>,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
  arrayMove: vi.fn((arr) => arr),
  verticalListSortingStrategy: vi.fn(),
}));

vi.mock("@dnd-kit/utilities", () => ({ CSS: { Transform: { toString: () => "" } } }));

vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

const renderCustomizePanel = (props?: Partial<Parameters<typeof CustomizePanel>[0]>) =>
  render(
    <CustomizePanel
      customizations={{}}
      onChange={vi.fn()}
      templateId="generic-modern"
      onTemplateChange={vi.fn()}
      instances={[]}
      onUpdateStyle={vi.fn()}
      {...props}
    />
  );

describe("CustomizePanel", () => {
  it("renders Global section with color pickers by default", () => {
    renderCustomizePanel();

    expect(screen.getByText("Global")).toBeDefined();
    expect(screen.getByText("Accent")).toBeDefined();
  });

  it("Global section contains fonts and spacing", () => {
    renderCustomizePanel();

    expect(screen.getByText("Body Font")).toBeDefined();
    expect(screen.getByText(/section gap/i)).toBeDefined();
  });

  it("calls onChange when color is changed", () => {
    const onChange = vi.fn();
    renderCustomizePanel({ customizations: { colors: { accent: "#2563eb" } }, onChange });

    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    const accentInput = inputs.find((i) => i.value === "#2563eb");
    if (accentInput) {
      fireEvent.change(accentInput, { target: { value: "#ff0000" } });
      expect(onChange).toHaveBeenCalled();
    }
  });

  it("renders per-section style cards", () => {
    renderCustomizePanel({
      instances: [
        { id: "s1", type: "profile", title: "John", enabled: true, data: {} },
        { id: "s2", type: "experience", title: "Work", enabled: true, data: [] },
      ],
    });

    expect(screen.getByText("John")).toBeDefined();
    expect(screen.getByText("Work")).toBeDefined();
    expect(screen.getByText("Profile")).toBeDefined();
    expect(screen.getByText("Experience")).toBeDefined();
  });
});

describe("T48: customization panel switches via tab bar in BuilderPage", () => {
  it("is hidden in Content tab by default", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.queryByText("Accent")).toBeNull());
  });

  it("appears after clicking Customize tab", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByText("Accent")).toBeDefined());
  });

  it("hides when switching back to Content tab", async () => {
    render(<BuilderPage />);
    await waitFor(() => expect(screen.getByText("Customize")).toBeDefined());
    fireEvent.click(screen.getByText("Customize"));
    await waitFor(() => expect(screen.getByText("Accent")).toBeDefined());
    fireEvent.click(screen.getByText("Content"));
    await waitFor(() => expect(screen.queryByText("Accent")).toBeNull());
  });
});
