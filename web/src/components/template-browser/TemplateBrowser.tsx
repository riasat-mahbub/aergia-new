import { useState, useEffect } from "react";
import { motion } from "motion/react";
import Modal from "../common/Modal";
import client from "../../lib/api/client";

interface TemplateInfo {
  id: string;
  name: string;
  description: string | null;
  preview_image_url: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  currentTemplateId: string;
  onSelect: (templateId: string) => void;
}

const LAYOUT_HINTS: Record<string, string> = {
  "generic-modern": "2-column · sidebar + main",
  "generic-classic": "1-column · serif · dividers",
  "generic-minimal": "1-column · clean · no decoration",
};

export default function TemplateBrowser({ open, onClose, currentTemplateId, onSelect }: Props) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);

  useEffect(() => {
    if (open) {
      client.get("/templates").then(({ data }) => setTemplates(data)).catch(() => {});
    }
  }, [open]);

  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Choose a Template</h2>
      <div className="space-y-3">
        {templates.map((t, i) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <button
              onClick={() => onSelect(t.id)}
              disabled={t.id === currentTemplateId}
              className={`w-full rounded-lg border p-4 text-left transition-colors ${
                t.id === currentTemplateId
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              } disabled:cursor-default`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{t.name}</p>
                  {t.description && <p className="mt-0.5 text-sm text-gray-500">{t.description}</p>}
                  <p className="mt-1 text-xs text-gray-400">{LAYOUT_HINTS[t.id] || ""}</p>
                </div>
                {t.id === currentTemplateId && (
                  <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                    Active
                  </span>
                )}
              </div>
            </button>
          </motion.div>
        ))}
      </div>
      <div className="mt-6 flex justify-end">
        <button
          onClick={onClose}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          Close
        </button>
      </div>
    </Modal>
  );
}
