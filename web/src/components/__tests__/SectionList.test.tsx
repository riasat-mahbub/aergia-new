import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SectionList from "../sections/SectionList";

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

describe("SectionList", () => {
  it("renders all sections with toggles", () => {
    render(
      <SectionList
        order={["profile", "experience"]}
        enabled={["profile"]}
        data={{ profile: { name: "" }, experience: [] } as any}
        onOrderChange={vi.fn()}
        onToggle={vi.fn()}
        onDataChange={vi.fn()}
      />
    );

    expect(screen.getByText("Profile")).toBeDefined();
    expect(screen.getByText("Experience")).toBeDefined();
  });

  it("shows correct toggle state", () => {
    render(
      <SectionList
        order={["profile", "education"]}
        enabled={["profile"]}
        data={{ profile: { name: "" }, education: [] } as any}
        onOrderChange={vi.fn()}
        onToggle={vi.fn()}
        onDataChange={vi.fn()}
      />
    );

    const profileToggle = screen.getByTitle("Disable section");
    const educationToggle = screen.getByTitle("Enable section");
    expect(profileToggle).toBeDefined();
    expect(educationToggle).toBeDefined();
  });
});
