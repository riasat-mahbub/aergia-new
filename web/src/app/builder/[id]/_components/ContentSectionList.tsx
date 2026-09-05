import { useState } from "react";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import { Plus } from "lucide-react";

import type { SectionInstance } from "@/lib/cv/schema";
import AddSectionModal from "./AddSectionModal";
import DeleteSectionDialog from "./DeleteSectionDialog";
import SortableSectionRow from "./SortableSectionRow";

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
  const safeInstances = Array.isArray(instances) ? instances : [];
  const [expandedSectionId, setExpandedSectionId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const toggleSectionExpand = (id: string) => {
    setExpandedSectionId((prev) => (prev === id ? null : id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const activeId = String(active.id);
    const overId = String(over.id);
    if (!safeInstances.some((instance) => instance.id === activeId) || !safeInstances.some((instance) => instance.id === overId)) return;
    const oldIndex = safeInstances.findIndex((instance) => instance.id === activeId);
    const newIndex = safeInstances.findIndex((instance) => instance.id === overId);
    if (oldIndex === -1 || newIndex === -1) return;
    onReorderInstances(arrayMove(safeInstances, oldIndex, newIndex));
  };

  const deleteTarget = safeInstances.find((instance) => instance.id === deleteConfirmId);

  return (
    <div className="space-y-2">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={safeInstances.map((instance) => instance.id)} strategy={verticalListSortingStrategy}>
          <div className="space-y-1.5">
            {safeInstances.map((instance) => (
              <SortableSectionRow
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
        className="flex w-full items-center justify-center gap-1 rounded-md border border-dashed border-app-rule-strong py-2 text-xs text-app-ink-3 hover:border-app-primary-soft hover:text-app-primary"
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

      <DeleteSectionDialog
        open={!!deleteConfirmId}
        title={deleteTarget?.title}
        onClose={() => setDeleteConfirmId(null)}
        onConfirm={() => {
          if (deleteConfirmId) onRemoveInstance(deleteConfirmId);
          setDeleteConfirmId(null);
        }}
      />
    </div>
  );
}
