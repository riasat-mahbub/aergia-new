import { useState, useEffect } from "react";
import Modal from "../common/Modal";
import { fetchSystemTemplates, UserTemplate } from "../../lib/api/templates";

interface Props {
  open: boolean;
  onClose: () => void;
  templateId: string;
  onSelect: (templateId: string) => void;
}

export default function TemplateSelectorModal({ open, onClose, templateId, onSelect }: Props) {
  const [systemTemplates, setSystemTemplates] = useState<UserTemplate[]>([]);

  useEffect(() => {
    if (open) {
      fetchSystemTemplates().then(setSystemTemplates).catch(() => {});
    }
  }, [open]);

  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Select Template</h2>

      <div className="space-y-6">
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">System Templates</h3>
          <div className="space-y-2">
            {systemTemplates.map((t) => (
              <button
                key={t.id}
                onClick={() => onSelect(t.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  t.id === templateId
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{t.name}</p>
                    {t.description && <p className="text-xs text-gray-500">{t.description}</p>}
                  </div>
                  {t.id === templateId && <div className="h-4 w-4 rounded-full bg-blue-500" />}
                </div>
              </button>
            ))}
            {!systemTemplates.length && (
              <p className="text-xs text-gray-400 italic">Loading…</p>
            )}
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </Modal>
  );
}
