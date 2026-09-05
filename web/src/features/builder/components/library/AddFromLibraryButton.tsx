import { useState } from "react";
import { Library as LibraryIcon } from "lucide-react";
import type { LibraryEntryKind } from "@/features/library";
import LibraryPicker from "./LibraryPicker";

interface AddFromLibraryButtonProps {
  kind: LibraryEntryKind;
  onPick: (picked: Record<string, unknown> | null) => void;
}

/** Library-specific host action used by the builder's section editors. */
export default function AddFromLibraryButton({ kind, onPick }: AddFromLibraryButtonProps) {
  const [open, setOpen] = useState(false);

  const handlePick = (picked: Record<string, unknown> | null) => {
    setOpen(false);
    onPick(picked);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 rounded-md bg-lib-accent px-3 py-1.5 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover"
      >
        <LibraryIcon className="h-3.5 w-3.5" />
        <span>Add from library</span>
      </button>
      <LibraryPicker
        open={open}
        onClose={() => setOpen(false)}
        kind={kind}
        onPick={handlePick}
      />
    </>
  );
}
