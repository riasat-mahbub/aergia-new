import { useState } from "react";
import Modal from "../common/Modal";

interface AddToLibraryConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  /** Short label for the entry, shown in the modal copy. */
  entryLabel?: string;
}

/**
 * Confirmation modal for "Add this CV entry to your Library".
 *
 * Title: "Add to library"
 * Body: explains the snapshot semantics — the entry lives in both
 * places independently once added.
 * Actions: Cancel (ghost) and Add to library (primary emerald).
 */
export default function AddToLibraryConfirmModal({
  open,
  onClose,
  onConfirm,
  entryLabel,
}: AddToLibraryConfirmModalProps) {
  const [busy, setBusy] = useState(false);

  const handleConfirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={busy ? () => undefined : onClose}>
      <div className="bg-lib-surface text-lib-ink">
        <h2 className="text-xl font-semibold text-lib-ink">Add to library</h2>
        <p className="mt-2 text-sm text-lib-ink-2">
          {entryLabel ? (
            <>
              Copy <span className="font-medium">{entryLabel}</span> to your Library.
              It will be available across all your CVs.
            </>
          ) : (
            <>Copy this entry to your Library. It will be available across all your CVs.</>
          )}
        </p>
        <p className="mt-2 text-xs text-lib-ink-3">
          Existing CVs are not affected — your entry here stays in this CV.
        </p>
        <div className="mt-6 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-md border border-lib-rule bg-lib-surface px-4 py-2 text-sm font-medium text-lib-ink-2 hover:bg-lib-surface-2 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={busy}
            className="rounded-md bg-lib-accent px-4 py-2 text-sm font-medium text-lib-accent-ink hover:bg-lib-accent-hover disabled:opacity-50"
          >
            {busy ? "Adding…" : "Add to library"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
