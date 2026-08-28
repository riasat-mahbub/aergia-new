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
  };
}

function errorDetail(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = error.response;
    if (typeof response === "object" && response !== null && "data" in response) {
      const data = response.data;
      if (typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string") {
        return data.detail;
      }
    }
  }
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
    <Modal open={open} onClose={busy ? () => undefined : onClose}>
      <form onSubmit={handleSubmit} className="max-h-[85vh] w-[min(720px,90vw)] overflow-y-auto">
        <header className="mb-5">
          <h2 className="text-xl font-semibold text-gray-900">
            {editing ? "Edit application" : "Track an application"}
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            {editing
              ? "Update the saved job details without rewriting the linked CV."
              : "Save a job description and generate an editable tailored CV."}
          </p>
        </header>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm font-medium text-gray-700">
              Company <span className="text-red-600">*</span>
              <input
                required
                value={form.company}
                onChange={(event) => setField("company", event.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Role <span className="text-red-600">*</span>
              <input
                required
                value={form.role}
                onChange={(event) => setField("role", event.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </label>
          </div>
          <label className="block text-sm font-medium text-gray-700">
            Job description <span className="text-red-600">*</span>
            <textarea
              required
              value={form.job_description}
              onChange={(event) => setField("job_description", event.target.value)}
              rows={10}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Job URL <span className="font-normal text-gray-400">(optional)</span>
            <input
              type="url"
              value={form.job_url}
              onChange={(event) => setField("job_url", event.target.value)}
              placeholder="https://example.com/jobs/..."
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Notes <span className="font-normal text-gray-400">(optional)</span>
            <textarea
              value={form.notes}
              onChange={(event) => setField("notes", event.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
        </div>

        {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {phase && <p className="mt-4 text-sm text-blue-700">{phase}</p>}

        <footer className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? phase || "Saving…" : editing ? "Save changes" : "Done"}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
