import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import SectionZoneView from "../layout/SectionZoneView";

vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({
  default: ({ open, onSelect }: any) =>
    open ? (
      <div>
        <button onClick={() => onSelect("skills")}>Pick Skills</button>
      </div>
    ) : null,
}));
vi.mock("../customization/ZoneStyleEditor", () => ({ default: () => <div /> }));
vi.mock("../customization/ZoneCreationModal", () => ({
  default: ({ open, onCreate }: any) =>
    open ? (
      <div>
        <button onClick={() => onCreate({ id: "zone_new", label: "New", styles: { width: "40%" } })}>
          Submit New Zone
        </button>
      </div>
    ) : null,
}));
vi.mock("../common/Modal", () => ({
  default: ({ open, children }: any) => (open ? <div>{children}</div> : null),
}));

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

const SAMPLE_INSTANCES = [
  { id: "sec_a", type: "profile", title: "Profile", enabled: true, data: {} },
];

function renderView(layout: any, propsOverride: any = {}) {
  const onLayoutConfigChange = vi.fn();
  const utils = render(
    <SectionZoneView
      instances={SAMPLE_INSTANCES}
      layoutConfig={layout}
      onUpdateData={vi.fn()}
      onAddSection={vi.fn()}
      onRemoveInstance={vi.fn()}
      onRenameInstance={vi.fn()}
      onLayoutConfigChange={onLayoutConfigChange}
      onReorderInstances={vi.fn()}
      onEntryDragEnd={vi.fn()}
      {...propsOverride}
    />,
  );
  return { onLayoutConfigChange, ...utils };
}

describe("SectionZoneView zone-only", () => {
  it("renders one row of zones, no Row N label, no Add Row button", () => {
    const layout = {
      zones: [
        { id: "left", label: "Sidebar", styles: { width: "30%" } },
        { id: "right", label: "Main", styles: { width: "70%" } },
      ],
      placement: {},
    };
    const { container } = renderView(layout);
    expect(screen.getByTestId("zone-row")).toBeDefined();
    expect(screen.getByText("Sidebar")).toBeDefined();
    expect(screen.getByText("Main")).toBeDefined();
    expect(screen.queryByText(/Row \d/)).toBeNull();
    expect(screen.queryByText(/Add Row/)).toBeNull();
    // Add Zone button is present.
    expect(screen.getByText(/Add Zone/)).toBeDefined();
    // Each zone's inner content carries the cell width.
    const left = screen.getByTestId("zone-content-left");
    const right = screen.getByTestId("zone-content-right");
    expect((left as HTMLElement).style.width).toBe("30%");
    expect((right as HTMLElement).style.width).toBe("70%");
    expect(container).toBeDefined();
  });

  it("Add Zone opens the modal; submitting appends a zone with normalized widths", () => {
    const layout = {
      zones: [
        { id: "left", styles: { width: "50%" } },
        { id: "right", styles: { width: "50%" } },
      ],
      placement: {},
    };
    const { onLayoutConfigChange } = renderView(layout);
    fireEvent.click(screen.getByText("Add Zone"));
    fireEvent.click(screen.getByText("Submit New Zone"));
    expect(onLayoutConfigChange).toHaveBeenCalled();
    const lastCall = onLayoutConfigChange.mock.calls[onLayoutConfigChange.mock.calls.length - 1][0];
    expect(lastCall.zones).toHaveLength(3);
    // Widths must sum to 100.
    const total = lastCall.zones.reduce(
      (s: number, z: any) => s + parseInt(z.styles.width),
      0,
    );
    expect(total).toBe(100);
  });

  it("zone background color tints the inner content wrapper, not the chrome", () => {
    const layout = {
      zones: [
        { id: "left", label: "Sidebar", styles: { width: "100%", "background-color": "#abcdef" } },
      ],
      placement: {},
    };
    renderView(layout);
    const content = screen.getByTestId("zone-content-left");
    expect((content as HTMLElement).style.backgroundColor).toBe("rgb(171, 205, 239)");
  });

  it("row itself is the drag target; no grip handle or eye icon", () => {
    const layout = {
      zones: [{ id: "main", label: "Main", styles: { width: "100%" } }],
      placement: { sec_a: "main" },
    };
    const { container } = renderView(layout);
    // The section row carries the drag listeners (useSortable attributes/listeners
    // are mocked as empty objects, but the spread is what matters — there is no
    // separate grip-handle button anymore).
    const row = screen.getByTestId("zone-section-sec_a");
    expect(row).toBeDefined();
    // Grip handle button removed.
    expect(container.querySelector(".cursor-grab")).toBeNull();
    // No lucide Eye/EyeOff icon svgs rendered (no <svg> with those paths —
    // simplest: no element with a title of Enable/Disable).
    expect(screen.queryByTitle("Enable")).toBeNull();
    expect(screen.queryByTitle("Disable")).toBeNull();
  });
});
