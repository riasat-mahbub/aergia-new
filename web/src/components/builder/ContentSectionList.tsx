import { useRef, useState } from "react";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { AnimatePresence, motion } from "motion/react";
import {
  GripVertical,
  ChevronDown,
  Eye,
  EyeOff,
  Pencil,
  Check,
  Trash2,
  Plus,
} from "lucide-react";

import type { SectionInstance } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import SectionEditorPanel from "../sections/SectionEditorPanel";
import AddSectionModal from "../sections/AddSectionModal";
import Modal from "../common/Modal";

interface Props {
  instances: SectionInstance[];
  cvId?: string;
  onToggle: (sectionId: string) => void;
  onUpdateData: (sectionId: string, data: unknown) => void;
  onAddSection: (type: string) => void;
  onRemoveInstance: (sectionId: string) => void;
  onRenameInstance: (sectionId: string, title: string) => void;
  onReorderInstances: (instances: SectionInstance[]) => void;
}

function SortableRow({
  instance,
  isExpanded,
  editingTitle,
  onToggle,
  onUpdateData,
  onRenameInstance,
  setEditingTitle,
  onRemoveInstance,
  onToggleExpand,
  cvId,
}: {
  instance: SectionInstance;
  isExpanded: boolean;
  editingTitle: string | null;
  onToggle: (id: string) => void;
  onUpdateData: (id: string, data: unknown) => void;
  onRenameInstance: (id: string, title: string) => void;
  setEditingTitle: (id: string | null) => void;
  onRemoveInstance: (id: string) => void;
  onToggleExpand: (id: string) => void;
  cvId?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: instance.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const commitRename = () => {
    const next = inputRef.current?.value.trim() ?? "";
    if (next) onRenameInstance(instance.id, next);
    setEditingTitle(null);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded border bg-white ${instance.enabled ? "border-gray-200" : "border-dashed border-gray-300 bg-gray-50"}`}
      data-section-id={instance.id}
    >
      <div
        className="flex cursor-pointer items-center gap-2 px-3 py-2"
        role="button"
        aria-expanded={isExpanded}
        onClick={() => onToggleExpand(instance.id)}
      >
        <button
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
          className="cursor-grab text-gray-400 hover:text-gray-600"
          title="Drag to reorder"
        >
          <GripVertical className="h-3.5 w-3.5" />
        </button>

        <div className="min-w-0 flex-1">
          {editingTitle === instance.id ? (
            <div className="flex items-center gap-1">
              <input
                ref={inputRef}
                type="text"
                defaultValue={instance.title}
                autoFocus
                className="w-full rounded border border-blue-300 px-1.5 py-0.5 text-sm font-medium text-gray-800"
                onBlur={commitRename}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename();
                }}
                onClick={(e) => e.stopPropagation()}
              />
              <button
                className="rounded bg-emerald-600 px-2 py-0.5 text-xs text-white"
                onClick={(e) => {
                  e.stopPropagation();
                  commitRename();
                }}
              >
                <Check className="h-3 w-3" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span
                className={`text-sm font-medium ${instance.enabled ? "text-gray-800" : "text-gray-400"}`}
              >
                {instance.title}
              </span>
              <span className="text-[10px] text-gray-400">
                {SECTION_LABELS[instance.type] || instance.type}
              </span>
            </div>
          )}
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle(instance.id);
          }}
          className={`rounded p-1 ${
            instance.enabled
              ? "text-blue-600 hover:text-blue-800"
              : "text-gray-400 hover:text-gray-600"
          }`}
          title={instance.enabled ? "Disable" : "Enable"}
        >
          {instance.enabled ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation();
            setEditingTitle(instance.id);
          }}
          className="rounded p-1 text-gray-400 hover:text-gray-600"
          title="Rename"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemoveInstance(instance.id);
          }}
          className="rounded p-1 text-red-400 hover:text-red-600"
          title="Delete"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleExpand(instance.id);
          }}
          className="rounded p-1 text-gray-400 hover:text-gray-600"
          title={isExpanded ? "Collapse" : "Expand"}
        >
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="h-3.5 w-3.5" />
          </motion.div>
        </button>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
              <SectionEditorPanel instance={instance} onChange={onUpdateData} cvId={cvId} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ContentSectionList({
  instances,
  cvId,
  onToggle,
  onUpdateData,
  onAddSection,
  onRemoveInstance,
  onRenameInstance,
  onReorderInstances,
}: Props) {
  // Defensive: a parent may briefly pass `undefined` during a hot-
  // reload transition or while the CV is mid-load. Same pattern as
  // SortableAccordionList's safeEntries.
  const safeInstances = Array.isArray(instances) ? instances : [];
  const [expandedSectionId, setExpandedSectionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const toggleSectionExpand = (id: string) => {
    // Only one content accordion open at a time: opening a section closes
    // whichever section was expanded before.
    setExpandedSectionId((prev) => (prev === id ? null : id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const activeId = String(active.id);
    const overId = String(over.id);
    // Nested per-section DndContext handles entry-level drags; only section IDs belong here.
    if (!safeInstances.some((i) => i.id === activeId) || !safeInstances.some((i) => i.id === overId)) return;
    const oldIndex = safeInstances.findIndex((i) => i.id === activeId);
    const newIndex = safeInstances.findIndex((i) => i.id === overId);
    if (oldIndex === -1 || newIndex === -1) return;
    onReorderInstances(arrayMove(safeInstances, oldIndex, newIndex));
  };

  const deleteTarget = safeInstances.find((i) => i.id === deleteConfirmId);

  return (
    <div className="space-y-2">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={safeInstances.map((i) => i.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-1.5">
            {safeInstances.map((instance) => (
              <SortableRow
                key={instance.id}
                instance={instance}
                isExpanded={expandedSectionId === instance.id}
                editingTitle={editingTitle}
                onToggle={onToggle}
                onUpdateData={onUpdateData}
                onRenameInstance={onRenameInstance}
                setEditingTitle={setEditingTitle}
                onRemoveInstance={(id) => setDeleteConfirmId(id)}
                onToggleExpand={toggleSectionExpand}
                cvId={cvId}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      <button
        type="button"
        onClick={() => setShowAddModal(true)}
        className="flex w-full items-center justify-center gap-1 rounded-md border border-dashed border-gray-300 py-2 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600"
      >
        <Plus className="h-3 w-3" />
        Add section
      </button>

      <AddSectionModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSelect={(type) => {
          onAddSection(type);
          setShowAddModal(false);
        }}
      />

      <Modal open={!!deleteConfirmId} onClose={() => setDeleteConfirmId(null)}>
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Delete Section</h2>
        <p className="text-sm text-gray-600">
          Are you sure you want to delete{" "}
          <span className="font-medium text-gray-900">
            &ldquo;{deleteTarget?.title}&rdquo;
          </span>
          ? This action cannot be undone.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={() => setDeleteConfirmId(null)}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (deleteConfirmId) onRemoveInstance(deleteConfirmId);
              setDeleteConfirmId(null);
            }}
            className="rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </Modal>
    </div>
  );
}
