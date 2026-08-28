import { type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  closestCenter,
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import AccordionPanel from "../../components/common/AccordionPanel";

interface SortableAccordionListProps {
  entries: { id: string }[];
  onRemove: (index: number) => void;
  onMove: (from: number, to: number) => void;
  getTitle: (entry: any) => string;
  /**
   * When provided, every entry gets a node rendered in the panel header
   * to the left of Remove. The callback receives the entry id; the parent
   * supplies the action UI (typically a button bound to a modal). Pass
   * undefined to omit (used by editors whose kind is not library-eligible).
   */
  onAddToLibrary?: (entryId: string) => ReactNode;
  children: (entry: any, index: number) => ReactNode;
  compact?: boolean;
}

function SortableItem({
  entry,
  index,
  onRemove,
  getTitle,
  actions,
  children,
}: {
  entry: { id: string };
  index: number;
  onRemove: (i: number) => void;
  getTitle: (entry: any) => string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: entry.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <AccordionPanel
        title={
          <span className="flex items-center gap-2">
            <button
              {...attributes}
              {...listeners}
              className="cursor-grab text-app-ink-3 hover:text-app-ink"
              onClick={(e) => e.stopPropagation()}
            >
              <GripVertical className="h-4 w-4" />
            </button>
            <span className="truncate">{getTitle(entry) || "Untitled"}</span>
          </span>
        }
        actions={actions}
        onRemove={() => onRemove(index)}
      >
        {children}
      </AccordionPanel>
    </div>
  );
}

export default function SortableAccordionList({
  entries,
  onRemove,
  onMove,
  getTitle,
  onAddToLibrary,
  children,
  compact = false,
}: SortableAccordionListProps) {
  // Defensive: a parent editor may briefly pass `undefined` during a
  // hot-reload transition or while a section is mid-save. The prop is
  // typed as an array, but at runtime anything goes. Falling back to
  // [] keeps every consumer safe without requiring each editor to
  // remember its own guard.
  const safeEntries = Array.isArray(entries) ? entries : [];
  const itemIds = safeEntries.map((e) => e.id);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  if (compact) {
    return (
      <div className="space-y-4">
        {safeEntries.map((entry, index) => (
          <div key={entry.id}>{children(entry, index)}</div>
        ))}
      </div>
    );
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const activeId = String(event.active.id);
    const overId = event.over ? String(event.over.id) : null;
    if (!overId || activeId === overId) return;
    const from = safeEntries.findIndex((entry) => entry.id === activeId);
    const to = safeEntries.findIndex((entry) => entry.id === overId);
    if (from === -1 || to === -1) return;
    onMove(from, to);
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
        <div className="space-y-4">
          <AnimatePresence>
            {safeEntries.map((entry, i) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                <SortableItem
                  entry={entry}
                  index={i}
                  onRemove={onRemove}
                  getTitle={getTitle}
                  actions={onAddToLibrary ? onAddToLibrary(entry.id) : undefined}
                >
                  {children(entry, i)}
                </SortableItem>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </SortableContext>
    </DndContext>
  );
}
