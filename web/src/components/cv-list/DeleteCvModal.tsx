import Modal from "../common/Modal";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  cvTitle: string;
}

export default function DeleteCvModal({ open, onClose, onConfirm, cvTitle }: Props) {
  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-2 text-lg font-semibold text-app-ink">Delete CV</h2>
      <p className="text-sm text-app-ink-2">
        Are you sure you want to delete <span className="font-medium text-app-ink">"{cvTitle}"</span>?
        This action cannot be undone.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <button
          onClick={onClose}
          className="rounded-md border border-app-rule-strong px-4 py-2 text-sm text-app-ink-2 hover:bg-app-surface-muted"
        >
          Cancel
        </button>
        <button
          onClick={() => { onConfirm(); onClose(); }}
          className="rounded-md bg-app-danger px-4 py-2 text-sm text-white hover:bg-app-danger"
        >
          Delete
        </button>
      </div>
    </Modal>
  );
}
