import { useState } from "react";
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
import { SECTION_LABELS, DEFAULT_SECTION_ORDER } from "../../lib/sections/types";
import type { SectionData } from "../../lib/sections/types";
import SectionEditorPanel from "./SectionEditorPanel";
import { Eye, EyeOff, GripVertical, Plus } from "lucide-react";

interface Props {
  order: string[];
  enabled: string[];
  data: SectionData;
  onOrderChange: (order: string[]) => void;
  onToggle: (section: string) => void;
  onDataChange: (data: SectionData) => void;
  onAddSection?: (section: string) => void;
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
        <GripVertical className="h-4 w-4" />
      </button>
      <span className={`flex-1 text-sm font-medium ${enabled ? "text-gray-800" : "text-gray-400"}`}>
        {SECTION_LABELS[section] || section}
      </span>
      <button
        onClick={(e) => { e.stopPropagation(); onToggle(); }}
        className={`rounded p-1 transition-colors ${enabled ? "text-blue-600 hover:text-blue-800" : "text-gray-400 hover:text-gray-600"}`}
        title={enabled ? "Disable section" : "Enable section"}
      >
        {enabled ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
      </button>
    </div>
  );
}

export default function SectionList({ order, enabled, data, onOrderChange, onToggle, onDataChange, onAddSection }: Props) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [showAddDropdown, setShowAddDropdown] = useState(false);

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
                <AnimatePresence>
                  {activeSection === section && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="border-x border-b rounded-b-lg p-3 bg-gray-50">
                        <SectionEditorPanel
                          sectionType={section}
                          data={data}
                          enabled={enabled.includes(section)}
                          onToggle={() => onToggle(section)}
                          onChange={onDataChange}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <div className="relative mt-3">
        <button
          onClick={() => setShowAddDropdown(!showAddDropdown)}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800"
        >
          <Plus className="h-4 w-4" /> Add Section
        </button>
        <AnimatePresence>
          {showAddDropdown && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="absolute left-0 top-full z-10 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
            {DEFAULT_SECTION_ORDER.filter((s) => !allSections.includes(s)).map((s) => (
              <button
                key={s}
                onClick={() => { onAddSection?.(s); setShowAddDropdown(false); }}
                className="flex w-full items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                {SECTION_LABELS[s] || s}
              </button>
            ))}
            {DEFAULT_SECTION_ORDER.filter((s) => !allSections.includes(s)).length === 0 && (
              <p className="px-3 py-2 text-xs text-gray-400">All sections added</p>
            )}
          </motion.div>
        )}
        </AnimatePresence>
      </div>
    </div>
  );
}
