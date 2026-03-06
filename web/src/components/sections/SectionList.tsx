import { useState, useRef } from "react";
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
import AddSectionModal from "./AddSectionModal";
import { Check, ChevronDown, Eye, EyeOff, GripVertical, Pencil, Plus, Trash2 } from "lucide-react";

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
  isActive,
  editingTitle,
  onRemoveInstance,
  onRenameInstance,
  setEditingTitle,
}: {
  instance: SectionInstance;
  onToggle: () => void;
  isActive: boolean;
  editingTitle: string | null;
  onRemoveInstance: (id:string) => void;
  onRenameInstance: (id: string, title: string) => void;
  setEditingTitle: (id: string | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: instance.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const commitRename = () => {
    if (inputRef.current && inputRef.current.value.trim()) {
      onRenameInstance(instance.id, inputRef.current.value);
    }
    setEditingTitle(null);
  };

  return (
    <div ref={setNodeRef} style={style} className={`flex items-center gap-3 rounded border p-3 ${instance.enabled ? "bg-white" : "bg-gray-50"} cursor-pointer`}>
      <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600" title="Drag to reorder">
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="flex-1 min-w-0">
        {editingTitle === instance.id ? (
          <div className="w-full flex flex-row">
            <input
              ref={inputRef}
              type="text"
              defaultValue={instance.title}
              autoFocus
              className="rounded border border-blue-300 px-1.5 py-0.5 text-sm font-medium text-gray-800"
              onBlur={commitRename}
              onKeyDown={(e) => { if (e.key === "Enter") commitRename(); }}
              onClick={(e) => e.stopPropagation()}
            />

            <button className="ml-2 flex flex-row items-center bg-gradient-to-r from-emerald-700 to-emerald-300 rounded-md text-white px-2 py-1"
              onBlur={commitRename}
              onKeyDown={(e) => { if (e.key === "Enter") commitRename(); }}
              onClick={(e) => e.stopPropagation()}
            >
              <Check className="h-3 w-3 mr-1"/>
              <div className="text-xs">
                Done
              </div>
            </button>
          </div>
          
        ) : (
          <div className="flex flex-row items-center">
            <div className={`block  mr-3 text-left text-sm font-medium truncate ${instance.enabled ? "text-gray-800" : "text-gray-400"}`}>
              {instance.title}
            </div>

            {isActive && <div 
              onClick={(e) => { e.stopPropagation(); setEditingTitle(instance.id); }} 
              className={`flex flex-row items-center text-left text-xs font-medium truncate bg-gray-200 p-1  rounded-md ${instance.enabled ? "text-gray-800" : "text-gray-400"} px-2`}
            >
              <Pencil className="h-3 w-3 mr-1"/>
              <button>
                Edit Title
              </button>
            </div>}

          </div>

        )}


        <span className="text-xs text-gray-400">{SECTION_LABELS[instance.type] || instance.type}</span>
      </div>

      <motion.div
        animate={{ rotate: isActive ? 180 : 0 }}
        transition={{ duration: 0.2 }}
      >
        <ChevronDown className="h-4 w-4 text-gray-800" />
      </motion.div>
      <button
        onClick={(e) => { e.stopPropagation(); onToggle(); }}
        className={`rounded p-1 transition-colors ${instance.enabled ? "text-blue-600 hover:text-blue-800" : "text-gray-400 hover:text-gray-600"}`}
        title={instance.enabled ? "Disable section" : "Enable section"}
      >
        {instance.enabled ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
      </button>

      <button
          onClick={(e) => { e.stopPropagation(); onRemoveInstance(instance.id); }}
          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
        >
          <Trash2 className="h-4 w-4" />
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
  const [showAddModal, setShowAddModal] = useState(false);
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
                <div onClick={() => { if (editingTitle !== instance.id) setActiveSection(instance.id === activeSection ? null : instance.id); }}>
                  <SortableSection
                    instance={instance}
                    isActive={activeSection === instance.id}
                    onToggle={() => onToggle(instance.id)}
                    editingTitle={editingTitle}
                    onRenameInstance={onRenameInstance}
                    onRemoveInstance={onRemoveInstance}
                    setEditingTitle={setEditingTitle}
                  />
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

      <div className="mt-3">
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800"
        >
          <Plus className="h-4 w-4" /> Add Section
        </button>
      </div>

      <AddSectionModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSelect={onAddSection}
      />
    </div>
  );
}
