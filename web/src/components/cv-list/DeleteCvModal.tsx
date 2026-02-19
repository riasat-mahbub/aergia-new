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
      <h2 className="mb-2 text-lg font-semibold text-gray-900">Delete CV</h2>
      <p className="text-sm text-gray-600">
        Are you sure you want to delete <span className="font-medium text-gray-900">"{cvTitle}"</span>?
        This action cannot be undone.
      </p>
      <div className="mt-6 flex justify-end gap-2">
        <button
          onClick={onClose}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onClick={() => { onConfirm(); onClose(); }}
          className="rounded-md bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
        >
          Delete
        </button>
      </div>
    </Modal>
  );
}
