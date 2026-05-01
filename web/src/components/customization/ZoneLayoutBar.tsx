import { useState, useRef, useCallback } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Plus, Trash2, GripVertical } from "lucide-react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Zone, LayoutConfig } from "../../lib/sections/types";
import {
  normalizeWidths,
  getWidthPercent,
  getRowNumbers,
  groupByRow,
  normalizeAllZones,
} from "../../lib/sections/zones";
import { SECTION_TYPES } from "../../lib/sections/types";
import ZoneStyleEditor from "./ZoneStyleEditor";
import ZoneCreationModal from "./ZoneCreationModal";

interface Props {
  layoutConfig: LayoutConfig;
  onChange: (config: LayoutConfig) => void;
}


/* ── Sortable Row Item ─────────────────────────────────────────────── */

interface SortableRowProps {
  rowNum: number;
  rowZones: Zone[];
  selectedZoneId: string | null;
  onSelectZone: (id: string | null) => void;
  onDeleteZone: (id: string) => void;
  onMouseDownHorizontal: (rowNum: number, localIndex: number, e: React.MouseEvent) => void;
  onDeleteRow: (rowNum: number) => void;
}

function SortableRow({
  rowNum,
  rowZones,
  selectedZoneId,
  onSelectZone,
  onDeleteZone,
  onMouseDownHorizontal,
  onDeleteRow,
}: SortableRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `row-${rowNum}`,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : undefined,
    opacity: isDragging ? 0.8 : 1,
    flexBasis: 0,
    flexGrow: 1,
    position: "relative",
  };

  return (
    <div ref={setNodeRef} style={style} className="flex flex-col">
      <div className="flex items-center gap-1 border-b border-gray-200 bg-gray-50 px-2 py-1">
        <button
          type="button"
          className="cursor-grab text-gray-400 hover:text-gray-600 active:cursor-grabbing"
          title="Drag to reorder row"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-3 w-3" />
        </button>
        <span className="flex-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
          Row {rowNum + 1}
        </span>
        <button
          type="button"
          onClick={() => onDeleteRow(rowNum)}
          className="text-gray-300 hover:text-red-500"
          title="Delete row"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>

      <div className="flex flex-1 items-center px-2 py-1">
        <div className="flex flex-1 overflow-hidden rounded border border-gray-200 bg-white">
          {rowZones.map((zone, localIndex) => {
            const width = getWidthPercent(zone);
            const isSelected = selectedZoneId === zone.id;
            return (
              <div key={zone.id} className="flex" style={{ width: `${width}%` }}>
                <button
                  type="button"
                  onClick={() => onSelectZone(isSelected ? null : zone.id)}
                  className={`flex flex-1 items-center justify-between px-2 py-1.5 text-xs font-medium transition-colors ${
                    isSelected ? "bg-emerald-50 text-emerald-700" : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <span className="truncate">{zone.label || zone.id}</span>
                  <span className="ml-1 text-[10px] text-gray-400">{width}%</span>
                </button>
                {rowZones.length > 1 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteZone(zone.id);
                    }}
                    className="flex items-center justify-center px-1 text-gray-300 hover:text-red-500"
                    title="Remove zone"
                  >
                    <span className="text-xs">x</span>
                  </button>
                )}
                {localIndex < rowZones.length - 1 && (
                  <div
                    onMouseDown={(e) => onMouseDownHorizontal(rowNum, localIndex, e)}
                    className="flex w-1.5 cursor-col-resize items-center justify-center bg-gray-100 hover:bg-gray-200"
                    title="Drag to resize"
                  >
                    <div className="h-3 w-px bg-gray-300" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── Main Component ─────────────────────────────────────────────── */

export default function ZoneLayoutBar({ layoutConfig, onChange }: Props) {
  const { zones, placement } = layoutConfig;
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createTargetRow, setCreateTargetRow] = useState<number>(0);

  const horizontalDragRef = useRef<{
    rowZones: Zone[];
    globalIndices: number[];
    localIndex: number;
    startX: number;
    widths: number[];
    barWidth: number;
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const rowNumbers = getRowNumbers(zones);
  const rowGroups = groupByRow(zones);

  /* ── Zone width drag ──────────────────────────────────────────── */
  const handleHorizontalMouseDown = useCallback(
    (rowNum: number, localIndex: number, e: React.MouseEvent) => {
      e.preventDefault();
      const rowZones = zones.filter((z) => (z.row ?? 0) === rowNum);
      const barEl = containerRef.current;
      const barWidth = barEl?.getBoundingClientRect().width || 300;
      const widths = rowZones.map((z) => getWidthPercent(z));
      const globalIndices: number[] = [];
      for (const z of zones) {
        if ((z.row ?? 0) === rowNum) globalIndices.push(zones.indexOf(z));
      }

      horizontalDragRef.current = { rowZones, globalIndices, localIndex, startX: e.clientX, widths, barWidth };

      const handleMouseMove = (moveEvent: MouseEvent) => {
        if (!horizontalDragRef.current) return;
        const { barWidth: bw, startX, widths: ws, globalIndices: gi, localIndex: li } = horizontalDragRef.current;
        const delta = moveEvent.clientX - startX;
        const deltaPercent = (delta / bw) * 100;
        const newWidths = [...ws];
        let newLeft = newWidths[li] + deltaPercent;
        let newRight = newWidths[li + 1] - deltaPercent;
        if (newLeft < 15) { newLeft = 15; newRight = newWidths[li] + newWidths[li + 1] - 15; }
        if (newRight < 15) { newRight = 15; newLeft = newWidths[li] + newWidths[li + 1] - 15; }
        newWidths[li] = Math.round(newLeft);
        newWidths[li + 1] = Math.round(newRight);

        const updatedZones = [...zones];
        for (let i = 0; i < gi.length; i++) {
          updatedZones[gi[i]] = { ...updatedZones[gi[i]], styles: { ...updatedZones[gi[i]].styles, width: `${newWidths[i]}%` } };
        }
        // Normalize widths per row (not globally)
        const rowGrouped = groupByRow(updatedZones);
        const normalized: Zone[] = [];
        for (const [, rZones] of rowGrouped) normalized.push(...normalizeWidths(rZones));
        onChange({ ...layoutConfig, zones: normalized });
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
    },
    [layoutConfig, onChange]
  );

  /* ── DnD row reorder ──────────────────────────────────────────── */
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = rowNumbers.indexOf(Number(String(active.id).replace("row-", "")));
      const newIndex = rowNumbers.indexOf(Number(String(over.id).replace("row-", "")));
      if (oldIndex === -1 || newIndex === -1) return;

      const reorderedRowNums = arrayMove(rowNumbers, oldIndex, newIndex);

      // Remap all zones to new sequential row numbers
      const newMapping = new Map<number, number>();
      reorderedRowNums.forEach((oldRow, i) => { newMapping.set(oldRow, i); });

      const newZones = zones.map((z) => ({ ...z, row: newMapping.get(z.row ?? 0) ?? 0 }));

      onChange({ ...layoutConfig, zones: normalizeWidths(newZones) });
    },
    [layoutConfig, onChange, rowNumbers, zones]
  );

  /* ── Zone CRUD ────────────────────────────────────────────────── */
  const handleDeleteZone = (zoneId: string) => {
    if (zones.length <= 1) return;
    const deletedZone = zones.find((z) => z.id === zoneId);
    const remaining = zones.filter((z) => z.id !== zoneId);
    const newPlacement = { ...placement };
    if (deletedZone?.assignedSections) {
      const targetZone = remaining[0];
      if (targetZone) {
        for (const section of deletedZone.assignedSections) newPlacement[section] = targetZone.id;
      }
    }
    const normalized = normalizeAllZones(remaining);
    onChange({ ...layoutConfig, zones: normalized, placement: newPlacement });
    if (selectedZoneId === zoneId) setSelectedZoneId(null);
  };

  const handleCreateZone = (zone: Zone) => {
    const targetRow = createTargetRow;
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
      newZones = [...otherZones, ...updatedExisting, { ...zoneWithRow, styles: { ...zoneWithRow.styles, width: `${requestedWidth}%` } }];
    }
    const normalized = normalizeAllZones(newZones);
    onChange({ ...layoutConfig, zones: normalized });
  };

  const handleAddRow = () => {
    const nextRow = rowNumbers.length > 0 ? Math.max(...rowNumbers) + 1 : 0;
    const newZone: Zone = {
      id: `zone_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
      label: `Row ${nextRow + 1}`,
      row: nextRow,
      styles: { width: "100%", padding: "24px" },
      assignedSections: [],
    };
    onChange({ ...layoutConfig, zones: [...zones, newZone] });
  };

const handleDeleteRow = (rowNum: number) => {
    const rowZones = zones.filter((z) => (z.row ?? 0) === rowNum);
    const remainingZones = zones.filter((z) => (z.row ?? 0) !== rowNum);
    if (remainingZones.length === 0) return;

    const newPlacement = { ...placement };
    const remainingRowNums = getRowNumbers(remainingZones);
    const targetZone = remainingZones.find((z) => (z.row ?? 0) === remainingRowNums[0]);
    if (targetZone) {
      for (const dz of rowZones) {
        if (dz.assignedSections) {
          for (const section of dz.assignedSections) newPlacement[section] = targetZone.id;
        }
      }
    }
    const normalized = normalizeAllZones(remainingZones);
    onChange({ ...layoutConfig, zones: normalized, placement: newPlacement });
    if (selectedZoneId && rowZones.some((z) => z.id === selectedZoneId)) setSelectedZoneId(null);
  };

  const handleZoneUpdate = (zone: Zone) => {
    const updatedZones = zones.map((z) => (z.id === zone.id ? zone : z));
    const normalized = normalizeAllZones(updatedZones);
    onChange({ ...layoutConfig, zones: normalized });
  };

  const handleAssignSection = (zoneId: string, sectionType: string) => {
    const newPlacement = { ...placement };
    const oldZoneId = newPlacement[sectionType];
    const updatedZones = zones.map((z) => {
      if (z.id === oldZoneId) return { ...z, assignedSections: (z.assignedSections || []).filter((s) => s !== sectionType) };
      if (z.id === zoneId) return { ...z, assignedSections: [...(z.assignedSections || []), sectionType] };
      return z;
    });
    newPlacement[sectionType] = zoneId;
    onChange({ ...layoutConfig, zones: updatedZones, placement: newPlacement });
  };

  const handleUnassignSection = (zoneId: string, sectionType: string) => {
    const newPlacement = { ...placement };
    delete newPlacement[sectionType];
    const updatedZones = zones.map((z) => {
      if (z.id === zoneId) return { ...z, assignedSections: (z.assignedSections || []).filter((s) => s !== sectionType) };
      return z;
    });
    onChange({ ...layoutConfig, zones: updatedZones, placement: newPlacement });
  };

  const handleMoveZoneToRow = (zoneId: string, newRow: number) => {
    const updatedZones = zones.map((z) => (z.id === zoneId ? { ...z, row: newRow } : z));
    const normalized = normalizeAllZones(updatedZones);
    onChange({ ...layoutConfig, zones: normalized });
  };

  const selectedZone = zones.find((z) => z.id === selectedZoneId);

  return (
    <div ref={containerRef}>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={rowNumbers.map((r) => `row-${r}`)} strategy={verticalListSortingStrategy}>
          {rowNumbers.map((rowNum) => {
            const rowZones = rowGroups.get(rowNum) || [];
            return (
              <SortableRow
                key={rowNum}
                rowNum={rowNum}
                rowZones={rowZones}
                selectedZoneId={selectedZoneId}
                onSelectZone={setSelectedZoneId}
                onDeleteZone={handleDeleteZone}
                onMouseDownHorizontal={handleHorizontalMouseDown}
                onDeleteRow={handleDeleteRow}
              />
            );
          })}
        </SortableContext>
      </DndContext>

      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={() => {
            setCreateTargetRow(rowNumbers[rowNumbers.length - 1] ?? 0);
            setShowCreateModal(true);
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

      <AnimatePresence>
        {selectedZone && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2">
              <ZoneStyleEditor
                zone={selectedZone}
                onChange={handleZoneUpdate}
                allSectionTypes={[...SECTION_TYPES]}
                assignedSections={selectedZone.assignedSections || []}
                onAssignSection={(sectionType) => handleAssignSection(selectedZone.id, sectionType)}
                onUnassignSection={(sectionType) => handleUnassignSection(selectedZone.id, sectionType)}
                availableRows={rowNumbers}
                onMoveToRow={(row) => handleMoveZoneToRow(selectedZone.id, row)}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ZoneCreationModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateZone}
        existingZoneCount={zones.length}
        targetRow={createTargetRow}
        availableRows={rowNumbers}
      />
    </div>
  );
}
