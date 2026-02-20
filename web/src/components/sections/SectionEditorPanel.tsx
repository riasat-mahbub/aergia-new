import type { SectionInstance } from "../../lib/sections/types";
import { renderSectionEditor } from "./SectionRegistry";

interface Props {
  instance: SectionInstance;
  onChange: (id: string, data: any) => void;
}

export default function SectionEditorPanel({ instance, onChange }: Props) {
  const handleSectionChange = (newData: any) => {
    onChange(instance.id, newData);
  };

  return (
    <div className={`rounded-lg border ${instance.enabled ? "border-gray-200" : "border-dashed border-gray-300"} bg-white p-4`}>
      {instance.enabled && renderSectionEditor(instance.type, instance.data, handleSectionChange)}
    </div>
  );
}
