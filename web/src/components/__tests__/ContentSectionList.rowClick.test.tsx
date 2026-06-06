import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ContentSectionList from "../builder/ContentSectionList";

vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({
  default: ({ open, onSelect }: any) =>
    open ? (
      <div><button onClick={() => onSelect("skills")}>Pick Skills</button></div>
    ) : null,
}));
vi.mock("../common/Modal", () => ({
  default: ({ open, children }: any) => (open ? <div>{children}</div> : null),
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
vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: any) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

const SAMPLE = [
  { id: "s1", type: "profile", title: "Profile", enabled: true, data: {} },
  { id: "s2", type: "experience", title: "Experience", enabled: true, data: [] },
];

describe("ContentSectionList whole-row click-to-expand", () => {
  it("clicking the row header (not buttons) toggles expand", () => {
    render(
      <ContentSectionList
        instances={SAMPLE}
        onToggle={vi.fn()}
        onUpdateData={vi.fn()}
        onAddSection={vi.fn()}
        onRemoveInstance={vi.fn()}
        onRenameInstance={vi.fn()}
        onReorderInstances={vi.fn()}
      />,
    );

    // Initially no "Collapse" button (both collapsed)
    expect(screen.queryAllByTitle("Collapse")).toHaveLength(0);

    // The row has a data-section-id attribute; find the header row by clicking
    // a non-button child of the section panel.
    const row = document.querySelector('[data-section-id="s1"]') as HTMLElement;
    expect(row).toBeTruthy();
    // Find a span inside the row that is not a button
    const titleSpan = row.querySelector("span");
    fireEvent.click(titleSpan!);

    // Now one of the rows should be expanded (Collapse button appears)
    expect(screen.getAllByTitle("Collapse").length).toBe(1);
  });

  it("clicking the chevron button still toggles expand independently", () => {
    render(
      <ContentSectionList
        instances={SAMPLE}
        onToggle={vi.fn()}
        onUpdateData={vi.fn()}
        onAddSection={vi.fn()}
        onRemoveInstance={vi.fn()}
        onRenameInstance={vi.fn()}
        onReorderInstances={vi.fn()}
      />,
    );
    const expandButtons = screen.getAllByTitle("Expand");
    expect(expandButtons.length).toBe(2);
    fireEvent.click(expandButtons[0]);
    expect(screen.getAllByTitle("Collapse").length).toBe(1);
  });
});
