import type { ReactNode } from "react";
import type { DragEndEvent } from "@dnd-kit/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SortableAccordionList from "../SortableAccordionList";

let dragEndEvent: DragEndEvent | null;

vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children, onDragEnd }: { children: ReactNode; onDragEnd?: (event: DragEndEvent) => void }) => {
    if (dragEndEvent) onDragEnd?.(dragEndEvent);
    return <div>{children}</div>;
  },
  closestCenter: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(() => ({})),
  useSensors: vi.fn(() => []),
}));

vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
  verticalListSortingStrategy: vi.fn(),
}));

vi.mock("@dnd-kit/utilities", () => ({ CSS: { Transform: { toString: () => "" } } }));
vi.mock("motion/react", () => ({
  motion: { div: ({ children, ...props }: { children: ReactNode }) => <div {...props}>{children}</div> },
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

const entries = [
  { id: "a", title: "Alpha" },
  { id: "b", title: "Bravo" },
  { id: "c", title: "Charlie" },
  { id: "d", title: "Delta" },
];

function renderList(onMove = vi.fn()) {
  render(
    <SortableAccordionList
      entries={entries}
      onRemove={vi.fn()}
      onMove={onMove}
      getTitle={(entry) => entry.title}
    >
      {() => <div>Body</div>}
    </SortableAccordionList>,
  );
  return onMove;
}

describe("SortableAccordionList", () => {
  beforeEach(() => {
    dragEndEvent = null;
  });

  it("renders entry titles in array order", () => {
    renderList();

    expect(screen.getAllByText(/Alpha|Bravo|Charlie|Delta/).map((node) => node.textContent)).toEqual([
      "Alpha",
      "Bravo",
      "Charlie",
      "Delta",
    ]);
  });

  it("moves between two distinct entry ids", () => {
    dragEndEvent = { active: { id: "a" }, over: { id: "c" } } as typeof dragEndEvent;
    const onMove = renderList();

    expect(onMove).toHaveBeenCalledOnce();
    expect(onMove).toHaveBeenCalledWith(0, 2);
  });

  it("does not move when dropped over itself", () => {
    dragEndEvent = { active: { id: "b" }, over: { id: "b" } } as typeof dragEndEvent;
    const onMove = renderList();

    expect(onMove).not.toHaveBeenCalled();
  });

  it("does not move when dropped outside a droppable", () => {
    dragEndEvent = { active: { id: "a" }, over: null } as typeof dragEndEvent;
    const onMove = renderList();

    expect(onMove).not.toHaveBeenCalled();
  });

  it("maps a downward drag to the original entry indices", () => {
    dragEndEvent = { active: { id: entries[1].id }, over: { id: entries[3].id } } as typeof dragEndEvent;
    const onMove = renderList();

    expect(onMove).toHaveBeenCalledWith(1, 3);
  });
});
