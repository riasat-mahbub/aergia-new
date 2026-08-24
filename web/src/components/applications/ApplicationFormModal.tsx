import { useEffect, useState } from "react";
import Modal from "../common/Modal";
import { useApplicationStore } from "../../lib/store/applicationStore";
import type {
  Application,
  ApplicationGenerateResponse,
  ApplicationUpdateData,
} from "../../lib/api/applications";

interface ApplicationFormModalProps {
  open: boolean;
  onClose: () => void;
  initialApplication?: Application | null;
  onSaved?: (application: Application) => void;
  onGenerated?: (result: ApplicationGenerateResponse) => void;
}

const EMPTY_FORM = {
  company: "",
  role: "",
  job_description: "",
  job_url: "",
  notes: "",
  next_follow_up_at: "",
};

type FormState = typeof EMPTY_FORM;

function formFromApplication(application: Application | null | undefined): FormState {
  if (!application) return EMPTY_FORM;
  return {
    company: application.company,
    role: application.role,
    job_description: application.job_description,
    job_url: application.job_url ?? "",
    notes: application.notes ?? "",
    next_follow_up_at: application.next_follow_up_at ?? "",
  };
}

function errorDetail(error: unknown): string {
  void error;
  return "Unable to save this application. Please try again.";
}

export default function ApplicationFormModal({
  open,
  onClose,
  initialApplication = null,
  onSaved,
  onGenerated,
}: ApplicationFormModalProps) {
  const create = useApplicationStore((state) => state.create);
  const update = useApplicationStore((state) => state.update);
  const generate = useApplicationStore((state) => state.generate);
  const [form, setForm] = useState<FormState>(() => formFromApplication(initialApplication));
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("");
  const [error, setError] = useState<string | null>(null);
  const editing = Boolean(initialApplication);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset draft when the modal opens
    setForm(formFromApplication(initialApplication));
    setError(null);
    setBusy(false);
    setPhase("");
  }, [open, initialApplication]);

  const setField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const company = form.company.trim();
    const role = form.role.trim();
    const jobDescription = form.job_description.trim();
    if (!company || !role || !jobDescription) {
      setError("Company, Role, and Job description are required.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      if (initialApplication) {
        const changes: ApplicationUpdateData = {
          company,
          role,
          job_description: jobDescription,
          job_url: form.job_url.trim() || null,
          notes: form.notes.trim() || null,
          next_follow_up_at: form.next_follow_up_at || null,
        };
        const saved = await update(initialApplication.id, changes);
        onSaved?.(saved);
        onClose();
        return;
      }

      setPhase("Saving application…");
      const created = await create({
        company,
        role,
        job_description: jobDescription,
        job_url: form.job_url.trim() || undefined,
        notes: form.notes.trim() || undefined,
        ...(form.next_follow_up_at ? { next_follow_up_at: form.next_follow_up_at } : {}),
      });
      onSaved?.(created);
      setPhase("Generating tailored CV…");
      try {
        const result = await generate(created.id);
        onGenerated?.(result);
        onSaved?.(result.application);
      } catch (generationError) {
        setError(errorDetail(generationError));
      }
      onClose();
    } catch (saveError) {
      setError(errorDetail(saveError));
    } finally {
      setBusy(false);
      setPhase("");
    }
  };

  return (
    <Modal open={open} onClose={busy ? () => undefined : onClose} size="wide">
      <form onSubmit={handleSubmit} className="max-h-[85vh] w-full min-w-0 overflow-x-hidden overflow-y-auto">
        <header className="mb-5">
          <h2 className="text-xl font-semibold text-app-ink">
            {editing ? "Edit application" : "Track an application"}
          </h2>
          <p className="mt-1 text-sm text-app-ink-2">
            {editing
              ? "Update the saved job details without rewriting the linked CV."
              : "Save a job description and generate an editable tailored CV."}
          </p>
        </header>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-medium text-app-ink-2">
              Company <span className="text-app-danger">*</span>
              <input
                required
                value={form.company}
                onChange={(event) => setField("company", event.target.value)}
                className="mt-1 w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm font-medium text-app-ink-2">
              Role <span className="text-app-danger">*</span>
              <input
                required
                value={form.role}
                onChange={(event) => setField("role", event.target.value)}
                className="mt-1 w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm"
              />
            </label>
          </div>
          <label className="block text-sm font-medium text-app-ink-2">
            Job description <span className="text-app-danger">*</span>
            <textarea
              required
              value={form.job_description}
              onChange={(event) => setField("job_description", event.target.value)}
              rows={10}
              className="mt-1 w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium text-app-ink-2">
            Job URL <span className="font-normal text-app-ink-3">(optional)</span>
            <input
              type="url"
              value={form.job_url}
              onChange={(event) => setField("job_url", event.target.value)}
              placeholder="https://example.com/jobs/..."
              className="mt-1 w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium text-app-ink-2">
            Notes <span className="font-normal text-app-ink-3">(optional)</span>
            <textarea
              value={form.notes}
              onChange={(event) => setField("notes", event.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium text-app-ink-2">
            Next follow-up <span className="font-normal text-app-ink-3">(optional)</span>
            <input
              type="date"
              value={form.next_follow_up_at}
              onChange={(event) => setField("next_follow_up_at", event.target.value)}
              className="mt-1 w-full rounded-md border border-app-rule-strong px-3 py-2 text-sm"
            />
          </label>
        </div>

        {error && <p className="mt-4 rounded-md bg-app-danger-soft px-3 py-2 text-sm text-app-danger">{error}</p>}
        {phase && <p className="mt-4 text-sm text-app-primary">{phase}</p>}

        <footer className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-md px-4 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-app-primary px-4 py-2 text-sm font-medium text-white hover:bg-app-primary-hover disabled:opacity-50"
          >
            {busy ? phase || "Saving…" : editing ? "Save changes" : "Done"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
