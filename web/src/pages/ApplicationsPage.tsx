import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import ApplicationCard from "../components/applications/ApplicationCard";
import ApplicationFormModal from "../components/applications/ApplicationFormModal";
import EmptyState from "../components/common/EmptyState";
import LoadingSkeleton from "../components/common/LoadingSkeleton";
import {
  APPLICATION_STATUSES,
  type Application,
  type ApplicationGenerateResponse,
  type ApplicationStatus,
} from "../lib/api/applications";
import { RELEVANCE_TOOLTIP, relevanceScore, STATUS_LABELS } from "../components/applications/applicationPresentation";
import { useApplicationStore } from "../lib/store/applicationStore";
import { useToastStore } from "../lib/store/uiStore";

export default function ApplicationsPage() {
  const navigate = useNavigate();
  const applications = useApplicationStore((state) => state.applications);
  const isLoading = useApplicationStore((state) => state.isLoading);
  const fetchAll = useApplicationStore((state) => state.fetchAll);
  const generate = useApplicationStore((state) => state.generate);
  const remove = useApplicationStore((state) => state.remove);
  const addToast = useToastStore((state) => state.addToast);
  const [filter, setFilter] = useState<ApplicationStatus | "all">("all");
  const [formOpen, setFormOpen] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const filteredApplications = useMemo(
    () => filter === "all" ? applications : applications.filter((application) => application.status === filter),
    [applications, filter],
  );

  const handleGenerated = async (result: ApplicationGenerateResponse) => {
    navigate(`/dashboard/applications/${result.application.id}`);
    if (result.application.generation_status === "failed") {
      addToast("CV generation failed. Please retry.", "error");
    }
  };

  const handleRetry = async (application: Application) => {
    setRetryingId(application.id);
    try {
      await handleGenerated(await generate(application.id));
    } catch {
      addToast("Unable to generate this CV", "error");
    } finally {
      setRetryingId(null);
    }
  };

  const handleDelete = async (application: Application) => {
    if (!window.confirm(`Delete the application for ${application.company}?`)) return;
    try {
      await remove(application.id);
      addToast("Application deleted", "info");
    } catch {
      addToast("Unable to delete this application", "error");
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-app-ink">Applications</h1>
          <p className="mt-1 text-sm text-app-ink-2">Track jobs and generate editable, keyword-tailored CVs.</p>
        </div>
        <button type="button" onClick={() => setFormOpen(true)} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-4 py-2 text-sm font-medium text-white hover:bg-app-primary-hover">
          <Plus className="h-4 w-4" />
          Track application
        </button>
      </header>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label htmlFor="application-status-filter" className="shrink-0 text-sm font-medium text-app-ink-2">Status</label>
        <select id="application-status-filter" value={filter} onChange={(event) => setFilter(event.target.value as ApplicationStatus | "all")} className="w-full min-w-[10rem] rounded-md border border-app-rule-strong px-3 py-2 text-sm sm:w-auto">
          <option value="all">All statuses</option>
          {APPLICATION_STATUSES.map((status) => <option key={status} value={status}>{STATUS_LABELS[status]}</option>)}
        </select>
      </div>

      {isLoading && <LoadingSkeleton count={4} />}
      {!isLoading && applications.length === 0 && (
        <EmptyState title="No applications yet" description="Save a job description to generate your first tailored CV." action={{ label: "Track application", onClick: () => setFormOpen(true) }} />
      )}
      {!isLoading && applications.length > 0 && filteredApplications.length === 0 && (
        <div className="rounded-lg border border-dashed border-app-rule-strong bg-app-surface p-10 text-center text-sm text-app-ink-2">No applications match this status.</div>
      )}
      {!isLoading && filteredApplications.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredApplications.map((application) => (
            <ApplicationCard
              key={application.id}
              application={application}
              retrying={retryingId === application.id}
              onRetry={() => handleRetry(application)}
              onDelete={() => handleDelete(application)}
            />
          ))}
        </div>
      )}

      <ApplicationFormModal open={formOpen} onClose={() => setFormOpen(false)} onGenerated={handleGenerated} />
    </div>
  );
}

export { RELEVANCE_TOOLTIP, STATUS_LABELS, relevanceScore };
