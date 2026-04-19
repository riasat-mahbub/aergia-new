import { useState, useEffect } from "react";
import Modal from "../common/Modal";
import useUserTemplateStore from "../../lib/store/userTemplateStore";
import { fetchSystemTemplates, UserTemplate } from "../../lib/api/templates";
import type { LayoutConfig } from "../../lib/sections/types";

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
  const [zoneInput, setZoneInput] = useState("");
  const [placementInput, setPlacementInput] = useState(
    JSON.stringify({
      profile: "sidebar",
      experience: "main",
      education: "main",
      skills: "main",
      projects: "main",
      languages: "main",
      certifications: "main",
    }, null, 2)
  );
  const [showZoneForm, setShowZoneForm] = useState(false);
  const { templates: userTemplates, fetchUserTemplates, uploadTemplate, deleteTemplate } = useUserTemplateStore();

  useEffect(() => {
    if (open) {
      fetchSystemTemplates().then(setSystemTemplates).catch(() => {});
      fetchUserTemplates();
      setZoneInput(JSON.stringify([
        { id: "sidebar", styles: { width: "30%", backgroundColor: "#f8fafc", padding: "24px" } },
        { id: "main", styles: { padding: "24px" } },
      ], null, 2));
      setShowZoneForm(false);
      setUploadError(null);
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

      let layoutConfig: LayoutConfig | undefined;
      if (showZoneForm && zoneInput && placementInput) {
        try {
          layoutConfig = {
            zones: JSON.parse(zoneInput),
            placement: JSON.parse(placementInput),
          };
        } catch {
          setUploadError("Invalid JSON in zone or placement configuration. Please check the format.");
          setIsUploading(false);
          return;
        }
      }

      await uploadTemplate(name, content, layoutConfig as Record<string, unknown> | undefined);
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

          <div className="mt-2 text-center">
            <button
              type="button"
              onClick={() => setShowZoneForm(!showZoneForm)}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              {showZoneForm ? "Hide zone configuration" : "Configure zones for new template"}
            </button>
          </div>

          {showZoneForm && (
            <div className="mt-3 space-y-3 rounded-lg border border-gray-200 p-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Zones (JSON)</label>
                <p className="mb-1 text-[10px] text-gray-400">Define zones with their styles. Each zone gets a {"{{"}zone_id{"}}"} placeholder in your HTML.</p>
                <textarea
                  value={zoneInput}
                  onChange={(e) => setZoneInput(e.target.value)}
                  rows={5}
                  className="w-full rounded border px-2 py-1 font-mono text-xs"
                  placeholder='[{"id": "sidebar", "styles": {"width": "30%", "padding": "24px"}}, {"id": "main", "styles": {"padding": "24px"}}]'
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Section Placement (JSON)</label>
                <p className="mb-1 text-[10px] text-gray-400">Map each section type to a zone ID.</p>
                <textarea
                  value={placementInput}
                  onChange={(e) => setPlacementInput(e.target.value)}
                  rows={7}
                  className="w-full rounded border px-2 py-1 font-mono text-xs"
                  placeholder='{"profile": "sidebar", "experience": "main", ...}'
                />
              </div>
            </div>
          )}

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
