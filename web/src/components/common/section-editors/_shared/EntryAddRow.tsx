import type { ReactNode } from "react";
import { Plus } from "lucide-react";

interface EntryAddRowProps {
  /** Friendly label for the "new item" button, e.g. "Experience". */
  addLabel: string;
  /** Called when the user wants a blank entry. */
  onAddNew: () => void;
  /** Optional host-provided secondary action, such as "Add from library". */
  secondaryAction?: ReactNode;
}

/**
 * Bottom row of every entry-based section editor. The editor owns the blank
 * item action; hosts may inject a secondary action without coupling this
 * shared primitive to a feature such as Library.
 */
export default function EntryAddRow({
  addLabel,
  onAddNew,
  secondaryAction,
}: EntryAddRowProps) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <button
        type="button"
        onClick={onAddNew}
        className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong bg-app-surface px-3 py-1.5 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"
      >
        <Plus className="h-3.5 w-3.5" />
        <span>Add {addLabel}</span>
      </button>
      {secondaryAction}
    </div>
  );
}
