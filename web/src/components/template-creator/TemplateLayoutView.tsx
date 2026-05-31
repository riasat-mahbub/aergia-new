import { useState, useMemo } from "react";
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
  horizontalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, Trash2 } from "lucide-react";
import type { Zone } from "../../lib/sections/types";
import { SECTION_TYPES, SECTION_LABELS } from "../../lib/sections/types";
import { normalizeWidths } from "../../lib/sections/zones";

interface Props {
  zones: Zone[];
  placement: Record<string, string>;
  onChange: (config: { zones: Zone[]; placement: Record<string, string> }) => void;
}

/* ── Droppable bar at bottom of each zone ──────── */

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

/* ── Dummy sortable section block (just a label + grip) ── */

function DummySortableSection({ sectionType }: { sectionType: string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: sectionType,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-1.5 rounded border border-blue-200 bg-blue-50 px-2 py-1.5 text-xs text-blue-800"
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab text-blue-400 hover:text-blue-600"
      >
        <GripVertical className="h-3 w-3" />
      </button>
      <span>{SECTION_LABELS[sectionType] || sectionType}</span>
    </div>
  );
}

/* ── Zone card (sortable) ──────────────────────── */

function ZoneCard({
  zone,
  sectionTypes,
  onDeleteZone,
  onUpdateZoneWidth,
}: {
  zone: Zone;
  sectionTypes: string[];
  onDeleteZone: (zoneId: string) => void;
  onUpdateZoneWidth: (zoneId: string, newWidth: number) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: zone.id,
  });

  const cardStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const widthPct = zone.styles?.width || "100%";

  return (
    <div
      ref={setNodeRef}
      style={{ ...cardStyle, width: widthPct }}
      className="flex shrink-0 flex-col rounded border border-gray-100 bg-gray-50"
    >
      <div className="flex items-center justify-between border-b border-gray-100 px-2 py-1">
        <div className="flex items-center gap-1.5">
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab text-gray-400 hover:text-gray-600"
            title="Drag zone"
          >
            <GripVertical className="h-3.5 w-3.5" />
          </button>
          <span className="text-[11px] font-medium text-gray-600">
            {zone.label || zone.id}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="rounded bg-gray-100 px-1 py-0.5 text-[10px] text-gray-500">
            {parseInt(widthPct)}%
          </span>
          <button
            onClick={() => onDeleteZone(zone.id)}
            className="rounded p-0.5 text-red-400 hover:text-red-600"
            title="Delete zone"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      <div className="px-2 py-1">
        <input
          type="range"
          min={15}
          max={85}
          value={parseInt(widthPct)}
          onChange={(e) => onUpdateZoneWidth(zone.id, parseInt(e.target.value))}
          className="w-full h-1"
        />
      </div>

      <div className="space-y-1 px-2 pb-2">
        {sectionTypes.map((st) => (
          <SortableContext key={st} items={[st]} strategy={verticalListSortingStrategy}>
            <DummySortableSection sectionType={st} />
          </SortableContext>
        ))}
        <ZoneDroppable zoneId={zone.id} />
      </div>
    </div>
  );
}

/* ── Main Component ───────────────────────────── */

export default function TemplateLayoutView({ zones, placement, onChange }: Props) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const [activeDragId, setActiveDragId] = useState<string | null>(null);

  /* Map: zoneId → sectionType[] */
  const zoneTypeMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    for (const zone of zones) {
      map[zone.id] = [];
    }
    for (const [sectionType, zoneId] of Object.entries(placement)) {
      if (map[zoneId]) map[zoneId].push(sectionType);
    }
    return map;
  }, [zones, placement]);

  const unassignedTypes = useMemo(
    () => SECTION_TYPES.filter((t) => !placement[t]),
    [placement],
  );

  /* ── Zone CRUD ──────────────────────────────── */

  const addZone = () => {
    const newId = `zone_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    const existingWidth = zones.reduce(
      (s, z) => s + parseInt((z.styles?.width || "100").replace("%", "")),
      0,
    );
    const newWidth = Math.min(50, 100 - existingWidth);
    const newZone: Zone = {
      id: newId,
      label: `Zone ${zones.length + 1}`,
      styles: { width: `${newWidth}%`, padding: "24px" },
    };
    const updated = zones.map((z) => {
      const w = parseInt((z.styles?.width || "100").replace("%", ""));
      const scale = existingWidth > 0 ? (100 - newWidth) / existingWidth : 1;
      return { ...z, styles: { ...z.styles, width: `${Math.round(w * scale)}%` } };
    });
    onChange({ zones: [...updated, newZone], placement });
  };

  const deleteZone = (zoneId: string) => {
    if (zones.length <= 1) return;
    const remaining = zones.filter((z) => z.id !== zoneId);
    const newPlacement = { ...placement };
    for (const [key, val] of Object.entries(placement)) {
      if (val === zoneId) delete newPlacement[key];
    }
    onChange({ zones: remaining, placement: newPlacement });
  };

  const updateZoneWidth = (zoneId: string, newWidth: number) => {
    const updated = zones.map((z) => {
      if (z.id === zoneId) {
        return { ...z, styles: { ...z.styles, width: `${newWidth}%` } };
      }
      return z;
    });
    onChange({ zones: updated, placement });
  };

  /* ── DnD ─────────────────────────────────────── */

  const handleDragStart = (event: DragStartEvent) => {
    setActiveDragId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragId(null);
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    // Zone reorder (left↔right) when both ends are zones
    if (zones.some((z) => z.id === activeId) && zones.some((z) => z.id === overId)) {
      const oldIndex = zones.findIndex((z) => z.id === activeId);
      const newIndex = zones.findIndex((z) => z.id === overId);
      if (oldIndex === -1 || newIndex === -1) return;
      onChange({
        zones: normalizeWidths(arrayMove(zones, oldIndex, newIndex)),
        placement,
      });
      return;
    }

    // Only handle section types
    if (!(SECTION_TYPES as readonly string[]).includes(activeId)) return;

    // Dropped on unassigned area — remove from placement
    if (overId === "unassigned-drop") {
      if (placement[activeId]) {
        const { [activeId]: _, ...rest } = placement;
        onChange({ zones, placement: rest });
      }
      return;
    }

    // Determine target zone
    let targetZone: string | null = null;
    if (overId.startsWith("zone-end-")) {
      targetZone = overId.replace("zone-end-", "");
    } else if ((SECTION_TYPES as readonly string[]).includes(overId)) {
      targetZone = placement[overId] || placement[activeId] || null;
    }

    if (!targetZone) return;
    if (placement[activeId] === targetZone) return;

    onChange({ zones, placement: { ...placement, [activeId]: targetZone } });
  };

  const draggedSectionType = activeDragId && (SECTION_TYPES as readonly string[]).includes(activeDragId)
    ? activeDragId
    : null;

  /* ── Render ────────────────────────────────────── */

  return (
    <div data-testid="template-layout-view">
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
              <ZoneCard
                key={zone.id}
                zone={zone}
                sectionTypes={zoneTypeMap[zone.id] || []}
                onDeleteZone={deleteZone}
                onUpdateZoneWidth={updateZoneWidth}
              />
            ))}
          </div>
        </SortableContext>

        {unassignedTypes.length > 0 && (
          <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-2">
            <p className="text-xs font-medium text-amber-700">
              {unassignedTypes.length} section(s) not assigned to any zone
            </p>
            <UnassignedDroppable />
            <SortableContext items={unassignedTypes} strategy={verticalListSortingStrategy}>
              <div className="mt-1 flex flex-wrap gap-1">
                {unassignedTypes.map((st) => (
                  <DummySortableSection key={st} sectionType={st} />
                ))}
              </div>
            </SortableContext>
          </div>
        )}

        <DragOverlay>
          {draggedSectionType && (
            <div className="flex items-center gap-1.5 rounded border border-blue-300 bg-blue-50 px-2 py-1.5 text-xs text-blue-800 shadow-lg">
              <GripVertical className="h-3 w-3 text-blue-400" />
              <span>{SECTION_LABELS[draggedSectionType] || draggedSectionType}</span>
            </div>
          )}
        </DragOverlay>
      </DndContext>

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={addZone}
          className="flex items-center gap-1 rounded-md border border-dashed border-gray-300 px-2 py-1.5 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600"
        >
          <Plus className="h-3 w-3" />
          Add Zone
        </button>
      </div>
    </div>
  );
}
