import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "../common/Modal";
import { useCVStore } from "../../lib/store/cvStore";
import client from "../../lib/api/client";

interface TemplateOption {
  id: string;
  name: string;
  description: string | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function CreateCvModal({ open, onClose }: Props) {
  const navigate = useNavigate();
  const { createCV } = useCVStore();
  const [title, setTitle] = useState("");
  const [templateId, setTemplateId] = useState("generic-modern");
  const [templates, setTemplates] = useState<TemplateOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setTitle("");
      setTemplateId("generic-modern");
      client.get("/templates").then(({ data }) => setTemplates(data)).catch(() => {});
    }
  }, [open]);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setLoading(true);
    try {
      const cv = await createCV(title.trim(), templateId);
      onClose();
      navigate(`/dashboard/builder/${cv.id}`);
    } catch {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Create New CV</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Software Engineer CV"
            className="mt-1 w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Template</label>
          <div className="mt-2 grid grid-cols-1 gap-2">
            {templates.map((t) => (
              <label
                key={t.id}
                className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                  templateId === t.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <input
                  type="radio"
                  name="template"
                  value={t.id}
                  checked={templateId === t.id}
                  onChange={() => setTemplateId(t.id)}
                  className="sr-only"
                />
                <div className={`h-4 w-4 rounded-full border-2 ${templateId === t.id ? "border-blue-500" : "border-gray-300"}`}>
                  {templateId === t.id && <div className="m-0.5 h-2.5 w-2.5 rounded-full bg-blue-500" />}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{t.name}</p>
                  {t.description && <p className="text-xs text-gray-500">{t.description}</p>}
                </div>
              </label>
            ))}
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!title.trim() || loading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
