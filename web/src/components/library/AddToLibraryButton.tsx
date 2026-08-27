import { useState } from "react";
import { Archive } from "lucide-react";
import { addEntryToLibrary, type LibraryEntryKind } from "../../lib/api/library";
import { useToastStore } from "../../lib/store/uiStore";
import { useLibraryStore } from "../../lib/store/libraryStore";
import AddToLibraryConfirmModal from "./AddToLibraryConfirmModal";

interface AddToLibraryButtonProps {
  cvId: string;
  sectionId: string;
  entryId: string;
  kind: LibraryEntryKind;
  entryData: Record<string, unknown>;
  /** Short label shown in the confirmation modal copy. */
  entryLabel?: string;
}

/**
 * Renders an "Add to library" button that opens a confirmation modal,
 * posts to the per-entry add endpoint, and toasts the result.
 *
 * Library entries are deduped on the server via content hash — calling
 * twice for the same entry produces one Library entry and the second
 * click is treated as a no-op success.
 */
export default function AddToLibraryButton({
  cvId,
  sectionId,
  entryId,
  kind,
  entryData,
  entryLabel,
}: AddToLibraryButtonProps) {
  const [open, setOpen] = useState(false);
  const addToast = useToastStore((s) => s.addToast);
  const fetchAll = useLibraryStore((s) => s.fetchAll);

  const handleConfirm = async () => {
    try {
      const resp = await addEntryToLibrary(cvId, sectionId, entryId, { kind, entry: entryData });
      if (resp.created) {
        addToast(entryLabel ? `Added "${entryLabel}" to Library.` : "Added to Library.", "success");
      } else {
        addToast("Already in your Library.", "info");
      }
      await fetchAll();
      setOpen(false);
    } catch (e) {
      addToast(
        `Add to library failed: ${e instanceof Error ? e.message : "unknown error"}`,
        "error",
      );
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        className="inline-flex items-center gap-1 text-xs font-medium text-lib-accent hover:underline"
      >
        <Archive className="h-3 w-3" />
        Add to library
      </button>
      <AddToLibraryConfirmModal
        open={open}
        onClose={() => setOpen(false)}
        onConfirm={handleConfirm}
        entryLabel={entryLabel}
      />
    </>
  );
}
