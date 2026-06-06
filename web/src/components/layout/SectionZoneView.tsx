import { useState, useMemo } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  DragOverlay,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  arrayMove,
  horizontalListSortingStrategy,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, Trash2, ChevronDown, Pencil } from "lucide-react";
import type { SectionInstance, Zone, LayoutConfig } from "../../lib/sections/types";
import { SECTION_LABELS, getFirstZoneId } from "../../lib/sections/types";
import { normalizeWidths, getWidthPercent } from "../../lib/sections/zones";
import SectionEditorPanel from "../sections/SectionEditorPanel";
import AddSectionModal from "../sections/AddSectionModal";
import ZoneStyleEditor from "../customization/ZoneStyleEditor";
import ZoneCreationModal from "../customization/ZoneCreationModal";
import Modal from "../common/Modal";

interface Props {
  instances: SectionInstance[];
  layoutConfig: LayoutConfig;
  assets?: Record<string, string>;
  onUpdateData: (id: string, data: any) => void;
  onAddSection: (type: string, zoneId?: string) => void;
  onRemoveInstance: (id: string) => void;
  onRenameInstance: (id: string, title: string) => void;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  onReorderInstances: (instances: SectionInstance[]) => void;
  onEntryDragEnd: (event: DragEndEvent) => void;
  readOnly?: boolean;
  selectedSectionId?: string | null;
  onSelect?: (id: string) => void;
}

/* ── Sortable Section ─────────────────────────────────────────────── */

function SortableSection({
  instance,
  isExpanded,
  editingTitle,
  onRenameInstance,
  setEditingTitle,
  setDeleteConfirmId,
  onClick,
  readOnly = false,
  selected = false,
  onSelect,
}: {
  instance: SectionInstance;
  isExpanded: boolean;
  editingTitle: string | null;
  onRenameInstance: (id: string, title: string) => void;
  setEditingTitle: (id: string | null) => void;
  setDeleteConfirmId: (id: string | null) => void;
  onClick: () => void;
  readOnly?: boolean;
  selected?: boolean;
  onSelect?: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: instance.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => { onSelect?.(instance.id); onClick(); }}
      data-testid={`zone-section-${instance.id}`}
      className={`flex cursor-pointer items-center gap-2 rounded border px-2 py-1.5 text-sm transition-colors ${
        selected
          ? "border-blue-400 bg-blue-50"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      {editingTitle === instance.id ? (
        <input
          autoFocus
          defaultValue={instance.title}
          onBlur={(e) => {
            onRenameInstance(instance.id, e.target.value || instance.title);
            setEditingTitle(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onRenameInstance(instance.id, (e.target as HTMLInputElement).value || instance.title);
              setEditingTitle(null);
            } else if (e.key === "Escape") {
              setEditingTitle(null);
            }
          }}
          className="flex-1 rounded border border-blue-300 px-1 py-0.5 text-sm"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span
          className="flex-1 truncate"
          onDoubleClick={(e) => {
            e.stopPropagation();
            if (!readOnly) setEditingTitle(instance.id);
          }}
        >
          {instance.title}
        </span>
      )}
      <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500">
        {SECTION_LABELS[instance.type] || instance.type}
      </span>
      {!readOnly && (
        <>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setEditingTitle(instance.id);
            }}
            className="text-gray-400 hover:text-gray-600"
            title="Rename"
          >
            <Pencil className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setDeleteConfirmId(instance.id);
            }}
            className="text-red-400 hover:text-red-600"
            title="Delete"
          >
            <Trash2 className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClick();
            }}
            className="text-gray-400 hover:text-gray-600"
            title="Expand"
          >
            <ChevronDown
              className={`h-3.5 w-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`}
            />
          </button>
        </>
      )}
    </div>
  );
}

/* ── Zone Droppable (end of list target) ───────────────────────────── */

function ZoneDroppable({ zoneId }: { zoneId: string }) {
  const { isOver, setNodeRef } = useDroppable({ id: `zone-end-${zoneId}` });
  return (
    <div
      ref={setNodeRef}
      className={`h-2 rounded ${isOver ? "bg-blue-300" : ""}`}
      data-testid={`zone-end-${zoneId}`}
    />
  );
}

function UnassignedDroppable() {
  const { isOver, setNodeRef } = useDroppable({ id: "unassigned-drop" });
  return (
    <div
      ref={setNodeRef}
      className={`mt-1 rounded border-2 border-dashed p-2 text-center text-[10px] ${
        isOver ? "border-blue-400 bg-blue-50" : "border-transparent"
      }`}
    >
      Drop section here to unassign
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────────────── */

export default function SectionZoneView({
  instances,
  layoutConfig,
  assets,
  onUpdateData,
  onAddSection,
  onRemoveInstance,
  onRenameInstance,
  onLayoutConfigChange,
  onReorderInstances,
  onEntryDragEnd,
  readOnly = false,
  selectedSectionId = null,
  onSelect,
}: Props) {
  const { zones, placement } = layoutConfig;

  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [expandedZoneStyles, setExpandedZoneStyles] = useState<Set<string>>(new Set());
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addTargetZoneId, setAddTargetZoneId] = useState<string | null>(null);
  const [showZoneCreationModal, setShowZoneCreationModal] = useState(false);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  /* ── Derived data ───────────────────────────────────────────────── */

  const sectionZoneMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const inst of instances) {
      const zoneId = placement[inst.id];
      if (zoneId) map[inst.id] = zoneId;
    }
    return map;
  }, [instances, placement]);

  const zoneSectionIds = useMemo(() => {
    const ids: Record<string, string[]> = {};
    for (const zone of zones) {
      ids[zone.id] = instances
        .filter((i) => sectionZoneMap[i.id] === zone.id)
        .map((i) => i.id);
    }
    return ids;
  }, [zones, instances, sectionZoneMap]);

  const unassignedInstances = useMemo(
    () => instances.filter((i) => !sectionZoneMap[i.id]),
    [instances, sectionZoneMap],
  );

  /* ── UI toggles ─────────────────────────────────────────────────── */

  const toggleSectionExpand = (id: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleZoneStyle = (zoneId: string) => {
    setExpandedZoneStyles((prev) => {
      const next = new Set(prev);
      if (next.has(zoneId)) next.delete(zoneId);
      else next.add(zoneId);
      return next;
    });
  };

  /* ── Add Section ────────────────────────────────────────────────── */

  const handleAddSectionClick = (zoneId: string) => {
    setAddTargetZoneId(zoneId);
    setShowAddModal(true);
  };

  const handleAddSectionWithZone = (type: string) => {
    const targetId = addTargetZoneId ?? getFirstZoneId(layoutConfig);
    if (!targetId) return;

    onAddSection(type, targetId);
    setShowAddModal(false);
    setAddTargetZoneId(null);
  };

  /* ── DnD ────────────────────────────────────────────────────────── */

  const findSectionZone = (sectionId: string): string | null =>
    sectionZoneMap[sectionId] || null;

  const handleDragStart = (event: DragStartEvent) => {
    setActiveDragId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragId(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    // Entry-level DnD — delegate to parent
    if (!activeId.startsWith("sec_")) {
      onEntryDragEnd(event);
      return;
    }

    // Zone reorder (left↔right) when a zone is the active draggable.
    if (zones.some((z) => z.id === activeId) && zones.some((z) => z.id === overId)) {
      const oldIndex = zones.findIndex((z) => z.id === activeId);
      const newIndex = zones.findIndex((z) => z.id === overId);
      if (oldIndex === -1 || newIndex === -1) return;
      const reordered = arrayMove(zones, oldIndex, newIndex);
      onLayoutConfigChange({ ...layoutConfig, zones: normalizeWidths(reordered) });
      return;
    }

    // Section reorder / cross-zone move / unassigned assignment
    const sourceZoneId = findSectionZone(activeId);

    // Dropped on unassigned area — remove from placement
    if (overId === "unassigned-drop") {
      if (sourceZoneId) {
        const { [activeId]: _, ...rest } = placement;
        onLayoutConfigChange({ ...layoutConfig, zones, placement: rest });
      }
      return;
    }

    let targetZoneId: string | null = null;
    if (overId.startsWith("zone-end-")) {
      targetZoneId = overId.replace("zone-end-", "");
    } else if (overId.startsWith("sec_")) {
      targetZoneId = findSectionZone(overId) || sourceZoneId || null;
    }

    if (!targetZoneId) {
      if (sourceZoneId) targetZoneId = sourceZoneId;
      else return;
    }

    // Unassigned → zone: set placement
    if (!sourceZoneId) {
      const newPlacement = { ...placement, [activeId]: targetZoneId };
      onLayoutConfigChange({ ...layoutConfig, zones, placement: newPlacement });
      return;
    }

    if (sourceZoneId === targetZoneId) {
      // Same zone — reorder instances array so renderer sees correct order
      const ids = zoneSectionIds[sourceZoneId] || [];
      const activeIdx = ids.indexOf(activeId);
      const overIdx = ids.indexOf(overId);
      if (activeIdx === -1 || overIdx === -1) return;

      const reordered = arrayMove(ids, activeIdx, overIdx);
      const zoneInstances = reordered
        .map((id) => instances.find((i) => i.id === id)!)
        .filter(Boolean);
      const otherInstances = instances.filter(
        (i) => sectionZoneMap[i.id] !== sourceZoneId,
      );
      onReorderInstances([...otherInstances, ...zoneInstances]);
    } else {
      // Cross-zone move — update placement
      const newPlacement = { ...placement, [activeId]: targetZoneId };
      onLayoutConfigChange({ ...layoutConfig, zones, placement: newPlacement });
    }
  };

  /* ── Zone CRUD ──────────────────────────────────────────────────── */

  const handleDeleteZone = (zoneId: string) => {
    if (zones.length <= 1) return;
    const remaining = zones.filter((z) => z.id !== zoneId);
    const newPlacement = { ...placement };
    const targetZone = remaining[0];
    if (targetZone) {
      for (const inst of instances) {
        if (sectionZoneMap[inst.id] === zoneId) {
          newPlacement[inst.id] = targetZone.id;
        }
      }
    }
    onLayoutConfigChange({
      ...layoutConfig,
      zones: normalizeWidths(remaining),
      placement: newPlacement,
    });
  };

  const handleCreateZone = (zone: Zone) => {
    const requestedWidth = Math.max(15, parseInt(zone.styles?.width?.replace("%", "") || "50"));
    let newZones: Zone[];
    if (zones.length === 0) {
      newZones = [{ ...zone, styles: { ...zone.styles, width: "100%" } }];
    } else {
      const available = 100 - requestedWidth;
      const totalExisting = zones.reduce((sum, z) => sum + getWidthPercent(z), 0);
      const updatedExisting = zones.map((z) => {
        const w = getWidthPercent(z);
        const scale = totalExisting > 0 ? available / totalExisting : 1;
        return { ...z, styles: { ...z.styles, width: `${Math.round(w * scale)}%` } };
      });
      newZones = [
        ...updatedExisting,
        { ...zone, styles: { ...zone.styles, width: `${requestedWidth}%` } },
      ];
    }
    onLayoutConfigChange({ ...layoutConfig, zones: normalizeWidths(newZones) });
  };

  const handleZoneUpdate = (zone: Zone) => {
    const updatedZones = zones.map((z) => (z.id === zone.id ? zone : z));
    onLayoutConfigChange({ ...layoutConfig, zones: normalizeWidths(updatedZones) });
  };

  const draggedInstance = activeDragId
    ? instances.find((i) => i.id === activeDragId)
    : null;

  /* ── Render ─────────────────────────────────────────────────────── */

  return (
    <div data-testid="section-zone-view">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={zones.map((z) => z.id)}
          strategy={horizontalListSortingStrategy}
        >
          <div className="flex flex-row gap-2" data-testid="zone-row">
            {zones.map((zone) => (
              <ZoneBlock
                key={zone.id}
                zone={zone}
                instances={instances}
                zoneSectionIds={zoneSectionIds}
                expandedSections={expandedSections}
                editingTitle={editingTitle}
                expandedZoneStyles={expandedZoneStyles}
                assets={assets}
                onUpdateData={onUpdateData}
                onRenameInstance={onRenameInstance}
                setDeleteConfirmId={setDeleteConfirmId}
                setEditingTitle={setEditingTitle}
                toggleSectionExpand={toggleSectionExpand}
                toggleZoneStyle={toggleZoneStyle}
                handleAddSectionClick={handleAddSectionClick}
                handleDeleteZone={handleDeleteZone}
                handleZoneUpdate={handleZoneUpdate}
                readOnly={readOnly}
                selectedSectionId={selectedSectionId}
                onSelect={onSelect}
              />
            ))}
          </div>
        </SortableContext>

        <DragOverlay>
          {draggedInstance && (
            <div className="flex items-center gap-2 rounded border-2 border-blue-400 bg-white px-3 py-2 shadow-lg">
              <GripVertical className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-sm font-medium text-gray-800">
                {draggedInstance.title}
              </span>
              <span className="text-[10px] text-gray-400">
                {SECTION_LABELS[draggedInstance.type] || draggedInstance.type}
              </span>
            </div>
          )}
        </DragOverlay>

        {unassignedInstances.length > 0 && (
          <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-2">
            <p className="text-xs font-medium text-amber-700">
              {unassignedInstances.length} section(s) not assigned to any zone
            </p>
            <UnassignedDroppable />
            <SortableContext items={unassignedInstances.map((i) => i.id)} strategy={verticalListSortingStrategy}>
              <div className="mt-1 space-y-1">
                {unassignedInstances.map((inst) => (
                  <div key={inst.id}>
                    <SortableSection
                      instance={inst}
                      isExpanded={expandedSections.has(inst.id)}
                      editingTitle={editingTitle}
                      onRenameInstance={onRenameInstance}
                      setEditingTitle={setEditingTitle}
                      setDeleteConfirmId={setDeleteConfirmId}
                      onClick={() => toggleSectionExpand(inst.id)}
                      readOnly={readOnly}
                      selected={inst.id === selectedSectionId}
                      onSelect={onSelect}
                    />
                    {!readOnly && (
                      <AnimatePresence>
                        {expandedSections.has(inst.id) && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="rounded-b-lg border-x border-b bg-gray-50 p-3">
                              <SectionEditorPanel instance={inst} onChange={onUpdateData} />
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    )}
                  </div>
                ))}
              </div>
            </SortableContext>
          </div>
        )}
      </DndContext>

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => setShowZoneCreationModal(true)}
          className="flex items-center gap-1 rounded-md border border-dashed border-gray-300 px-2 py-1.5 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600"
        >
          <Plus className="h-3 w-3" />
          Add Zone
        </button>
      </div>

      <AddSectionModal
        open={showAddModal}
        onClose={() => {
          setShowAddModal(false);
          setAddTargetZoneId(null);
        }}
        onSelect={handleAddSectionWithZone}
      />

      <ZoneCreationModal
        open={showZoneCreationModal}
        onClose={() => setShowZoneCreationModal(false)}
        onCreate={handleCreateZone}
        existingZoneCount={zones.length}
      />

      <Modal open={!!deleteConfirmId} onClose={() => setDeleteConfirmId(null)}>
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Delete Section</h2>
        <p className="text-sm text-gray-600">
          Are you sure you want to delete{" "}
          <span className="font-medium text-gray-900">
            &ldquo;{instances.find((i) => i.id === deleteConfirmId)?.title}&rdquo;
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

/* ── Zone Block ──────────────────────────────────────────────────────── */

function ZoneBlock({
  zone,
  instances,
  zoneSectionIds,
  expandedSections,
  editingTitle,
  expandedZoneStyles,
  assets,
  onUpdateData,
  onRenameInstance,
  setDeleteConfirmId,
  setEditingTitle,
  toggleSectionExpand,
  toggleZoneStyle,
  handleAddSectionClick,
  handleDeleteZone,
  handleZoneUpdate,
  readOnly = false,
  selectedSectionId = null,
  onSelect,
}: {
  zone: Zone;
  instances: SectionInstance[];
  zoneSectionIds: Record<string, string[]>;
  expandedSections: Set<string>;
  editingTitle: string | null;
  expandedZoneStyles: Set<string>;
  assets?: Record<string, string>;
  onUpdateData: (id: string, data: any) => void;
  onRenameInstance: (id: string, title: string) => void;
  setDeleteConfirmId: (id: string | null) => void;
  setEditingTitle: (id: string | null) => void;
  toggleSectionExpand: (id: string) => void;
  toggleZoneStyle: (id: string) => void;
  handleAddSectionClick: (zoneId: string) => void;
  handleDeleteZone: (zoneId: string) => void;
  handleZoneUpdate: (zone: Zone) => void;
  readOnly?: boolean;
  selectedSectionId?: string | null;
  onSelect?: (id: string) => void;
}) {
  // Zone styles drive the inner content area (background/padding/width) so the
  // chrome (border/header) stays visually stable. The styles are already in
  // kebab-case from the editor and pass through unchanged.
  const zoneStyles = zone.styles || {};
  const widthPct = zoneStyles.width || "100%";
  const wrapperStyle: React.CSSProperties = { width: widthPct };
  if (zoneStyles["background-color"]) wrapperStyle.backgroundColor = zoneStyles["background-color"];
  if (zoneStyles.padding) wrapperStyle.padding = zoneStyles.padding;

  const sectionIds = zoneSectionIds[zone.id] || [];
  const zoneInstances = sectionIds
    .map((id) => instances.find((i) => i.id === id))
    .filter(Boolean) as SectionInstance[];

  const isStyleExpanded = expandedZoneStyles.has(zone.id);

  return (
    <div
      className="flex shrink-0 flex-col rounded border border-gray-100"
      style={{ width: widthPct }}
    >
      {/* Zone chrome header — kept outside the styled content area so backgrounds tint content, not chrome. */}
      <div className="flex items-center justify-between rounded-t border-b border-gray-100 bg-gray-50 px-2 py-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-gray-600">
            {zone.label || zone.id}
          </span>
          <span className="rounded bg-gray-100 px-1 py-0.5 text-[10px] text-gray-500">
            {widthPct}
          </span>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => toggleZoneStyle(zone.id)}
            className={`rounded p-0.5 ${
              isStyleExpanded
                ? "bg-blue-100 text-blue-600"
                : "text-gray-400 hover:text-gray-600"
            }`}
            title="Zone style"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
          <button
            onClick={() => handleDeleteZone(zone.id)}
            className="rounded p-0.5 text-red-400 hover:text-red-600"
            title="Delete zone"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Inline zone style editor (chrome) */}
      <AnimatePresence>
        {isStyleExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-b border-gray-100"
          >
            <div className="p-2">
              <ZoneStyleEditor zone={zone} onChange={handleZoneUpdate} assets={assets} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sections within zone — this is the content area that receives zone styles. */}
      <div
        data-testid={`zone-content-${zone.id}`}
        style={wrapperStyle}
        className="space-y-1.5 p-2"
      >
        <SortableContext items={sectionIds} strategy={verticalListSortingStrategy}>
          {zoneInstances.map((instance) => (
            <div key={instance.id}>
              <SortableSection
                instance={instance}
                isExpanded={expandedSections.has(instance.id)}
                editingTitle={editingTitle}
                onRenameInstance={onRenameInstance}
                setEditingTitle={setEditingTitle}
                setDeleteConfirmId={setDeleteConfirmId}
                onClick={() => toggleSectionExpand(instance.id)}
                readOnly={readOnly}
                selected={instance.id === selectedSectionId}
                onSelect={onSelect}
              />
              {!readOnly && (
                <AnimatePresence>
                  {expandedSections.has(instance.id) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="rounded-b-lg border-x border-b bg-gray-50 p-3">
                        <SectionEditorPanel instance={instance} onChange={onUpdateData} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              )}
            </div>
          ))}
        </SortableContext>

        <ZoneDroppable zoneId={zone.id} />

        {!readOnly && (
          <button
            onClick={() => handleAddSectionClick(zone.id)}
            className="flex w-full items-center justify-center gap-1 rounded border border-dashed border-gray-300 py-1.5 text-[11px] text-gray-400 hover:border-blue-400 hover:text-blue-600"
          >
            <Plus className="h-3 w-3" />
            Add Section
          </button>
        )}
      </div>
    </div>
  );
}
