import { useState, useRef, useCallback } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Plus } from "lucide-react";
import type { Zone, LayoutConfig } from "../../lib/sections/types";
import { SECTION_TYPES } from "../../lib/sections/types";
import ZoneStyleEditor from "./ZoneStyleEditor";
import ZoneCreationModal from "./ZoneCreationModal";

interface Props {
  zones: Zone[];
  placement: Record<string, string>;
  onChange: (config: LayoutConfig) => void;
}

function getWidthPercent(zone: Zone): number {
  const w = zone.styles?.width || "";
  const num = parseInt(w.replace("%", ""));
  return isNaN(num) ? 0 : num;
}

function normalizeWidths(zones: Zone[]): Zone[] {
  if (zones.length === 0) return zones;

  const rawWidths = zones.map((z) => {
    const w = z.styles?.width || "";
    const num = parseInt(w.replace("%", ""));
    return isNaN(num) ? 100 / zones.length : num;
  });

  const total = rawWidths.reduce((sum, w) => sum + w, 0);
  if (total === 0) {
    const equal = Math.floor(100 / zones.length);
    return zones.map((z, i) => ({
      ...z,
      styles: { ...z.styles, width: `${equal + (i === 0 ? 100 - equal * zones.length : 0)}%` },
    }));
  }

  const scale = 100 / total;
  const scaled = rawWidths.map((w) => w * scale);
  const floored = scaled.map((w) => Math.floor(w));
  const remainders = scaled.map((w, i) => ({ index: i, remainder: w - floored[i] }));
  remainders.sort((a, b) => b.remainder - a.remainder);

  let remainder = 100 - floored.reduce((sum, w) => sum + w, 0);
  for (let i = 0; i < remainder; i++) {
    floored[remainders[i].index]++;
  }

  return zones.map((z, i) => ({
    ...z,
    styles: { ...z.styles, width: `${floored[i]}%` },
  }));
}

export default function ZoneLayoutBar({ zones, placement, onChange }: Props) {
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const dragRef = useRef<{ index: number; startX: number; widths: number[] } | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  const allSectionTypes = [...SECTION_TYPES];

  const handleMouseDown = useCallback(
    (index: number, e: React.MouseEvent) => {
      e.preventDefault();
      const barWidth = barRef.current?.getBoundingClientRect().width || 300;
      const widths = zones.map((z) => getWidthPercent(z));
      dragRef.current = { index, startX: e.clientX, widths };

      const handleMouseMove = (moveEvent: MouseEvent) => {
        if (!dragRef.current) return;
        const delta = moveEvent.clientX - dragRef.current.startX;
        const deltaPercent = (delta / barWidth) * 100;

        const newWidths = [...dragRef.current.widths];
        const leftIdx = index;
        const rightIdx = index + 1;

        let newLeft = newWidths[leftIdx] + deltaPercent;
        let newRight = newWidths[rightIdx] - deltaPercent;

        if (newLeft < 15) {
          newLeft = 15;
          newRight = newWidths[leftIdx] + newWidths[rightIdx] - 15;
        }
        if (newRight < 15) {
          newRight = 15;
          newLeft = newWidths[leftIdx] + newWidths[rightIdx] - 15;
        }

        newWidths[leftIdx] = Math.round(newLeft);
        newWidths[rightIdx] = Math.round(newRight);

        const updatedZones = zones.map((z, i) => ({
          ...z,
          styles: { ...z.styles, width: `${newWidths[i]}%` },
        }));
        onChange({ zones: normalizeWidths(updatedZones), placement });
      };

      const handleMouseUp = () => {
        dragRef.current = null;
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
    [zones, placement, onChange]
  );

  const handleDeleteZone = (zoneId: string) => {
    if (zones.length <= 1) return;
    const deletedZone = zones.find((z) => z.id === zoneId);
    const remaining = zones.filter((z) => z.id !== zoneId);

    const updatedZones = normalizeWidths(remaining);

    const newPlacement = { ...placement };
    if (deletedZone?.assignedSections) {
      const targetZone = updatedZones[0];
      if (targetZone) {
        targetZone.assignedSections = [
          ...(targetZone.assignedSections || []),
          ...deletedZone.assignedSections,
        ];
        for (const section of deletedZone.assignedSections) {
          newPlacement[section] = targetZone.id;
        }
      }
    }

    onChange({ zones: updatedZones, placement: newPlacement });
    if (selectedZoneId === zoneId) setSelectedZoneId(null);
  };

  const handleCreateZone = (zone: Zone) => {
    const requestedWidth = Math.max(15, parseInt(zone.styles?.width?.replace("%", "") || "50"));

    let newZones: Zone[];
    if (zones.length === 0) {
      newZones = [{ ...zone, styles: { ...zone.styles, width: "100%" } }];
    } else {
      const totalExisting = zones.reduce((sum, z) => sum + getWidthPercent(z), 0);
      const available = 100 - requestedWidth;

      if (totalExisting > 0 && available > 0) {
        const scale = available / totalExisting;
        const scaledZones = zones.map((z) => {
          const w = getWidthPercent(z);
          return { ...z, styles: { ...z.styles, width: `${Math.round(w * scale)}%` } };
        });
        newZones = [...scaledZones, { ...zone, styles: { ...zone.styles, width: `${requestedWidth}%` } }];
      } else {
        newZones = [...zones, { ...zone, styles: { ...zone.styles, width: `${requestedWidth}%` } }];
      }
    }

    const normalized = normalizeWidths(newZones);
    onChange({ zones: normalized, placement });
  };

  const handleZoneUpdate = (zone: Zone) => {
    const updatedZones = zones.map((z) => (z.id === zone.id ? zone : z));
    onChange({ zones: normalizeWidths(updatedZones), placement });
  };

  const handleAssignSection = (zoneId: string, sectionType: string) => {
    const newPlacement = { ...placement };
    const oldZoneId = newPlacement[sectionType];
    if (oldZoneId) {
      const oldZone = zones.find((z) => z.id === oldZoneId);
      if (oldZone) {
        const updatedOldZone = {
          ...oldZone,
          assignedSections: (oldZone.assignedSections || []).filter((s) => s !== sectionType),
        };
        const updatedZones = zones.map((z) => (z.id === oldZoneId ? updatedOldZone : z));
        newPlacement[sectionType] = zoneId;
        const targetZone = updatedZones.find((z) => z.id === zoneId);
        if (targetZone) {
          targetZone.assignedSections = [...(targetZone.assignedSections || []), sectionType];
        }
        onChange({ zones: updatedZones, placement: newPlacement });
        return;
      }
    }
    newPlacement[sectionType] = zoneId;
    const updatedZones = zones.map((z) => {
      if (z.id === zoneId) {
        return { ...z, assignedSections: [...(z.assignedSections || []), sectionType] };
      }
      return z;
    });
    onChange({ zones: updatedZones, placement: newPlacement });
  };

  const handleUnassignSection = (zoneId: string, sectionType: string) => {
    const newPlacement = { ...placement };
    delete newPlacement[sectionType];
    const updatedZones = zones.map((z) => {
      if (z.id === zoneId) {
        return { ...z, assignedSections: (z.assignedSections || []).filter((s) => s !== sectionType) };
      }
      return z;
    });
    onChange({ zones: updatedZones, placement: newPlacement });
  };

  const selectedZone = zones.find((z) => z.id === selectedZoneId);

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <div ref={barRef} className="flex flex-1 overflow-hidden rounded-lg border border-gray-200">
          {zones.map((zone, index) => {
            const width = getWidthPercent(zone);
            const isSelected = selectedZoneId === zone.id;
            return (
              <div key={zone.id} className="flex" style={{ width: `${width}%` }}>
                <button
                  type="button"
                  onClick={() => setSelectedZoneId(isSelected ? null : zone.id)}
                  className={`flex flex-1 items-center justify-between px-2 py-2 text-xs font-medium transition-colors ${
                    isSelected
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <span className="truncate">{zone.label || zone.id}</span>
                  <span className="ml-1 text-[10px] text-gray-400">{width}%</span>
                </button>
                {zones.length > 1 && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteZone(zone.id);
                    }}
                    className="flex items-center justify-center px-1 text-gray-300 hover:text-red-500"
                    title="Remove zone"
                  >
                    <span className="text-xs">x</span>
                  </button>
                )}
                {index < zones.length - 1 && (
                  <div
                    onMouseDown={(e) => handleMouseDown(index, e)}
                    className="flex w-1.5 cursor-col-resize items-center justify-center bg-gray-100 hover:bg-gray-200"
                    title="Drag to resize"
                  >
                    <div className="h-4 w-px bg-gray-300" />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-1 rounded-md border border-dashed border-gray-300 px-2 py-2 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600"
        >
          <Plus className="h-3 w-3" />
          Add Zone
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
            <ZoneStyleEditor
              zone={selectedZone}
              onChange={handleZoneUpdate}
              allSectionTypes={allSectionTypes}
              assignedSections={selectedZone.assignedSections || []}
              onAssignSection={(sectionType) => handleAssignSection(selectedZone.id, sectionType)}
              onUnassignSection={(sectionType) => handleUnassignSection(selectedZone.id, sectionType)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <ZoneCreationModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateZone}
        existingZoneCount={zones.length}
      />
    </div>
  );
}
