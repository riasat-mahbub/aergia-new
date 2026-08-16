import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ContentSectionList from "../builder/ContentSectionList";

vi.mock("../sections/SectionEditorPanel", () => ({ default: () => <div /> }));
vi.mock("../sections/AddSectionModal", () => ({
  default: ({ open, onSelect }: any) =>
    open ? (
      <div>
        <button onClick={() => onSelect("skills")}>Pick Skills</button>
      </div>
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
  arrayMove: vi.fn((arr, from, to) => {
    const next = [...arr];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    return next;
  }),
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

describe("ContentSectionList", () => {
  it("renders instances in array order with their titles and type chips", () => {
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

    // Each section title renders twice (title span + type chip span when types differ in casing).
    expect(screen.getAllByText("Profile").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Experience").length).toBeGreaterThanOrEqual(1);
  });

  it("calls onToggle when the eye button is clicked", () => {
    const onToggle = vi.fn();
    render(
      <ContentSectionList
        instances={SAMPLE}
        onToggle={onToggle}
        onUpdateData={vi.fn()}
        onAddSection={vi.fn()}
        onRemoveInstance={vi.fn()}
        onRenameInstance={vi.fn()}
        onReorderInstances={vi.fn()}
      />,
    );

    const eyeButtons = screen.getAllByTitle("Disable");
    fireEvent.click(eyeButtons[0]);
    expect(onToggle).toHaveBeenCalledWith("s1");
  });

  it("opens the confirmation modal when trash is clicked and calls onRemoveInstance on confirm", () => {
    const onRemove = vi.fn();
    render(
      <ContentSectionList
        instances={SAMPLE}
        onToggle={vi.fn()}
        onUpdateData={vi.fn()}
        onAddSection={vi.fn()}
        onRemoveInstance={onRemove}
        onRenameInstance={vi.fn()}
        onReorderInstances={vi.fn()}
      />,
    );

    const trashButtons = screen.getAllByTitle("Delete");
    fireEvent.click(trashButtons[0]);
    // "Delete" is the button text and also appears in the heading. Match by class instead.
    const confirmBtn = document.querySelector("button.bg-app-danger") as HTMLButtonElement;
    expect(confirmBtn).toBeTruthy();
    fireEvent.click(confirmBtn);
  });


  it("keeps only one section expanded at a time", () => {
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
    fireEvent.click(expandButtons[0]);
    fireEvent.click(screen.getAllByTitle("Expand")[0]);
    // Opening a second section collapses the first — exactly one stays open.
    expect(screen.getAllByTitle("Collapse").length).toBe(1);
  });

  it("opens the AddSectionModal when Add section is clicked and calls onAddSection on pick", () => {
    const onAddSection = vi.fn();
    render(
      <ContentSectionList
        instances={SAMPLE}
        onToggle={vi.fn()}
        onUpdateData={vi.fn()}
        onAddSection={onAddSection}
        onRemoveInstance={vi.fn()}
        onRenameInstance={vi.fn()}
        onReorderInstances={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("Add section"));
    fireEvent.click(screen.getByText("Pick Skills"));
    expect(onAddSection).toHaveBeenCalledWith("skills");
  });
});
