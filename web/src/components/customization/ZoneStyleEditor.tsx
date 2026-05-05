import type { Zone } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";

const FONT_OPTIONS = [
  "",
  "Inter, system-ui, sans-serif",
  "Georgia, Crimson, serif",
  "system-ui, sans-serif",
  "Arial, Helvetica, sans-serif",
  "Times New Roman, serif",
  "Courier New, monospace",
];

interface Props {
  zone: Zone;
  onChange: (zone: Zone) => void;
  allSectionTypes: string[];
  assignedSections: string[];
  onAssignSection: (sectionType: string) => void;
  onUnassignSection: (sectionType: string) => void;
  availableRows?: number[];
  onMoveToRow?: (row: number) => void;
  assets?: Record<string, string>; // asset name -> data URL
}

export default function ZoneStyleEditor({ zone, onChange, allSectionTypes, assignedSections, onAssignSection, onUnassignSection, availableRows, onMoveToRow, assets = {} }: Props) {
  const styles = zone.styles || {};

  const getStyle = (key: string): string => styles[key] ?? "";
  const getStyleNumber = (key: string, unit: string): number => {
    const val = styles[key] || "";
    return parseInt(val.replace(unit, "")) || 0;
  };

  const updateStyle = (key: string, value: string) => {
    const newStyles = { ...styles, [key]: value };
    if (!value) delete newStyles[key];
    onChange({ ...zone, styles: newStyles });
  };

  const updateLabel = (label: string) => {
    onChange({ ...zone, label });
  };

  const widthVal = getStyleNumber("width", "%") || 50;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Zone: {zone.label || zone.id}
      </div>

      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Name</label>
          <input
            type="text"
            value={zone.label || ""}
            onChange={(e) => updateLabel(e.target.value)}
            className="w-full rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
            placeholder="Zone name"
          />
        </div>

        {availableRows && onMoveToRow && availableRows.length > 1 && (
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Row</label>
            <select
              value={zone.row ?? 0}
              onChange={(e) => onMoveToRow(parseInt(e.target.value))}
              className="w-full rounded border px-2 py-1 text-xs"
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
          <label className="mb-1 block text-xs font-medium text-gray-600">Width: {widthVal}%</label>
          <input
            type="range"
            min={15}
            max={85}
            value={widthVal}
            onChange={(e) => updateStyle("width", `${e.target.value}%`)}
            className="w-full"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Padding: {getStyleNumber("padding", "px") || 0}px
          </label>
          <input
            type="range"
            min={0}
            max={48}
            value={getStyleNumber("padding", "px")}
            onChange={(e) => updateStyle("padding", `${e.target.value}px`)}
            className="w-full"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="w-20 text-xs font-medium text-gray-600">Background</label>
          <input
            type="color"
            value={getStyle("background-color") || "#ffffff"}
            onChange={(e) => updateStyle("background-color", e.target.value)}
            className="h-7 w-10 cursor-pointer rounded border"
          />
          <input
            type="text"
            value={getStyle("background-color") || ""}
            onChange={(e) => updateStyle("background-color", e.target.value)}
            className="flex-1 rounded border px-2 py-1 text-xs"
            placeholder="Transparent"
          />
        </div>

        {/* Background Image Section */}
        <div className="space-y-2 border-t pt-3">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Background Image</div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Image</label>
            <select
              value={getStyle("background-image") || ""}
              onChange={(e) => updateStyle("background-image", e.target.value || "")}
              className="w-full rounded border px-2 py-1 text-xs"
            >
              <option value="">None</option>
              {Object.keys(assets).map((name) => (
                <option key={name} value={`url(${assets[name]})`}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          {getStyle("background-image") && (
            <div className="space-y-2 mt-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Position X: {getStyleNumber("background-position-x", "%") || 50}%
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={getStyleNumber("background-position-x", "%") || 50}
                  onChange={(e) => updateStyle("background-position-x", `${e.target.value}%`)}
                  className="w-full"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Position Y: {getStyleNumber("background-position-y", "%") || 50}%
                </label>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={getStyleNumber("background-position-y", "%") || 50}
                  onChange={(e) => updateStyle("background-position-y", `${e.target.value}%`)}
                  className="w-full"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">
                  Size: {getStyleNumber("background-size", "%") || 100}%
                </label>
                <input
                  type="range"
                  min={50}
                  max={200}
                  value={getStyleNumber("background-size", "%") || 100}
                  onChange={(e) => updateStyle("background-size", `${e.target.value}%`)}
                  className="w-full"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="w-20 text-xs font-medium text-gray-600">Repeat</label>
                <select
                  value={getStyle("background-repeat") || "no-repeat"}
                  onChange={(e) => updateStyle("background-repeat", e.target.value || "no-repeat")}
                  className="flex-1 rounded border px-2 py-1 text-xs"
                >
                  <option value="no-repeat">No Repeat</option>
                  <option value="repeat">Repeat</option>
                  <option value="repeat-x">Repeat X</option>
                  <option value="repeat-y">Repeat Y</option>
                </select>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 pt-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Border</div>

          <div className="space-y-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Width: {getStyleNumber("border-width", "px") || 0}px
              </label>
              <input
                type="range"
                min={0}
                max={4}
                value={getStyleNumber("border-width", "px")}
                onChange={(e) => updateStyle("border-width", `${e.target.value}px`)}
                className="w-full"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="w-20 text-xs font-medium text-gray-600">Color</label>
              <input
                type="color"
                value={getStyle("border-color") || "#d1d5db"}
                onChange={(e) => updateStyle("border-color", e.target.value)}
                className="h-7 w-10 cursor-pointer rounded border"
              />
              <input
                type="text"
                value={getStyle("border-color") || ""}
                onChange={(e) => updateStyle("border-color", e.target.value)}
                className="flex-1 rounded border px-2 py-1 text-xs"
                placeholder="Default"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Radius: {getStyleNumber("border-radius", "px") || 0}px
              </label>
              <input
                type="range"
                min={0}
                max={16}
                value={getStyleNumber("border-radius", "px")}
                onChange={(e) => updateStyle("border-radius", `${e.target.value}px`)}
                className="w-full"
              />
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Typography</div>

          <div className="space-y-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Font</label>
              <select
                value={getStyle("font")}
                onChange={(e) => updateStyle("font", e.target.value)}
                className="w-full rounded border px-2 py-1 text-xs"
              >
                {FONT_OPTIONS.map((f) => (
                  <option key={f} value={f}>
                    {f ? f.split(",")[0] : "Inherit from template"}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="w-20 text-xs font-medium text-gray-600">Text Color</label>
              <input
                type="color"
                value={getStyle("color") || "#374151"}
                onChange={(e) => updateStyle("color", e.target.value)}
                className="h-7 w-10 cursor-pointer rounded border"
              />
              <input
                type="text"
                value={getStyle("color") || ""}
                onChange={(e) => updateStyle("color", e.target.value)}
                className="flex-1 rounded border px-2 py-1 text-xs"
                placeholder="Default"
              />
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Sections</div>
          <div className="flex flex-wrap gap-1">
            {allSectionTypes.map((sectionType) => {
              const isAssigned = assignedSections.includes(sectionType);
              return (
                <button
                  key={sectionType}
                  type="button"
                  onClick={() => {
                    if (isAssigned) {
                      onUnassignSection(sectionType);
                    } else {
                      onAssignSection(sectionType);
                    }
                  }}
                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
                    isAssigned
                      ? "bg-blue-100 text-blue-700 hover:bg-blue-200"
                      : "border border-gray-200 bg-gray-50 text-gray-400 hover:border-gray-300 hover:bg-gray-100"
                  }`}
                >
                  {SECTION_LABELS[sectionType] || sectionType}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
