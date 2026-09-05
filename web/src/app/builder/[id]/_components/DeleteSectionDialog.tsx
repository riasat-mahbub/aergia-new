import Modal from "@/components/common/Modal";

interface DeleteSectionDialogProps {
  open: boolean;
  title?: string;
  onClose: () => void;
  onConfirm: () => void;
}

export default function DeleteSectionDialog({
  open,
  title,
  onClose,
  onConfirm,
}: DeleteSectionDialogProps) {
  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-2 text-lg font-semibold text-app-ink">Delete Section</h2>
      <p className="text-sm text-app-ink-2">
        Are you sure you want to delete{" "}
        <span className="font-medium text-app-ink">&ldquo;{title}&rdquo;</span>? This action cannot be undone.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <button
          onClick={onClose}
          className="rounded-md border border-app-rule-strong px-4 py-2 text-sm text-app-ink-2 hover:bg-app-surface-muted"
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          className="rounded-md bg-app-danger px-4 py-2 text-sm text-white hover:bg-app-danger"
        >
          Delete
        </button>
      </div>
    </Modal>
  );
}
