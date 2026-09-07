import { useId, useRef, useState, type ReactNode } from "react";
import Modal from "./Modal";

type ConfirmResult = void | Promise<void>;

interface ConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => ConfirmResult;
  onError: (error: unknown) => void;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
}

const CONFIRM_BUTTON_STYLES = {
  danger: "bg-app-danger text-white hover:bg-app-danger/90",
  primary: "bg-app-primary text-white hover:bg-app-primary-hover",
} as const;

export default function ConfirmModal({
  open,
  onClose,
  onConfirm,
  onError,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
}: ConfirmModalProps) {
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  const handleConfirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await onConfirm();
      onClose();
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={busy ? () => undefined : onClose}
      titleId={titleId}
      descriptionId={descriptionId}
      initialFocusRef={cancelRef}
    >
      <h2 id={titleId} className="mb-2 text-lg font-semibold text-app-ink">{title}</h2>
      <div id={descriptionId} className="text-sm text-app-ink-2">{description}</div>
      <div className="mt-6 flex justify-end gap-2">
        <button
          ref={cancelRef}
          type="button"
          onClick={onClose}
          disabled={busy}
          className="rounded-md border border-app-rule-strong px-4 py-2 text-sm text-app-ink-2 hover:bg-app-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          {cancelLabel}
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={busy}
          className={`rounded-md px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${CONFIRM_BUTTON_STYLES[variant]}`}
        >
          {busy ? "Working…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
