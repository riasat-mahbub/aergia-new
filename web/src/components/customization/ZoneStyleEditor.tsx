import type { Zone } from "../../lib/sections/types";
import { getWidthPercent, percentToToken, spacingTokenToCss, pxToSpacingToken } from "../../lib/sections/zones";

interface Props {
  zone: Zone;
  onChange: (zone: Zone) => void;
  assets?: Record<string, string>; // asset name -> data URL
}

// Zone styles speak the closed design vocabulary (width / background /
// padding tokens). The manifest and the resolver reject raw CSS strings,
// so the editor quantizes slider input to tokens at the wire boundary.
export default function ZoneStyleEditor({ zone, onChange, assets = {} }: Props) {
  void assets; // kept in the props contract for callers; no asset UI in the closed vocabulary
  const styles = zone.styles || {};

  const widthPercent = getWidthPercent(zone);
  const paddingPx = parseInt(spacingTokenToCss(styles.padding)) || 0;
  const background = styles.background || "";

  const updateStyle = (key: "width" | "padding" | "background", value: string) => {
    const newStyles = { ...styles };
    if (key === "width") newStyles.width = value as typeof styles.width;
    else if (key === "padding") newStyles.padding = value as typeof styles.padding;
    else if (key === "background") newStyles.background = value || null;
    onChange({ ...zone, styles: newStyles });
  };

  const updateLabel = (label: string) => {
    onChange({ ...zone, label });
  };

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
            placeholder="e.g. Sidebar"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Width: {widthPercent || "auto"}%
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={widthPercent}
            onChange={(e) => updateStyle("width", percentToToken(parseInt(e.target.value)))}
            className="w-full"
          />
          <div className="flex justify-between text-[10px] text-gray-400">
            <span>0 (auto)</span>
            <span>100</span>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Padding: {paddingPx}px
          </label>
          <input
            type="range"
            min={0}
            max={48}
            value={paddingPx}
            onChange={(e) => updateStyle("padding", pxToSpacingToken(parseInt(e.target.value)))}
            className="w-full"
          />
        </div>

        <div className="flex items-center gap-2">
          <label className="w-20 text-xs font-medium text-gray-600">Background</label>
          <input
            type="color"
            value={/^#[0-9a-fA-F]{6}$/.test(background) ? background : "#ffffff"}
            onChange={(e) => updateStyle("background", e.target.value)}
            className="h-7 w-10 cursor-pointer rounded border"
          />
          <input
            type="text"
            value={background}
            onChange={(e) => updateStyle("background", e.target.value)}
            className="flex-1 rounded border px-2 py-1 text-xs"
            placeholder="#RRGGBB or palette.<name>"
          />
        </div>
      </div>
    </div>
  );
}
