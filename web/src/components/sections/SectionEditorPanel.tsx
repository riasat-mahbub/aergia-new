import { Eye, EyeOff } from "lucide-react";
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
        <button
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
          className={`rounded p-1 transition-colors ${enabled ? "text-blue-600 hover:text-blue-800" : "text-gray-400 hover:text-gray-600"}`}
          title={enabled ? "Disable section" : "Enable section"}
        >
          {enabled ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
        </button>
      </div>
      {enabled && renderSectionEditor(sectionType, sectionData, handleSectionChange)}
    </div>
  );
}
