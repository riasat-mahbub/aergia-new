import { useState } from "react";
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
import { SECTION_LABELS, DEFAULT_SECTION_ORDER } from "../../lib/sections/types";
import type { SectionData } from "../../lib/sections/types";
import SectionEditorPanel from "./SectionEditorPanel";

interface Props {
  order: string[];
  enabled: string[];
  data: SectionData;
  onOrderChange: (order: string[]) => void;
  onToggle: (section: string) => void;
  onDataChange: (data: SectionData) => void;
}

function SortableSection({
  section,
  enabled,
  onToggle,
}: {
  section: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: section });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className={`flex items-center gap-3 rounded border p-3 ${enabled ? "bg-white" : "bg-gray-50"}`}>
      <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600" title="Drag to reorder">
        ⠿
      </button>
      <span className={`flex-1 text-sm font-medium ${enabled ? "text-gray-800" : "text-gray-400"}`}>
        {SECTION_LABELS[section] || section}
      </span>
      <label className="flex items-center gap-1.5 text-xs text-gray-500">
        <input type="checkbox" checked={enabled} onChange={onToggle} />
        Show
      </label>
    </div>
  );
}

export default function SectionList({ order, enabled, data, onOrderChange, onToggle, onDataChange }: Props) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = order.indexOf(active.id as string);
      const newIndex = order.indexOf(over.id as string);
      onOrderChange(arrayMove(order, oldIndex, newIndex));
    }
  };

  const allSections = order.length > 0 ? order : DEFAULT_SECTION_ORDER;

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Sections</h3>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={allSections} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {allSections.map((section) => (
              <div key={section} onClick={() => setActiveSection(section === activeSection ? null : section)}>
                <SortableSection
                  section={section}
                  enabled={enabled.includes(section)}
                  onToggle={() => onToggle(section)}
                />
                {activeSection === section && (
                  <div className="border-x border-b rounded-b-lg p-3 bg-gray-50">
                    <SectionEditorPanel
                      sectionType={section}
                      data={data}
                      enabled={enabled.includes(section)}
                      onToggle={() => onToggle(section)}
                      onChange={onDataChange}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
