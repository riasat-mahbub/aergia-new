/**
 * ResetFooter — template switcher + reset-to-defaults button.
 *
 * Replaces the small "Template" button at the top of the old panel.
 * The template display now shows the actual template name from the
 * manifest (not `templateId.split("-")[1]` which produced "modern" for
 * generic-modern).
 *
 * Reset wipes section-local style overrides and legacy style values, then
 * re-applies the template defaults. Destructive — opens a confirmation
 * modal before executing. Layout placement is preserved.
 */

import { useState } from "react";
import Modal from "@/shared/ui/Modal";
import ConfirmModal from "@/shared/ui/ConfirmModal";
import { useToastStore } from "@/shared/state/uiStore";
import { accent, danger, ink, radius, ruleDefault } from "@/styles/tokens";

interface Props {
  templateName: string;
  onChangeTemplate: () => void | Promise<void>;
  onReset: () => void;
  /** Whether there's anything to reset — disable when there's nothing. */
  canReset: boolean;
}

export default function ResetFooter({ templateName, onChangeTemplate, onReset, canReset }: Props) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [templateConfirmOpen, setTemplateConfirmOpen] = useState(false);
  const addToast = useToastStore((state) => state.addToast);

  return (
    <>
      <div
        className="mt-4 flex items-center justify-between rounded border px-3 py-2"
        style={{ borderColor: ruleDefault }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: ink.ink3 }}>Template</span>
          <span className="text-sm font-medium" style={{ color: ink.ink }}>{templateName}</span>
          <button
            type="button"
            onClick={() => setTemplateConfirmOpen(true)}
            className="text-xs underline"
            style={{ color: accent.accent }}
          >
            Change
          </button>
        </div>
        <button
          type="button"
          onClick={() => setConfirmOpen(true)}
          disabled={!canReset}
          className="text-xs underline disabled:opacity-50"
          style={{ color: canReset ? danger : ink.ink4 }}
          aria-label="Reset section styles"
          title="Reset section styles"
        >
          Reset
        </button>
      </div>

      <ConfirmModal
        open={templateConfirmOpen}
        onClose={() => setTemplateConfirmOpen(false)}
        onConfirm={onChangeTemplate}
        onError={() => addToast("Unable to change the template", "error")}
        title="Change template?"
        description="Switching templates installs the new template's zones and reassigns every section to the first zone. Per-section content (text, entries, order) is preserved."
        confirmLabel="Change template"
        variant="primary"
      />
      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <h2 className="mb-2 text-lg font-semibold" style={{ color: ink.ink }}>
          Reset section styles?
        </h2>
        <p className="text-sm" style={{ color: ink.ink2 }}>
          Every section style override will be removed. The template's
          default font, colors, and spacing will be restored. Your content,
          entries, order, and layout placement are preserved.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={() => setConfirmOpen(false)}
            className="rounded-md border px-4 py-2 text-sm"
            style={{ borderColor: ruleDefault, color: ink.ink2 }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => { setConfirmOpen(false); onReset(); }}
            className="rounded-md px-4 py-2 text-sm text-white"
            style={{ background: danger, borderRadius: radius.r1 }}
          >
            Reset
          </button>
        </div>
      </Modal>
    </>
  );
}
