import type { SectionData } from "../../lib/sections/types";
import { SECTION_LABELS } from "../../lib/sections/types";
import { renderSectionEditor } from "./SectionRegistry";

interface Props {
  sectionType: string;
  data: SectionData;
  enabled: boolean;
  onToggle: () => void;
  onChange: (data: SectionData) => void;
}

export default function SectionEditorPanel({ sectionType, data, enabled, onToggle, onChange }: Props) {
  const sectionData = (data as any)[sectionType];

  const handleSectionChange = (newData: any) => {
    onChange({ ...data, [sectionType]: newData });
  };

  return (
    <div className={`rounded-lg border ${enabled ? "border-gray-200" : "border-dashed border-gray-300"} bg-white p-4`}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">{SECTION_LABELS[sectionType] || sectionType}</h3>
        <label className="flex items-center gap-2 text-sm text-gray-500">
          <input type="checkbox" checked={enabled} onChange={onToggle} />
          Enabled
        </label>
      </div>
      {enabled && renderSectionEditor(sectionType, sectionData, handleSectionChange)}
    </div>
  );
}
