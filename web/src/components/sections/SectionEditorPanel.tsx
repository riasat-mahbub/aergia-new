import { useState } from "react";
import { Plus } from "lucide-react";
import type { SectionInstance } from "../../lib/sections/types";
import { renderSectionEditor } from "./SectionRegistry";
import LibraryPicker from "../library/LibraryPicker";
import type { LibraryEntryKind } from "../../lib/api/library";

// Section types that the Library can supply. Matches the service-side
// `LIBRARY_ENTRY_KINDS` set; ``profile`` and ``summary`` are excluded
// because their data shape is a dict, not a list of entries.
const LIBRARY_ELIGIBLE_TYPES: Record<string, true> = {
  experience: true,
  education: true,
  skill: true,
  project: true,
  certification: true,
  language: true,
};

interface Props {
  instance: SectionInstance;
  onChange: (id: string, data: any) => void;
  /**
   * Called when the user picks a Library entry. Receives the cloned
   * SectionInstance ready to merge into the parent CV.
   */
  onAddFromLibrary?: (picked: SectionInstance) => void;
}

export default function SectionEditorPanel({
  instance,
  onChange,
  onAddFromLibrary,
}: Props) {
  const [pickerOpen, setPickerOpen] = useState(false);

  const handleSectionChange = (newData: any) => {
    onChange(instance.id, newData);
  };

  const eligible = LIBRARY_ELIGIBLE_TYPES[instance.type] === true;
  const libraryKind = eligible ? (instance.type as LibraryEntryKind) : null;

  const handlePick = (picked: SectionInstance | null) => {
    setPickerOpen(false);
    if (picked && onAddFromLibrary) {
      onAddFromLibrary(picked);
    }
  };

  return (
    <div
      className={`rounded-lg border ${instance.enabled ? "border-gray-200" : "border-dashed border-gray-300"} bg-white p-4`}
    >
      {instance.enabled && eligible && libraryKind && (
        <div className="mb-3 flex items-center justify-between border-b border-gray-100 pb-2">
          <span className="text-xs font-medium text-gray-500">Library</span>
          <button
            type="button"
            onClick={() => setPickerOpen(true)}
            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
          >
            <Plus className="h-3 w-3" />
            Add from library
          </button>
        </div>
      )}
      {instance.enabled && renderSectionEditor(instance.type, instance.data, handleSectionChange)}

      {libraryKind && (
        <LibraryPicker
          open={pickerOpen}
          onClose={() => setPickerOpen(false)}
          kind={libraryKind}
          onPick={(picked) => {
            handlePick(picked as unknown as SectionInstance | null);
          }}
        />
      )}
    </div>
  );
}
