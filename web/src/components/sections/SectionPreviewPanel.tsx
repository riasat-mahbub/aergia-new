import type { SectionInstance } from "../../lib/sections/types";
import { renderSectionPreview } from "./SectionRegistry";

interface Props {
  instance: SectionInstance;
}

export default function SectionPreviewPanel({ instance }: Props) {
  if (!instance.enabled) return null;

  return (
    <div className="mb-6">
      <h2 className="mb-2 text-base font-bold uppercase tracking-wide text-gray-800">
        {instance.title}
      </h2>
      {renderSectionPreview(instance.type, instance.data) || (
        <p className="text-sm text-gray-400 italic">No data</p>
      )}
    </div>
  );
}
