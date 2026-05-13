import { useState, useMemo, useRef } from "react";
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
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, Trash2, ChevronDown, Eye, EyeOff, Pencil, Check } from "lucide-react";
import type { SectionInstance, Zone, LayoutConfig } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import {
  normalizeWidths,
  normalizeAllZones,
  getRowNumbers,
  groupByRow,
  getWidthPercent,
} from "../../lib/sections/zones";
import SectionEditorPanel from "../sections/SectionEditorPanel";
import AddSectionModal from "../sections/AddSectionModal";
import ZoneStyleEditor from "../customization/ZoneStyleEditor";
import ZoneCreationModal from "../customization/ZoneCreationModal";
import Modal from "../common/Modal";

interface Props {
  instances: SectionInstance[];
  layoutConfig: LayoutConfig;
  assets?: Record<string, string>;
  onToggle: (sectionId: string) => void;
  onUpdateData: (sectionId: string, data: any) => void;
  onAddSection: (type: string, zoneId?: string) => void;
  onRemoveInstance: (sectionId: string) => void;
  onRenameInstance: (sectionId: string, title: string) => void;
  onLayoutConfigChange: (config: LayoutConfig) => void;
  onReorderInstances: (instances: SectionInstance[]) => void;
  onEntryDragEnd: (event: DragEndEvent) => void;
}

/* ── Sortable Section ─────────────────────────────────────────────── */

function SortableSection({
  instance,
  isExpanded,
  editingTitle,
  onToggle,
  onRenameInstance,
  setEditingTitle,
  setDeleteConfirmId,
  onClick,
}: {
  instance: SectionInstance;
  isExpanded: boolean;
  editingTitle: string | null;
  onToggle: () => void;
  onRenameInstance: (id: string, title: string) => void;
  setEditingTitle: (id: string | null) => void;
  setDeleteConfirmId: (id: string | null) => void;
  onClick: () => void;
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
    if (inputRef.current && inputRef.current.value.trim()) {
      onRenameInstance(instance.id, inputRef.current.value);
    }
    setEditingTitle(null);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 rounded border px-3 py-2 ${
        instance.enabled ? "bg-white" : "bg-gray-50"
      }`}
    >
      <button
        {...attributes}
        {...listeners}
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
            <button onClick={onClick} className="text-left">
              <span
                className={`text-sm font-medium ${
                  instance.enabled ? "text-gray-800" : "text-gray-400"
                }`}
              >
                {instance.title}
              </span>
            </button>
            <span className="text-[10px] text-gray-400">
              {SECTION_LABELS[instance.type] || instance.type}
            </span>
            {isExpanded && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setEditingTitle(instance.id);
                }}
                className="flex items-center gap-0.5 rounded bg-gray-200 px-1.5 py-0.5 text-[10px] text-gray-600"
              >
                <Pencil className="h-2.5 w-2.5" /> Rename
              </button>
            )}
          </div>
        )}
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggle();
        }}
        className={`rounded p-1 ${
          instance.enabled
            ? "text-blue-600 hover:text-blue-800"
            : "text-gray-400 hover:text-gray-600"
        }`}
        title={instance.enabled ? "Disable" : "Enable"}
      >
        {instance.enabled ? (
          <Eye className="h-3.5 w-3.5" />
        ) : (
          <EyeOff className="h-3.5 w-3.5" />
        )}
      </button>

      <button
        onClick={(e) => {
          e.stopPropagation();
          setDeleteConfirmId(instance.id);
        }}
        className="rounded p-1 text-red-400 hover:text-red-600"
        title="Delete"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>

      <button onClick={onClick} className="rounded p-1 text-gray-400 hover:text-gray-600">
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </motion.div>
      </button>
    </div>
  );
}

/* ── Zone Droppable (end of list target) ───────────────────────────── */

function ZoneDroppable({ zoneId }: { zoneId: string }) {
  const { isOver, setNodeRef } = useDroppable({ id: `zone-end-${zoneId}` });
  return (
    <div
      ref={setNodeRef}
      className={`h-1 rounded transition-colors ${isOver ? "h-2 bg-blue-300" : ""}`}
    />
  );
}

function UnassignedDroppable() {
  const { isOver, setNodeRef } = useDroppable({ id: "unassigned-drop" });
  return (
    <div
      ref={setNodeRef}
      className={`h-1 rounded transition-colors ${isOver ? "h-2 bg-amber-300" : ""}`}
    />
  );
}

/* ── Main Component ───────────────────────────────────────────────── */

export default function SectionZoneView({
  instances,
  layoutConfig,
  assets,
  onToggle,
  onUpdateData,
  onAddSection,
  onRemoveInstance,
  onRenameInstance,
  onLayoutConfigChange,
  onReorderInstances,
  onEntryDragEnd,
}: Props) {
  const { zones, placement } = layoutConfig;

  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [expandedZoneStyles, setExpandedZoneStyles] = useState<Set<string>>(new Set());
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addTargetZoneId, setAddTargetZoneId] = useState<string | null>(null);
  const [showZoneCreationModal, setShowZoneCreationModal] = useState(false);
  const [selectedRowForZone, setSelectedRowForZone] = useState(0);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const containerRef = useRef<HTMLDivElement>(null);
  const horizontalDragRef = useRef<{
    rowZones: Zone[];
    globalIndices: number[];
    localIndex: number;
    startX: number;
    widths: number[];
    barWidth: number;
  } | null>(null);

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

  const rowNumbers = useMemo(() => getRowNumbers(zones), [zones]);
  const rowGroups = useMemo(() => groupByRow(zones), [zones]);

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
    const targetId = addTargetZoneId || (zones.length > 0 ? zones[0].id : undefined);
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

    // Row reorder
    if (activeId.startsWith("row-")) {
      const oldIndex = rowNumbers.indexOf(Number(activeId.replace("row-", "")));
      const newIndex = rowNumbers.indexOf(Number(overId.replace("row-", "")));
      if (oldIndex === -1 || newIndex === -1) return;

      const reorderedRowNums = arrayMove(rowNumbers, oldIndex, newIndex);
      const newMapping = new Map<number, number>();
      reorderedRowNums.forEach((oldRow, i) => newMapping.set(oldRow, i));

      const newZones = zones.map((z) => ({
        ...z,
        row: newMapping.get(z.row ?? 0) ?? 0,
      }));
      onLayoutConfigChange({ ...layoutConfig, zones: normalizeWidths(newZones) });
      return;
    }

    // Entry-level DnD — delegate to parent
    if (!activeId.startsWith("sec_")) {
      onEntryDragEnd(event);
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
    } else if (overId.startsWith("row-")) {
      const rowNum = Number(overId.replace("row-", ""));
      const rowZones = zones.filter((z) => (z.row ?? 0) === rowNum);
      if (rowZones.length > 0) targetZoneId = rowZones[0].id;
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

  /* ── Zone/Row CRUD ──────────────────────────────────────────────── */

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
    const normalized = normalizeAllZones(remaining);
    onLayoutConfigChange({ ...layoutConfig, zones: normalized, placement: newPlacement });
  };

  const handleCreateZone = (zone: Zone) => {
    const targetRow = selectedRowForZone;
    const requestedWidth = Math.max(15, parseInt(zone.styles?.width?.replace("%", "") || "50"));
    const zoneWithRow = { ...zone, row: targetRow };
    const rowZones = zones.filter((z) => (z.row ?? 0) === targetRow);
    let newZones: Zone[];
    if (rowZones.length === 0) {
      newZones = [...zones, { ...zoneWithRow, styles: { ...zoneWithRow.styles, width: "100%" } }];
    } else {
      const available = 100 - requestedWidth;
      const totalExisting = rowZones.reduce((sum, z) => sum + getWidthPercent(z), 0);
      const updatedExisting = rowZones.map((z) => {
        const w = getWidthPercent(z);
        const scale = totalExisting > 0 ? available / totalExisting : 1;
        return { ...z, styles: { ...z.styles, width: `${Math.round(w * scale)}%` } };
      });
      const otherZones = zones.filter((z) => (z.row ?? 0) !== targetRow);
      newZones = [
        ...otherZones,
        ...updatedExisting,
        { ...zoneWithRow, styles: { ...zoneWithRow.styles, width: `${requestedWidth}%` } },
      ];
    }
    const normalized = normalizeAllZones(newZones);
    onLayoutConfigChange({ ...layoutConfig, zones: normalized });
  };

  const handleAddRow = () => {
    const nextRow = rowNumbers.length > 0 ? Math.max(...rowNumbers) + 1 : 0;
    const newZone: Zone = {
      id: `zone_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
      label: `Row ${nextRow + 1}`,
      row: nextRow,
      styles: { width: "100%", padding: "24px" },
    };
    onLayoutConfigChange({ ...layoutConfig, zones: [...zones, newZone] });
  };

  const handleDeleteRow = (rowNum: number) => {
    const rowZones = zones.filter((z) => (z.row ?? 0) === rowNum);
    const remainingZones = zones.filter((z) => (z.row ?? 0) !== rowNum);
    if (remainingZones.length === 0) return;

    const newPlacement = { ...placement };
    const targetZone = remainingZones[0];
    if (targetZone) {
      for (const inst of instances) {
        const currentZone = sectionZoneMap[inst.id];
        if (currentZone && rowZones.some((z) => z.id === currentZone)) {
          newPlacement[inst.id] = targetZone.id;
        }
      }
    }
    const normalized = normalizeAllZones(remainingZones);
    onLayoutConfigChange({ ...layoutConfig, zones: normalized, placement: newPlacement });
  };

  const handleZoneUpdate = (zone: Zone) => {
    const updatedZones = zones.map((z) => (z.id === zone.id ? zone : z));
    const normalized = normalizeAllZones(updatedZones);
    onLayoutConfigChange({ ...layoutConfig, zones: normalized });
  };

  /* ── Horizontal resize ──────────────────────────────────────────── */

  const handleHorizontalMouseDown = (rowNum: number, localIndex: number, e: React.MouseEvent) => {
    e.preventDefault();
    const rowZones = zones.filter((z) => (z.row ?? 0) === rowNum);
    const barEl = containerRef.current;
    const barWidth = barEl?.getBoundingClientRect().width || 300;
    const widths = rowZones.map((z) => getWidthPercent(z));
    const globalIndices: number[] = [];
    for (const z of zones) {
      if ((z.row ?? 0) === rowNum) globalIndices.push(zones.indexOf(z));
    }

    horizontalDragRef.current = {
      rowZones,
      globalIndices,
      localIndex,
      startX: e.clientX,
      widths,
      barWidth,
    };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!horizontalDragRef.current) return;
      const {
        barWidth: bw,
        startX,
        widths: ws,
        globalIndices: gi,
        localIndex: li,
      } = horizontalDragRef.current;
      const delta = moveEvent.clientX - startX;
      const deltaPercent = (delta / bw) * 100;
      const newWidths = [...ws];
      let newLeft = newWidths[li] + deltaPercent;
      let newRight = newWidths[li + 1] - deltaPercent;
      if (newLeft < 15) {
        newLeft = 15;
        newRight = newWidths[li] + newWidths[li + 1] - 15;
      }
      if (newRight < 15) {
        newRight = 15;
        newLeft = newWidths[li] + newWidths[li + 1] - 15;
      }
      newWidths[li] = Math.round(newLeft);
      newWidths[li + 1] = Math.round(newRight);

      const updatedZones = [...zones];
      for (let i = 0; i < gi.length; i++) {
        updatedZones[gi[i]] = {
          ...updatedZones[gi[i]],
          styles: { ...updatedZones[gi[i]].styles, width: `${newWidths[i]}%` },
        };
      }
      const rowGrouped = groupByRow(updatedZones);
      const normalized: Zone[] = [];
      for (const [, rZones] of rowGrouped) normalized.push(...normalizeWidths(rZones));
      onLayoutConfigChange({ ...layoutConfig, zones: normalized });
    };

    const handleMouseUp = () => {
      horizontalDragRef.current = null;
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const draggedInstance = activeDragId
    ? instances.find((i) => i.id === activeDragId)
    : null;

  /* ── Render ─────────────────────────────────────────────────────── */

  return (
    <div ref={containerRef}>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={rowNumbers.map((r) => `row-${r}`)}
          strategy={verticalListSortingStrategy}
        >
          {rowNumbers.map((rowNum) => {
            const rowZones = rowGroups.get(rowNum) || [];
            return (
              <RowContainer
                key={rowNum}
                rowNum={rowNum}
                zones={rowZones}
                instances={instances}
                zoneSectionIds={zoneSectionIds}
                expandedSections={expandedSections}
                editingTitle={editingTitle}
                expandedZoneStyles={expandedZoneStyles}
                assets={assets}
                onToggle={onToggle}
                onUpdateData={onUpdateData}
                onRenameInstance={onRenameInstance}
                setDeleteConfirmId={setDeleteConfirmId}
                setEditingTitle={setEditingTitle}
                toggleSectionExpand={toggleSectionExpand}
                toggleZoneStyle={toggleZoneStyle}
                handleAddSectionClick={handleAddSectionClick}
                handleDeleteZone={handleDeleteZone}
                handleDeleteRow={handleDeleteRow}
                handleZoneUpdate={handleZoneUpdate}
                handleHorizontalMouseDown={handleHorizontalMouseDown}
              />
            );
          })}
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
                      onToggle={() => onToggle(inst.id)}
                      onRenameInstance={onRenameInstance}
                      setEditingTitle={setEditingTitle}
                      setDeleteConfirmId={setDeleteConfirmId}
                      onClick={() => toggleSectionExpand(inst.id)}
                    />
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
          onClick={() => {
            setSelectedRowForZone(rowNumbers[rowNumbers.length - 1] ?? 0);
            setShowZoneCreationModal(true);
          }}
          className="flex items-center gap-1 rounded-md border border-dashed border-gray-300 px-2 py-1.5 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600"
        >
          <Plus className="h-3 w-3" />
          Add Zone
        </button>
        <button
          type="button"
          onClick={handleAddRow}
          className="flex items-center gap-1 rounded-md border border-dashed border-gray-300 px-2 py-1.5 text-xs text-gray-500 hover:border-emerald-400 hover:text-emerald-600"
        >
          <Plus className="h-3 w-3" />
          Add Row
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
        targetRow={selectedRowForZone}
        availableRows={rowNumbers}
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

/* ── Row Container ──────────────────────────────────────────────────── */

function RowContainer({
  rowNum,
  zones: rowZones,
  instances,
  zoneSectionIds,
  expandedSections,
  editingTitle,
  expandedZoneStyles,
  assets,
  onToggle,
  onUpdateData,
  onRenameInstance,
  setDeleteConfirmId,
  setEditingTitle,
  toggleSectionExpand,
  toggleZoneStyle,
  handleAddSectionClick,
  handleDeleteZone,
  handleDeleteRow,
  handleZoneUpdate,
  handleHorizontalMouseDown,
}: {
  rowNum: number;
  zones: Zone[];
  instances: SectionInstance[];
  zoneSectionIds: Record<string, string[]>;
  expandedSections: Set<string>;
  editingTitle: string | null;
  expandedZoneStyles: Set<string>;
  assets?: Record<string, string>;
  onToggle: (id: string) => void;
  onUpdateData: (id: string, data: any) => void;
  onRenameInstance: (id: string, title: string) => void;
  setDeleteConfirmId: (id: string | null) => void;
  setEditingTitle: (id: string | null) => void;
  toggleSectionExpand: (id: string) => void;
  toggleZoneStyle: (id: string) => void;
  handleAddSectionClick: (zoneId: string) => void;
  handleDeleteZone: (zoneId: string) => void;
  handleDeleteRow: (rowNum: number) => void;
  handleZoneUpdate: (zone: Zone) => void;
  handleHorizontalMouseDown: (rowNum: number, localIndex: number, e: React.MouseEvent) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `row-${rowNum}`,
  });

  const rowStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={rowStyle} className="relative mb-4 rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b bg-gray-50 px-3 py-1.5">
        <div className="flex items-center gap-2">
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab text-gray-400 hover:text-gray-600"
            title="Drag row"
          >
            <GripVertical className="h-3.5 w-3.5" />
          </button>
          <span className="text-xs font-medium text-gray-500">Row {rowNum + 1}</span>
        </div>
        <button
          onClick={() => handleDeleteRow(rowNum)}
          className="rounded p-1 text-red-400 hover:text-red-600"
          title="Delete row"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>

      <div className="flex p-3">
        {rowZones.map((zone, idx) => (
          <div key={zone.id} className="relative flex-1" style={{ width: zone.styles?.width }}>
            {!idx && idx > 0 && (
              <div
                onMouseDown={(e) => handleHorizontalMouseDown(rowNum, idx - 1, e)}
                className="absolute inset-y-0 left-0 w-1 cursor-col-resize hover:bg-blue-400 active:bg-blue-500"
                style={{ zIndex: 10 }}
              />
            )}
            <ZoneBlock
              zone={zone}
              instances={instances}
              zoneSectionIds={zoneSectionIds}
              expandedSections={expandedSections}
              editingTitle={editingTitle}
              expandedZoneStyles={expandedZoneStyles}
              assets={assets}
              onToggle={onToggle}
              onUpdateData={onUpdateData}
              onRenameInstance={onRenameInstance}
              setDeleteConfirmId={setDeleteConfirmId}
              setEditingTitle={setEditingTitle}
              toggleSectionExpand={toggleSectionExpand}
              toggleZoneStyle={toggleZoneStyle}
              handleAddSectionClick={handleAddSectionClick}
              handleDeleteZone={handleDeleteZone}
              handleZoneUpdate={handleZoneUpdate}
            />
          </div>
        ))}
      </div>
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
  onToggle,
  onUpdateData,
  onRenameInstance,
  setDeleteConfirmId,
  setEditingTitle,
  toggleSectionExpand,
  toggleZoneStyle,
  handleAddSectionClick,
  handleDeleteZone,
  handleZoneUpdate,
}: {
  zone: Zone;
  instances: SectionInstance[];
  zoneSectionIds: Record<string, string[]>;
  expandedSections: Set<string>;
  editingTitle: string | null;
  expandedZoneStyles: Set<string>;
  assets?: Record<string, string>;
  onToggle: (id: string) => void;
  onUpdateData: (id: string, data: any) => void;
  onRenameInstance: (id: string, title: string) => void;
  setDeleteConfirmId: (id: string | null) => void;
  setEditingTitle: (id: string | null) => void;
  toggleSectionExpand: (id: string) => void;
  toggleZoneStyle: (id: string) => void;
  handleAddSectionClick: (zoneId: string) => void;
  handleDeleteZone: (zoneId: string) => void;
  handleZoneUpdate: (zone: Zone) => void;
}) {
  const zoneStyle = zone.styles || {};
  const widthPct = zoneStyle.width || "100%";
  const bgColor = zoneStyle["background-color"] || "";

  const sectionIds = zoneSectionIds[zone.id] || [];
  const zoneInstances = sectionIds
    .map((id) => instances.find((i) => i.id === id))
    .filter(Boolean) as SectionInstance[];

  const isStyleExpanded = expandedZoneStyles.has(zone.id);

  return (
    <div
      className="flex flex-col rounded border border-gray-100"
      style={bgColor ? { backgroundColor: bgColor } : undefined}
    >
      {/* Zone header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-2 py-1">
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

      {/* Inline zone style editor */}
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

      {/* Sections within zone */}
      <div className="space-y-1.5 p-2">
        <SortableContext items={sectionIds} strategy={verticalListSortingStrategy}>
          {zoneInstances.map((instance) => (
            <div key={instance.id}>
              <SortableSection
                instance={instance}
                isExpanded={expandedSections.has(instance.id)}
                editingTitle={editingTitle}
                onToggle={() => onToggle(instance.id)}
                onRenameInstance={onRenameInstance}
                setEditingTitle={setEditingTitle}
                setDeleteConfirmId={setDeleteConfirmId}
                onClick={() => toggleSectionExpand(instance.id)}
              />
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
            </div>
          ))}
        </SortableContext>

        <ZoneDroppable zoneId={zone.id} />

        <button
          onClick={() => handleAddSectionClick(zone.id)}
          className="flex w-full items-center justify-center gap-1 rounded border border-dashed border-gray-300 py-1.5 text-[11px] text-gray-400 hover:border-blue-400 hover:text-blue-600"
        >
          <Plus className="h-3 w-3" />
          Add Section
        </button>
      </div>
    </div>
  );
}
