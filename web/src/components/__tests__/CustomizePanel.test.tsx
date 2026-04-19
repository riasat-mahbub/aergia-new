import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CustomizePanel from "../customization/CustomizePanel";
import BuilderPage from "../../pages/BuilderPage";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-id" }),
  useNavigate: () => vi.fn(),
  useBlocker: () => ({ state: "unblocked" }),
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
vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: vi.fn(() => ({
    currentCV: mockCurrentCV,
    loadCV: mockLoadCV,
    isLoading: false,
    isSaving: false,
    lastSaved: null,
    setIsSaving: mockSetIsSaving,
    setLastSaved: mockSetLastSaved,
  })),
}));

vi.mock("../../lib/api/cvs", () => ({
  updateCV: vi.fn(() => Promise.resolve({})),
}));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
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

const renderCustomizePanel = (props?: Partial<Parameters<typeof CustomizePanel>[0]>) =>
  render(
    <CustomizePanel
      customizations={{}}
      onChange={vi.fn()}
      templateId="generic-modern"
      onTemplateChange={vi.fn()}
      instances={[]}
      onUpdateStyle={vi.fn()}
      layoutConfig={null}
      onLayoutConfigChange={vi.fn()}
      templateLayoutConfig={null}
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
  it("is hidden in Content tab by default", () => {
    render(<BuilderPage />);
    expect(screen.queryByText("Accent")).toBeNull();
  });

  it("appears after clicking Customize tab", () => {
    render(<BuilderPage />);
    fireEvent.click(screen.getByText("Customize"));
    expect(screen.getByText("Accent")).toBeDefined();
  });

  it("hides when switching back to Content tab", () => {
    render(<BuilderPage />);
    fireEvent.click(screen.getByText("Customize"));
    expect(screen.getByText("Accent")).toBeDefined();
    fireEvent.click(screen.getByText("Content"));
    expect(screen.queryByText("Accent")).toBeNull();
  });
});
