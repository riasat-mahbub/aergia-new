import { useEffect, useState } from "react";
import Modal from "../common/Modal";
import { useToastStore } from "../../lib/store/uiStore";
import { useLibraryStore } from "../../lib/store/libraryStore";
import type { LibraryEntry, LibraryEntryKind } from "../../lib/api/library";
import {
  LIBRARY_KIND_LABELS,
  cloneLibrary,
  sectionTypeForLibraryKind,
} from "../../lib/api/library";
import LibraryEntryCard from "./LibraryEntryCard";

interface LibraryPickerProps {
  open: boolean;
  onClose: () => void;
  kind: LibraryEntryKind;
  /** Receives the cloned SectionInstance, or `null` if the user picked "+ Add new item instead". */
  onPick: (sectionInstance: Record<string, unknown> | null) => void;
}

export default function LibraryPicker({ open, onClose, kind, onPick }: LibraryPickerProps) {
  // Defensive: handle every non-array case at the entry point so the
  // filter() and length checks below cannot throw under any prop shape.
  // `?? []` only catches null/undefined; Array.isArray catches anything
  // else (object, array-like, primitives leaked through HMR).
  const rawEntries = useLibraryStore((s) => s.entries);
  const entries: LibraryEntry[] = Array.isArray(rawEntries) ? rawEntries : [];
  const filtered = entries.filter((e) => e.kind === kind);
  const fetchAll = useLibraryStore((s) => s.fetchAll);
  const addToast = useToastStore((s) => s.addToast);
  const [picking, setPicking] = useState<string | null>(null);

  useEffect(() => {
    if (open && entries.length === 0) {
      fetchAll();
    }
  }, [open, entries.length, fetchAll]);

  const handlePick = async (entry: LibraryEntry) => {
    if (picking) return;
    setPicking(entry.id);
    try {
      const resp = await cloneLibrary(entry.id);
      const inst = {
        ...resp.section_instance,
        type: sectionTypeForLibraryKind(kind),
      };
      const title = inst.title || entry.kind;
      addToast(`Added ${title} to ${LIBRARY_KIND_LABELS[kind]}`, "success");
      onPick(inst as unknown as Record<string, unknown>);
      onClose();
    } catch {
      addToast("Failed to add entry from the Library", "error");
    } finally {
      setPicking(null);
    }
  };

  return (
    <Modal open={open} onClose={onClose}>
      <div className="bg-lib-surface text-lib-ink">
        <header className="mb-3">
          <h2 className="text-xl font-semibold text-lib-ink">Add from library</h2>
          <p className="mt-0.5 text-sm font-medium text-lib-ink-3">
            {LIBRARY_KIND_LABELS[kind]}
          </p>
        </header>

        <div className="my-3 h-px bg-lib-rule" />

        {filtered.length === 0 ? (
          <div className="space-y-4 py-4 text-center">
            <p className="text-sm text-lib-ink-2">
              No library entries yet for {LIBRARY_KIND_LABELS[kind].toLowerCase()}.
            </p>
            <div className="flex flex-col items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  window.open(
                    `/dashboard/library?kind=${kind}`,
                    "_blank",
                    "noopener,noreferrer",
                  );
                }}
                className="inline-flex items-center rounded-md bg-lib-accent px-4 py-2 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover"
              >
                Create one
              </button>
              <button
                type="button"
                onClick={() => {
                  onPick(null);
                  onClose();
                }}
                className="text-sm font-medium text-lib-accent hover:underline"
              >
                + Add new item instead
              </button>
            </div>
          </div>
        ) : (
          <>
            <ul className="max-h-[60vh] space-y-2 overflow-y-auto pr-1">
              {filtered.map((entry) => (
                <li key={entry.id}>
                  <LibraryEntryCard
                    entry={entry}
                    interactive
                    onEdit={undefined}
                    onDelete={undefined}
                    showMeta
                  />
                  <button
                    type="button"
                    onClick={() => handlePick(entry)}
                    disabled={picking === entry.id}
                    className="sr-only"
                    aria-label={`Add ${kind} entry`}
                  >
                    Add
                  </button>
                  <div className="-mt-1 flex justify-end">
                    <button
                      type="button"
                      onClick={() => handlePick(entry)}
                      disabled={picking === entry.id}
                      className="rounded px-3 py-1 text-xs font-medium text-lib-accent hover:bg-lib-accent-soft disabled:opacity-50"
                    >
                      {picking === entry.id ? "Adding…" : "+ Add"}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <footer className="mt-4 flex items-center justify-between border-t border-lib-rule pt-3">
              <span className="text-xs text-lib-ink-3">Don&apos;t see it?</span>
              <button
                type="button"
                onClick={() => {
                  window.open(
                    `/dashboard/library?kind=${kind}`,
                    "_blank",
                    "noopener,noreferrer",
                  );
                }}
                className="text-xs font-medium text-lib-accent hover:underline"
              >
                + Create in library
              </button>
            </footer>
          </>
        )}
      </div>
    </Modal>
  );
}
