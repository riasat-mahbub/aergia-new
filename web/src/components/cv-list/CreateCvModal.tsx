import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "../common/Modal";
import { useCVStore } from "../../lib/store/cvStore";
import { fetchSystemTemplates } from "../../lib/api/templates";

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
  const [templateId, setTemplateId] = useState("generic-minimal");
  const [systemTemplates, setSystemTemplates] = useState<TemplateOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- modal open reset; see Phase 9 lint debt
      setTitle("");
      setTemplateId("generic-minimal");
      fetchSystemTemplates().then(setSystemTemplates).catch(() => {});
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
      <h2 className="mb-4 text-lg font-semibold text-app-ink">Create New CV</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-app-ink-2">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Software Engineer CV"
            className="mt-1 w-full rounded-md border-app-rule-strong shadow-sm focus:border-app-primary focus:ring-app-primary sm:text-sm"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-app-ink-2">Template</label>
          <div className="mt-2 grid grid-cols-1 gap-2">
            {systemTemplates.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-app-ink-3 uppercase tracking-wide">System Templates</p>
                {systemTemplates.map((t) => (
                  <label
                    key={t.id}
                    className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                      templateId === t.id
                        ? "border-app-primary bg-app-primary-soft"
                        : "border-app-rule hover:border-app-rule-strong"
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
                    <div className={`h-4 w-4 rounded-full border-2 ${templateId === t.id ? "border-app-primary" : "border-app-rule-strong"}`}>
                      {templateId === t.id && <div className="m-0.5 h-2.5 w-2.5 rounded-full bg-app-primary" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-app-ink">{t.name}</p>
                      {t.description && <p className="text-xs text-app-ink-3">{t.description}</p>}
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="rounded-md border border-app-rule-strong px-4 py-2 text-sm text-app-ink-2 hover:bg-app-surface-muted"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!title.trim() || loading}
            className="rounded-md bg-app-primary px-4 py-2 text-sm text-white hover:bg-app-primary-hover disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
