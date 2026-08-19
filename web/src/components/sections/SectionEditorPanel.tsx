import type { SectionInstance } from "../../lib/sections/types";
import { renderSectionEditor } from "./SectionRegistry";

interface Props {
  instance: SectionInstance;
  onChange: (id: string, data: any) => void;
  cvId?: string;
  mode?: "section" | "library";
  /**
   * Kept for backward compatibility with callers that pass it. The
   * Library picker is now mounted per-editor (inside `EntryAddRow`),
   * not here, so this prop is unused at the panel level.
   */
  onAddFromLibrary?: (picked: SectionInstance) => void;
}

export default function SectionEditorPanel({ instance, onChange, cvId, mode = "section" }: Props) {
  const handleSectionChange = (newData: any) => {
    onChange(instance.id, newData);
  };

  return (
    <div
      className={`rounded-lg border ${instance.enabled ? "border-app-rule" : "border-dashed border-app-rule-strong"} bg-app-surface p-4`}
    >
      {instance.enabled && renderSectionEditor(
        instance.type,
        instance.data,
        handleSectionChange,
        cvId ? { cvId, sectionId: instance.id } : undefined,
        mode,
      )}
    </div>
  );
}
