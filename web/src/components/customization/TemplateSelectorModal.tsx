import { useState, useEffect } from "react";
import Modal from "../common/Modal";
import useUserTemplateStore from "../../lib/store/userTemplateStore";
import { fetchSystemTemplates } from "../../lib/api/templates";
import type { UserTemplate } from "../../lib/api/templates";

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
  const { templates: userTemplates, fetchUserTemplates, uploadTemplate, deleteTemplate } = useUserTemplateStore();

  useEffect(() => {
    if (open) {
      fetchSystemTemplates().then(setSystemTemplates).catch(() => {});
      fetchUserTemplates();
    }
  }, [open, fetchUserTemplates]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const content = await file.text();
      const name = file.name.replace(/\.html?$/i, "");
      await uploadTemplate(name, content);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Failed to upload template");
    } finally {
      setIsUploading(false);
      if (event.target) {
        event.target.value = "";
      }
    }
  };

  const handleDelete = async (templateId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (window.confirm("Are you sure you want to delete this template?")) {
      await deleteTemplate(templateId);
    }
  };

  const allTemplates = [...systemTemplates, ...userTemplates];

  return (
    <Modal open={open} onClose={onClose}>
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Select Template</h2>

      <div className="space-y-4">
        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">System Templates</h3>
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

        <div>
          <h3 className="mb-2 text-sm font-semibold text-gray-700">Your Templates</h3>
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
                      🗑️
                    </button>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="pt-2">
          <label className="block">
            <div className="cursor-pointer rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-4 text-center transition-colors hover:bg-gray-100">
              <div className="text-sm font-medium text-gray-700">Add New Template</div>
              <div className="mt-1 text-xs text-gray-500">Upload an HTML file</div>
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