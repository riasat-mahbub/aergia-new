import { useState } from "react";
import Modal from "../common/Modal";
import type { Zone } from "../../lib/sections/types";

const FONT_OPTIONS = [
  "",
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

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
  targetRow?: number;
  availableRows?: number[];
}

export default function ZoneCreationModal({ open, onClose, onCreate, existingZoneCount, targetRow, availableRows }: Props) {
  const [name, setName] = useState(`Zone ${existingZoneCount + 1}`);
  const [width, setWidth] = useState(50);
  const [padding, setPadding] = useState(24);
  const [backgroundColor, setBackgroundColor] = useState("#ffffff");
  const [font, setFont] = useState("");
  const [textColor, setTextColor] = useState("#374151");
  const [selectedRow, setSelectedRow] = useState(targetRow ?? 0);

  const availableWidth = 100;
  const maxWidth = Math.max(15, availableWidth - 15);

  const handleCreate = () => {
    const styles: Record<string, string> = {};
    styles.width = `${width}%`;
    if (padding) styles.padding = `${padding}px`;
    if (backgroundColor && backgroundColor !== "#ffffff") styles["background-color"] = backgroundColor;
    if (font) styles.font = font;
    if (textColor && textColor !== "#374151") styles.color = textColor;

    const zone: Zone = {
      id: generateZoneId(),
      label: name,
      row: selectedRow,
      styles,
      assignedSections: [],
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

        {availableRows && availableRows.length > 0 && (
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Row</label>
            <select
              value={selectedRow}
              onChange={(e) => setSelectedRow(parseInt(e.target.value))}
              className="w-full rounded border px-2 py-1.5 text-sm"
            >
              {availableRows.map((r) => (
                <option key={r} value={r}>
                  Row {r + 1}
                </option>
              ))}
            </select>
          </div>
        )}

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
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Font</label>
          <select
            value={font}
            onChange={(e) => setFont(e.target.value)}
            className="w-full rounded border px-2 py-1.5 text-sm"
          >
            {FONT_OPTIONS.map((f) => (
              <option key={f} value={f}>
                {f ? f.split(",")[0] : "Inherit from template"}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="w-24 text-xs font-medium text-gray-600">Text Color</label>
          <input
            type="color"
            value={textColor}
            onChange={(e) => setTextColor(e.target.value)}
            className="h-7 w-10 cursor-pointer rounded border"
          />
          <input
            type="text"
            value={textColor}
            onChange={(e) => setTextColor(e.target.value)}
            className="flex-1 rounded border px-2 py-1 text-xs"
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
