import { useState } from "react";
import { Plus, Library as LibraryIcon } from "lucide-react";
import { isLibraryKind, type LibraryEntryKind } from "../../../lib/api/library";
import LibraryPicker from "../../library/LibraryPicker";

interface EntryAddRowProps {
  /** Section kind, e.g. "experience". Drives the picker filter. */
  kind: string;
  /** Friendly label for the "new item" button, e.g. "Experience". */
  addLabel: string;
  /** Called when the user wants a blank entry. */
  onAddNew: () => void;
  /**
   * Called when the user picks a library entry. The shape matches the
   * backend's `LibraryCloneResponse.section_instance` (a permissive
   * record so each editor can pick out the fields it cares about).
   */
  onPickFromLibrary?: (picked: Record<string, unknown> | null) => void;
}


/**
 * Bottom row of every entry-based section editor. Renders two parallel
 * buttons: one to add a blank item, one to pull an entry from the
 * user's Library. The library button is omitted for ineligible kinds
 * (profile, summary, research, extras).
 */
export default function EntryAddRow({
  kind,
  addLabel,
  onAddNew,
  onPickFromLibrary,
}: EntryAddRowProps) {
  const eligible = isLibraryKind(kind);
  const [pickerOpen, setPickerOpen] = useState(false);

  const handlePick = (picked: Record<string, unknown> | null) => {
    setPickerOpen(false);
    if (picked && onPickFromLibrary) onPickFromLibrary(picked);
  };

  return (
    <div className="flex items-center gap-2 pt-1">
      <button
        type="button"
        onClick={onAddNew}
        className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <Plus className="h-3.5 w-3.5" />
        <span>Add {addLabel}</span>
      </button>
      {eligible && onPickFromLibrary && (
        <>
          <button
            type="button"
            onClick={() => setPickerOpen(true)}
            className="inline-flex items-center gap-1 rounded-md bg-lib-accent px-3 py-1.5 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover"
          >
            <LibraryIcon className="h-3.5 w-3.5" />
            <span>Add from library</span>
          </button>
          <LibraryPicker
            open={pickerOpen}
            onClose={() => setPickerOpen(false)}
            kind={kind as LibraryEntryKind}
            onPick={handlePick}
          />
        </>
      )}
    </div>
  );
}
