import { useState } from "react";
import Modal from "../common/Modal";
import type { Zone } from "../../lib/sections/types";
import { percentToToken, pxToSpacingToken } from "../../lib/sections/zones";

function generateZoneId(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let id = "zone_";
  for (let i = 0; i < 6; i++) {
    id += chars[Math.floor(Math.random() * chars.length)];
  }
  return id;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreate: (zone: Zone) => void;
  existingZoneCount: number;
}

export default function ZoneCreationModal({ open, onClose, onCreate, existingZoneCount }: Props) {
  const [name, setName] = useState(`Zone ${existingZoneCount + 1}`);
  const [width, setWidth] = useState(50);
  const [padding, setPadding] = useState(24);
  const [backgroundColor, setBackgroundColor] = useState("#ffffff");

  const availableWidth = 100;
  const maxWidth = Math.max(15, availableWidth - 15);

  const handleCreate = () => {
    // The closed design vocabulary: width/padding are tokens, background is
    // a color ref. Raw CSS strings are rejected at the schema boundary.
    const styles: Record<string, string> = {
      width: percentToToken(width),
      padding: pxToSpacingToken(padding),
    };
    if (backgroundColor && backgroundColor !== "#ffffff") {
      styles.background = backgroundColor;
    }

    const zone: Zone = {
      id: generateZoneId(),
      label: name,
      styles,
    };
    onCreate(zone);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Add New Zone</h2>

      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Zone Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="e.g. Sidebar, Main, Header"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Width: {width}%</label>
          <input
            type="range"
            min={15}
            max={maxWidth}
            value={width}
            onChange={(e) => setWidth(parseInt(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-[10px] text-gray-400">
            <span>15%</span>
            <span>{maxWidth}%</span>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Padding: {padding}px</label>
          <input
            type="range"
            min={0}
            max={48}
            value={padding}
            onChange={(e) => setPadding(parseInt(e.target.value))}
            className="w-full"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="w-24 text-xs font-medium text-gray-600">Background</label>
          <input
            type="color"
            value={backgroundColor}
            onChange={(e) => setBackgroundColor(e.target.value)}
            className="h-7 w-10 cursor-pointer rounded border"
          />
          <input
            type="text"
            value={backgroundColor}
            onChange={(e) => setBackgroundColor(e.target.value)}
            className="flex-1 rounded border px-2 py-1 text-xs"
            placeholder="#RRGGBB or palette.<name>"
          />
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <button
          onClick={onClose}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onClick={handleCreate}
          disabled={!name.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          Add Zone
        </button>
      </div>
    </Modal>
  );
}
