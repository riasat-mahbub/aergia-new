import { Plus } from "lucide-react";
import type { LibraryEntry, LibraryEntryKind } from "../../lib/api/library";
import { LIBRARY_KIND_LABELS } from "../../lib/api/library";
import LibraryEntryCard from "./LibraryEntryCard";

interface LibraryKindGroupProps {
  kind: LibraryEntryKind;
  entries: LibraryEntry[];
  onAdd?: () => void;
  onEditEntry?: (entry: LibraryEntry) => void;
  onDeleteEntry?: (entry: LibraryEntry) => void;
  onPickEntry?: (entry: LibraryEntry) => void;
}

export default function LibraryKindGroup({
  kind,
  entries,
  onAdd,
  onEditEntry,
  onDeleteEntry,
  onPickEntry,
}: LibraryKindGroupProps) {
  const label = LIBRARY_KIND_LABELS[kind];

  return (
    <section className="space-y-3" aria-labelledby={`lib-group-${kind}`}>
      <div className="flex items-center justify-between border-b border-lib-rule pb-2">
        <div className="flex items-baseline gap-2">
          <h2
            id={`lib-group-${kind}`}
            className="text-xs font-semibold uppercase tracking-wider text-lib-ink-2"
          >
            {label}
          </h2>
          <span className="text-xs text-lib-ink-3">· {entries.length}</span>
        </div>
        {onAdd && (
          <button
            type="button"
            onClick={onAdd}
            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-lib-accent hover:bg-lib-accent-soft"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add</span>
          </button>
        )}
      </div>

      {entries.length === 0 ? (
        <p className="rounded-md border border-dashed border-lib-rule px-4 py-3 text-sm text-lib-ink-3">
          No {label.toLowerCase()} yet.
        </p>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <div
              key={entry.id}
              onClick={onPickEntry ? () => onPickEntry(entry) : undefined}
              role={onPickEntry ? "button" : undefined}
              tabIndex={onPickEntry ? 0 : undefined}
            >
              <LibraryEntryCard
                entry={entry}
                onEdit={onEditEntry ? () => onEditEntry(entry) : undefined}
                onDelete={onDeleteEntry ? () => onDeleteEntry(entry) : undefined}
                interactive={!!onPickEntry}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
