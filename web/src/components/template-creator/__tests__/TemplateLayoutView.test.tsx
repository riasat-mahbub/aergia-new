/** @vitest-environment jsdom */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TemplateLayoutView from "../TemplateLayoutView";

vi.mock("../../sections/SectionEditorPanel", () => ({ default: () => <div /> }));

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: any) => <div>{children}</div>,
  DragOverlay: ({ children }: any) => <div>{children}</div>,
  closestCenter: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(() => ({})),
  useSensors: vi.fn(() => []),
  useDroppable: () => ({ isOver: false, setNodeRef: vi.fn() }),
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
  arrayMove: vi.fn((arr, from, to) => {
    const next = [...arr];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    return next;
  }),
  verticalListSortingStrategy: vi.fn(),
  horizontalListSortingStrategy: vi.fn(),
}));

vi.mock("@dnd-kit/utilities", () => ({ CSS: { Transform: { toString: () => "" } } }));

vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe("TemplateLayoutView zone-only", () => {
  it("renders a flat list of zones, no Add Row, no Row N label", () => {
    const onChange = vi.fn();
    render(
      <TemplateLayoutView
        zones={[
          { id: "a", label: "Side", styles: { width: "40%" } },
          { id: "b", label: "Main", styles: { width: "60%" } },
        ]}
        placement={{}}
        onChange={onChange}
      />,
    );
    expect(screen.getByTestId("zone-row")).toBeDefined();
    expect(screen.getByText("Side")).toBeDefined();
    expect(screen.getByText("Main")).toBeDefined();
    expect(screen.queryByText(/Row \d/)).toBeNull();
    expect(screen.queryByText(/Add Row/)).toBeNull();
    expect(screen.getByText(/Add Zone/)).toBeDefined();
  });

  it("Add Zone appends a new zone and rebalances widths to sum to 100", () => {
    const onChange = vi.fn();
    render(
      <TemplateLayoutView
        zones={[
          { id: "a", label: "Side", styles: { width: "50%" } },
          { id: "b", label: "Main", styles: { width: "50%" } },
        ]}
        placement={{}}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByText("Add Zone"));
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    expect(lastCall.zones).toHaveLength(3);
    const total = lastCall.zones.reduce(
      (s: number, z: any) => s + parseInt(z.styles.width),
      0,
    );
    expect(total).toBe(100);
  });
});
