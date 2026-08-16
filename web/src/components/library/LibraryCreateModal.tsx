import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import Modal from "../common/Modal";
import SectionEditorPanel from "../sections/SectionEditorPanel";
import {
  LIBRARY_KINDS,
  LIBRARY_KIND_LABELS,
  sectionTypeForLibraryKind,
  type LibraryEntry,
  type LibraryEntryKind,
} from "../../lib/api/library";
import { createDefaultSectionData } from "../../lib/sections/types";
import { useLibraryStore } from "../../lib/store/libraryStore";

interface LibraryCreateModalProps {
  open: boolean;
  onClose: () => void;
  initialKind?: LibraryEntryKind;
  entry?: LibraryEntry | null;
  onSaved?: (entry: LibraryEntry) => void;
}

export default function LibraryCreateModal({
  open,
  onClose,
  initialKind,
  entry = null,
  onSaved,
}: LibraryCreateModalProps) {
  const create = useLibraryStore((s) => s.create);
  const update = useLibraryStore((s) => s.update);
  const [kind, setKind] = useState<LibraryEntryKind | undefined>(() => entry?.kind ?? initialKind);
  const [data, setData] = useState<unknown>(() =>
    entry ? entry.payload : initialKind ? createDefaultSectionData(sectionTypeForLibraryKind(initialKind)) : [],
  );
  const [saving, setSaving] = useState(false);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    if (!initializedRef.current) {
      initializedRef.current = true;
      return;
    }
    const nextKind = entry?.kind ?? initialKind;
    setKind(nextKind);
    setData(
      entry
        ? entry.payload.map((row) => ({ ...row }))
        : nextKind
          ? createDefaultSectionData(sectionTypeForLibraryKind(nextKind))
          : [],
    );
  }, [open, entry, initialKind]);
  const handleKindSelect = (k: LibraryEntryKind) => {
    setKind(k);
    setData(createDefaultSectionData(sectionTypeForLibraryKind(k)));
  };

  const handleSave = async () => {
    if (!kind || !Array.isArray(data)) return;
    setSaving(true);
    try {
      const saved = entry
        ? await update(entry.id, data as Array<Record<string, unknown>>)
        : await create(kind, data as Array<Record<string, unknown>>);
      onSaved?.(saved);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose}>
      <div className="max-h-[80vh] w-[min(640px,90vw)] bg-lib-surface text-lib-ink">
        <header className="mb-4">
          <h2 className="text-xl font-semibold text-lib-ink">{entry ? "Edit library entry" : "New library entry"}</h2>
          {!kind && (
            <p className="mt-1 text-sm text-lib-ink-2">Pick the type of content to add.</p>
          )}
        </header>

        {!kind ? (
          <div className="grid grid-cols-2 gap-2">
            {LIBRARY_KINDS.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => handleKindSelect(k)}
                className="rounded-md border border-lib-rule bg-lib-surface px-4 py-3 text-left text-sm font-medium text-lib-ink hover:bg-lib-surface-2"
              >
                {LIBRARY_KIND_LABELS[k]}
              </button>
            ))}
          </div>
        ) : (
          <>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-lib-ink-3">
              {LIBRARY_KIND_LABELS[kind]}
            </p>
            <div className="max-h-[55vh] overflow-y-auto rounded-md border border-lib-rule bg-lib-surface-2 p-3">
              <SectionEditorPanel
                instance={{
                  id: "lib_draft",
                  type: sectionTypeForLibraryKind(kind),
                  title: LIBRARY_KIND_LABELS[kind],
                  enabled: true,
                  data: data as never,
                  style: null,
                }}
                onChange={(_id, newData) => setData(newData)}
              />
            </div>
            <footer className="mt-4 flex items-center justify-end gap-2">
              {!entry && (
                <button
                  type="button"
                  onClick={() => setKind(undefined)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-lib-ink-2 hover:bg-lib-surface-2"
                >
                  Change type
                </button>
              )}
              <motion.button
                type="button"
                onClick={handleSave}
                disabled={saving}
                whileTap={{ scale: 0.97 }}
                className="rounded-md bg-lib-accent px-4 py-2 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover disabled:opacity-50"
              >
                {saving ? "Saving…" : entry ? "Save changes" : "Save to library"}
              </motion.button>
            </footer>
          </>
        )}
      </div>
    </Modal>
  );
}
