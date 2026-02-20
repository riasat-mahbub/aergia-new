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
import { SECTION_LABELS, SECTION_TYPES } from "../../lib/sections/types";
import type { SectionInstance } from "../../lib/sections/types";
import SectionEditorPanel from "./SectionEditorPanel";
import { Eye, EyeOff, GripVertical, Plus, Trash2, Pencil } from "lucide-react";

interface Props {
  instances: SectionInstance[];
  onReorder: (ids: string[]) => void;
  onToggle: (id: string) => void;
  onUpdateData: (id: string, data: any) => void;
  onAddSection: (type: string) => void;
  onRemoveInstance: (id: string) => void;
  onRenameInstance: (id: string, title: string) => void;
}

function SortableSection({
  instance,
  onToggle,
}: {
  instance: SectionInstance;
  onToggle: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: instance.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className={`flex items-center gap-3 rounded border p-3 ${instance.enabled ? "bg-white" : "bg-gray-50"}`}>
      <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600" title="Drag to reorder">
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="flex-1 min-w-0">
        <span className={`block text-sm font-medium truncate ${instance.enabled ? "text-gray-800" : "text-gray-400"}`}>
          {instance.title}
        </span>
        <span className="text-xs text-gray-400">{SECTION_LABELS[instance.type] || instance.type}</span>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onToggle(); }}
        className={`rounded p-1 transition-colors ${instance.enabled ? "text-blue-600 hover:text-blue-800" : "text-gray-400 hover:text-gray-600"}`}
        title={instance.enabled ? "Disable section" : "Enable section"}
      >
        {instance.enabled ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
      </button>
    </div>
  );
}

export default function SectionList({
  instances,
  onReorder,
  onToggle,
  onUpdateData,
  onAddSection,
  onRemoveInstance,
  onRenameInstance,
}: Props) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [showAddDropdown, setShowAddDropdown] = useState(false);
  const [editingTitle, setEditingTitle] = useState<string | null>(null);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = instances.findIndex((i) => i.id === active.id);
      const newIndex = instances.findIndex((i) => i.id === over.id);
      const reordered = arrayMove(instances, oldIndex, newIndex);
      onReorder(reordered.map((i) => i.id));
    }
  };

  const itemIds = instances.map((i) => i.id);

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Sections</h3>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
          <div className="space-y-2">
            {instances.map((instance) => (
              <div key={instance.id}>
                <div onClick={() => setActiveSection(instance.id === activeSection ? null : instance.id)}>
                  <SortableSection instance={instance} onToggle={() => onToggle(instance.id)} />
                </div>
                <AnimatePresence>
                  {activeSection === instance.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="border-x border-b rounded-b-lg p-3 bg-gray-50">
                        <div className="mb-2 flex items-center gap-2">
                          {editingTitle === instance.id ? (
                            <input
                              type="text"
                              defaultValue={instance.title}
                              autoFocus
                              className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
                              onBlur={(e) => {
                                onRenameInstance(instance.id, e.target.value);
                                setEditingTitle(null);
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") {
                                  onRenameInstance(instance.id, (e.target as HTMLInputElement).value);
                                  setEditingTitle(null);
                                }
                              }}
                            />
                          ) : (
                            <button
                              onClick={() => setEditingTitle(instance.id)}
                              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                            >
                              <Pencil className="h-3 w-3" /> Rename
                            </button>
                          )}
                          <button
                            onClick={(e) => { e.stopPropagation(); onRemoveInstance(instance.id); }}
                            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
                          >
                            <Trash2 className="h-3 w-3" /> Remove
                          </button>
                        </div>
                        <SectionEditorPanel
                          instance={instance}
                          onChange={onUpdateData}
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
            {(SECTION_TYPES as unknown as string[]).map((s) => (
              <button
                key={s}
                onClick={() => { onAddSection(s); setShowAddDropdown(false); }}
                className="flex w-full items-center px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                {SECTION_LABELS[s] || s}
              </button>
            ))}
          </motion.div>
        )}
        </AnimatePresence>
      </div>
    </div>
  );
}
