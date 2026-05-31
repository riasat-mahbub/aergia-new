import { motion } from "motion/react";
import type { UserTemplate } from "../../lib/api/templates";

interface Props {
  template: UserTemplate;
  onSelect: (templateId: string) => void;
}

function renderThumbnail(manifest: any) {
  if (!manifest?.zones || manifest.zones.length === 0) {
    return (
      <div className="flex h-full w-2/3 flex-col items-center justify-center gap-1">
        <div className="h-px w-8 bg-gray-8 bg-gray-300" />
        <div className="h-1.5 w-6 rounded bg-gray-200" />
      </div>
    );
  }

  const zones = manifest.zones;
  const defaultWidth = `${100 / zones.length}%`;

  return (
    <div className="flex h-full w-2/3 gap-0.5">
      {zones.map((zone: any) => (
        <div
          key={zone.id}
          className="h-full rounded"
          style={{
            width: zone.styles?.width || defaultWidth,
            backgroundColor: zone.styles?.["background-color"] || "transparent",
            border: zone.styles?.["background-color"] ? "none" : "1px dashed #d1d5db",
          }}
        />
      ))}
    </div>
  );
}

export default function BaseTemplateCard({ template, onSelect }: Props) {
  const manifest = template.manifest;

  return (
    <motion.button
      type="button"
      whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(template.id)}
      className="flex w-full flex-col items-start rounded-xl border-2 border-gray-200 bg-white p-5 text-left transition-all hover:border-blue-400"
    >
      <div className="mb-3 flex h-16 w-full items-center justify-center rounded-lg bg-gray-50">
        {renderThumbnail(manifest)}
      </div>

      <h3 className="text-sm font-semibold text-gray-900">{template.name}</h3>
      {template.description && (
        <p className="mt-1 line-clamp-2 text-xs text-gray-500">{template.description}</p>
      )}
    </motion.button>
  );
}
