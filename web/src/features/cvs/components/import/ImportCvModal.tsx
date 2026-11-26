import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react";
import { FileUp, Loader2, X } from "lucide-react";

import Modal from "@/shared/ui/Modal";
import { fetchSystemTemplates } from "@/features/templates";
import type { UserTemplate } from "@/features/templates";

interface Props {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (input: { title: string; templateId: string; file: File }) => void;
}

const TITLE_PLACEHOLDER = "e.g. My Imported CV";
const DEFAULT_TEMPLATE_ID = "generic-minimal";

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
export default function ImportCvModal({ open, busy, onClose, onSubmit }: Props) {
  const titleId = useId();
  const [title, setTitle] = useState("");
  const [templateId, setTemplateId] = useState(DEFAULT_TEMPLATE_ID);
  const [file, setFile] = useState<File | null>(null);
  const [templates, setTemplates] = useState<UserTemplate[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const submitButtonRef = useRef<HTMLButtonElement>(null);

  useLayoutEffect(() => {
    if (!busy) return;

    const activeElement = document.activeElement;
    if (activeElement !== submitButtonRef.current) {
      submitButtonRef.current?.focus();
    }
  }, [busy]);

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
    if (busy) return;
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
    if (busy || !file) return;
    const trimmed = title.trim();
    if (trimmed.length === 0) return;
    onSubmit({ title: trimmed, templateId, file });
  };

  const canImport = file !== null && title.trim().length > 0;

  return (
    <Modal open={open} onClose={onClose} titleId={titleId}>
      <form onSubmit={handleSubmit} aria-busy={busy} className="space-y-4">
        <div className="flex items-start justify-between">
          <h2 id={titleId} className="text-lg font-semibold text-app-ink">Import CV</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            aria-label="Close"
            className="rounded p-1 text-app-ink-3 hover:bg-app-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
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
            onChange={(e) => {
              if (!busy) setTitle(e.target.value);
            }}
            disabled={busy}
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
            onChange={(e) => {
              if (!busy) setTemplateId(e.target.value);
            }}
            disabled={busy}
            className="w-full rounded border border-app-rule-strong px-2 py-1.5 text-sm focus:border-app-primary focus:outline-none"
          >
            {templates.length === 0 ? (
              <option value={DEFAULT_TEMPLATE_ID}>Minimal</option>
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
                disabled={busy}
                className="rounded border border-app-rule-strong px-2 py-1 text-xs text-app-ink-2 hover:bg-app-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
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
            disabled={busy}
            className="hidden"
          />
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-app-rule pt-3">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded border border-app-rule-strong px-3 py-1.5 text-xs text-app-ink-2 hover:bg-app-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            ref={submitButtonRef}
            type="submit"
            disabled={!canImport && !busy}
            aria-disabled={busy}
            aria-busy={busy}
            onClick={(e) => {
              if (busy) e.preventDefault();
            }}
            className="flex items-center gap-1 rounded bg-app-primary px-3 py-1.5 text-xs text-white hover:bg-app-primary-hover disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-wait aria-disabled:opacity-75"
          >
            {busy && <Loader2 aria-hidden="true" className="h-3 w-3 motion-safe:animate-spin" />}
            {busy ? "Importing…" : "Import"}
          </button>
        </div>
      </form>
      <p role="status" className="sr-only">{busy ? "Importing CV…" : ""}</p>
    </Modal>
  );
}

export { titleFromFilename };
