import type { SectionData } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import { renderSectionPreview } from "./SectionRegistry";

interface Props {
  sectionType: string;
  data: SectionData;
  enabled: boolean;
}

export default function SectionPreviewPanel({ sectionType, data, enabled }: Props) {
  const sectionData = (data as any)[sectionType];

  if (!enabled) return null;

  return (
    <div className="mb-6">
      <h2 className="mb-2 text-base font-bold uppercase tracking-wide text-gray-800">
        {SECTION_LABELS[sectionType] || sectionType}
      </h2>
      {renderSectionPreview(sectionType, sectionData) || (
        <p className="text-sm text-gray-400 italic">No data</p>
      )}
    </div>
  );
}
