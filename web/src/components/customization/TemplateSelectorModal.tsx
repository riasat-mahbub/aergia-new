import { useState, useEffect } from "react";
import Modal from "../common/Modal";
import useUserTemplateStore from "../../lib/store/userTemplateStore";
import { fetchSystemTemplates, UserTemplate } from "../../lib/api/templates";
import { useToastStore } from "../../lib/store/uiStore";

interface Props {
  open: boolean;
  onClose: () => void;
  templateId: string;
  onSelect: (templateId: string) => void;
}

export default function TemplateSelectorModal({ open, onClose, templateId, onSelect }: Props) {
  const [systemTemplates, setSystemTemplates] = useState<UserTemplate[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const addToast = useToastStore((s) => s.addToast);
  const { templates: userTemplates, fetchUserTemplates, uploadTemplate, deleteTemplate } = useUserTemplateStore();

  useEffect(() => {
    if (open) {
      fetchSystemTemplates().then(setSystemTemplates).catch(() => {});
      fetchUserTemplates();
      setUploadError(null);
    }
  }, [open, fetchUserTemplates]);

  const performUpload = async (name: string, content: string) => {
    setIsUploading(true);
    setUploadError(null);

    try {
      await uploadTemplate(name, content);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Failed to upload template");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const content = await file.text();
      const name = file.name.replace(/\.html?$/i, "");
      await performUpload(name, content);
    } finally {
      if (event.target) {
        event.target.value = "";
      }
    }
  };

  const handleDelete = async (templateId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setPendingDeleteId(templateId);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!pendingDeleteId) return;
    await deleteTemplate(pendingDeleteId);
    setDeleteConfirmOpen(false);
    setPendingDeleteId(null);
    addToast("Template deleted", "success");
  };

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
          </div>
        </div>

        <div className="border-t border-gray-200 pt-2">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">Your Templates</h3>
          <div className="space-y-2">
            {userTemplates.map((t) => (
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
                    <p className="text-xs text-gray-400">User template</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {t.id === templateId && <div className="h-4 w-4 rounded-full bg-blue-500" />}
                    <button
                      onClick={(e) => handleDelete(t.id, e)}
                      className="rounded p-1 text-gray-400 hover:text-red-600"
                      title="Delete template"
                    >
                      {t.id === templateId ? "✕" : "🗑️"}
                    </button>
                  </div>
                </div>
              </button>
            ))}
            {!userTemplates.length && (
              <p className="text-xs text-gray-400 italic">No user templates yet</p>
            )}
          </div>
        </div>

        <div className="border-t border-gray-200 pt-2">
          <label className="block">
            <div className="cursor-pointer rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-4 text-center transition-colors hover:bg-gray-100">
              <div className="text-sm font-medium text-gray-700">Add New Template</div>
              <input
                type="file"
                accept=".html,.htm"
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
                id="template-upload"
              />
              <label htmlFor="template-upload" className="cursor-pointer">
                {isUploading ? "Uploading..." : "Choose file"}
              </label>
            </div>
          </label>

          {uploadError && <p className="mt-2 text-xs text-red-600">{uploadError}</p>}
        </div>

        {deleteConfirmOpen && pendingDeleteId && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-800">
              Are you sure you want to delete this template? This action cannot be undone.
            </p>
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={() => { setDeleteConfirmOpen(false); setPendingDeleteId(null); }}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        )}

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
