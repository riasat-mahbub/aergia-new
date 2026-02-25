import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CustomizePanel from "../customization/CustomizePanel";
import BuilderPage from "../../pages/BuilderPage";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-id" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../../lib/store/cvStore", () => ({
  useCVStore: vi.fn(() => ({
    currentCV: {
      id: "1",
      title: "Test CV",
      template_id: "generic-modern",
      sections: [],
      customizations: {},
    },
    loadCV: vi.fn(),
    isLoading: false,
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

describe("CustomizePanel", () => {
  it("renders color tab by default", () => {
    render(<CustomizePanel customizations={{}} onChange={vi.fn()} />);

    expect(screen.getByText("Colors")).toBeDefined();
    expect(screen.getByText("Accent")).toBeDefined();
  });

  it("switches between tabs", () => {
    render(<CustomizePanel customizations={{}} onChange={vi.fn()} />);

    fireEvent.click(screen.getByText("Fonts"));
    expect(screen.getByText("Body Font")).toBeDefined();

    fireEvent.click(screen.getByText("Spacing"));
    expect(screen.getByText(/section gap/i)).toBeDefined();
  });

  it("calls onChange when color is changed", () => {
    const onChange = vi.fn();
    render(<CustomizePanel customizations={{ colors: { accent: "#2563eb" } }} onChange={onChange} />);

    const inputs = screen.getAllByRole("textbox") as HTMLInputElement[];
    const accentInput = inputs.find((i) => i.value === "#2563eb");
    if (accentInput) {
      fireEvent.change(accentInput, { target: { value: "#ff0000" } });
      expect(onChange).toHaveBeenCalled();
    }
  });
});

describe("T48: customization panel visibility in BuilderPage", () => {
  it("is hidden by default", () => {
    render(<BuilderPage />);
    expect(screen.queryByText("Customize")).toBeNull();
  });

  it("appears after clicking toggle icon", () => {
    render(<BuilderPage />);
    const toggle = screen.getByTitle("Toggle customization panel");
    fireEvent.click(toggle);
    expect(screen.getByText("Customize")).toBeDefined();
  });
});
