import { type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import AccordionPanel from "../../components/common/AccordionPanel";

interface SortableAccordionListProps {
  entries: { id: string }[];
  onReorder: (entries: { id: string }[]) => void;
  onRemove: (index: number) => void;
  getTitle: (entry: any) => string;
  children: (entry: any, index: number) => ReactNode;
}

function SortableItem({
  entry,
  index,
  onRemove,
  getTitle,
  children,
}: {
  entry: { id: string };
  index: number;
  onRemove: (i: number) => void;
  getTitle: (entry: any) => string;
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
              className="cursor-grab text-gray-400 hover:text-gray-600"
              onClick={(e) => e.stopPropagation()}
            >
              <GripVertical className="h-4 w-4" />
            </button>
            <span className="truncate">{getTitle(entry) || "Untitled"}</span>
          </span>
        }
        onRemove={() => onRemove(index)}
      >
        {children}
      </AccordionPanel>
    </div>
  );
}

export default function SortableAccordionList({
  entries,
  onReorder,
  onRemove,
  getTitle,
  children,
}: SortableAccordionListProps) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = entries.findIndex((e) => e.id === active.id);
      const newIndex = entries.findIndex((e) => e.id === over.id);
      onReorder(arrayMove(entries, oldIndex, newIndex));
    }
  };

  const itemIds = entries.map((e) => e.id);

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
        <div className="space-y-4">
          <AnimatePresence>
            {entries.map((entry, i) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                <SortableItem entry={entry} index={i} onRemove={onRemove} getTitle={getTitle}>
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
