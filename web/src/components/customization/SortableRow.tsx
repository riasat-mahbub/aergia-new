
/* ── Sortable Row Item ─────────────────────────────────────────────── */
import { useSortable } from "@dnd-kit/sortable";
import { Zone } from "../../lib/sections/types";
import { GripVertical, Trash2 } from "lucide-react";
import { getWidthPercent } from "../../lib/sections/zones";
import { CSS } from "@dnd-kit/utilities";

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

export default SortableRow;