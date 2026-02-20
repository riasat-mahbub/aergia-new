import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SectionList from "../sections/SectionList";
import type { SectionInstance } from "../../lib/sections/types";

// Mock dnd-kit since it requires browser APIs
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

const makeInstances = (overrides?: Partial<SectionInstance>[]): SectionInstance[] => [
  { id: "sec_1", type: "profile", title: "My Profile", enabled: true, data: { name: "" }, ...overrides?.[0] },
  { id: "sec_2", type: "experience", title: "Experience", enabled: false, data: [], ...overrides?.[1] },
];

describe("SectionList", () => {
  it("renders all sections with toggles", () => {
    render(
      <SectionList
        instances={makeInstances()}
        onReorder={vi.fn()}
        onToggle={vi.fn()}
        onUpdateData={vi.fn()}
        onAddSection={vi.fn()}
        onRemoveInstance={vi.fn()}
        onRenameInstance={vi.fn()}
      />
    );

    expect(screen.getAllByText("My Profile").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Experience").length).toBeGreaterThanOrEqual(1);
  });

  it("shows correct toggle state", () => {
    render(
      <SectionList
        instances={makeInstances([{ enabled: true }, { enabled: false }])}
        onReorder={vi.fn()}
        onToggle={vi.fn()}
        onUpdateData={vi.fn()}
        onAddSection={vi.fn()}
        onRemoveInstance={vi.fn()}
        onRenameInstance={vi.fn()}
      />
    );

    const profileToggle = screen.getByTitle("Disable section");
    const educationToggle = screen.getByTitle("Enable section");
    expect(profileToggle).toBeDefined();
    expect(educationToggle).toBeDefined();
  });
});
