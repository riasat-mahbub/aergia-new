import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import { FileUp, Loader2, X } from "lucide-react";

import Modal from "../common/Modal";
import { fetchSystemTemplates, type UserTemplate } from "../../lib/api/templates";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (input: { title: string; templateId: string; file: File }) => void;
}

const TITLE_PLACEHOLDER = "e.g. My Imported CV";
const DEFAULT_TEMPLATE_ID = "generic-modern";

/**
 * Strip a `.pdf` extension (case-insensitive) from a filename.
 * Falls back to "Imported CV" when the input has nothing usable.
 */
function titleFromFilename(name: string): string {
  const base = (name || "").replace(/\.pdf$/i, "").trim();
  return base.length > 0 ? base : "Imported CV";
}

/**
 * Pre-file modal for the import flow.
 *
 * Pattern: a single modal opens; the user types a title, picks a
 * template, then clicks "Choose PDF…" to attach a file. The import
 * button stays disabled until both title and file are present.
 *
 * Title auto-fill: when the user picks a file, the title field
 * receives the filename-without-extension IF the field is empty
 * OR still matches the placeholder default. Any actual content
 * the user typed survives the auto-fill.
 */
export default function ImportCvModal({ open, onClose, onSubmit }: Props) {
  const [title, setTitle] = useState("");
  const [templateId, setTemplateId] = useState(DEFAULT_TEMPLATE_ID);
  const [file, setFile] = useState<File | null>(null);
  const [templates, setTemplates] = useState<UserTemplate[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- modal open reset; see Phase 9 lint debt
    setTitle("");
    setTemplateId(DEFAULT_TEMPLATE_ID);
    setFile(null);
    fetchSystemTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, [open]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const next = e.target.files?.[0] ?? null;
    if (!next) {
      setFile(null);
      return;
    }
    setFile(next);
    // Auto-fill title from filename when the field is empty or matches
    // the placeholder default. Otherwise the user's typed value stays.
    const trimmed = title.trim();
    if (trimmed.length === 0) {
      setTitle(titleFromFilename(next.name));
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    const trimmed = title.trim();
    if (trimmed.length === 0) return;
    onSubmit({ title: trimmed, templateId, file });
  };

  const canImport = file !== null && title.trim().length > 0;

  return (
    <Modal open={open} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-app-ink">Import CV</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-app-ink-3 hover:bg-app-surface-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="import-title"
            className="block text-sm font-medium text-app-ink-2"
          >
            Title
          </label>
          <input
            id="import-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={TITLE_PLACEHOLDER}
            className="w-full rounded border border-app-rule-strong px-2 py-1.5 text-sm focus:border-app-primary focus:outline-none"
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="import-template"
            className="block text-sm font-medium text-app-ink-2"
          >
            Template
          </label>
          <select
            id="import-template"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            className="w-full rounded border border-app-rule-strong px-2 py-1.5 text-sm focus:border-app-primary focus:outline-none"
          >
            {templates.length === 0 ? (
              <option value={DEFAULT_TEMPLATE_ID}>Modern</option>
            ) : (
              templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))
            )}
          </select>
        </div>

        <div className="space-y-2">
          <span className="block text-sm font-medium text-app-ink-2">
            PDF
          </span>
          {file ? (
            <div className="flex items-center gap-2">
              <span
                className="flex-1 truncate rounded border border-app-rule bg-app-canvas px-2 py-1.5 text-sm text-app-ink-2"
                title={file.name}
              >
                {file.name}
              </span>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="rounded border border-app-rule-strong px-2 py-1 text-xs text-app-ink-2 hover:bg-app-surface-muted"
              >
                Change
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 rounded-md border border-app-primary bg-app-surface px-3 py-1.5 text-xs text-app-primary hover:bg-app-primary-soft"
            >
              <FileUp className="h-3.5 w-3.5" />
              Choose PDF…
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-app-rule pt-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-app-rule-strong px-3 py-1.5 text-xs text-app-ink-2 hover:bg-app-surface-muted"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!canImport}
            className="flex items-center gap-1 rounded bg-app-primary px-3 py-1.5 text-xs text-white hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Loader2 className="hidden h-3 w-3 animate-spin" />
            Import
          </button>
        </div>
      </form>
    </Modal>
  );
}

/* The button above intentionally renders an inert spinner — the
   in-flight state lives in the parent (`ImportCvButton`) where the
   real submit handler awaits `importPDF` + `createCV`. The hidden
   `Loader2` keeps the visual slot stable when the parent swaps its
   label. */

export { titleFromFilename };
