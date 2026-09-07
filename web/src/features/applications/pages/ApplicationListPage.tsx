import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import ApplicationCard from "../components/ApplicationCard";
import ApplicationFormModal from "../components/ApplicationFormModal";
import EmptyState from "@/shared/ui/EmptyState";
import LoadingSkeleton from "@/shared/ui/LoadingSkeleton";
import ConfirmModal from "@/shared/ui/ConfirmModal";
import {
  APPLICATION_STATUSES,
  type Application,
  type ApplicationGenerateResponse,
  type ApplicationStatus,
} from "@/features/applications/types";
import { applicationMatchesSearch, RELEVANCE_TOOLTIP, relevanceScore } from "../domain/list/applicationPresentation";
import { STATUS_LABELS } from "../domain/applicationStatus";
import { useApplicationStore } from "@/features/applications/state/applicationStore";
import { useToastStore } from "@/shared/state/uiStore";

export default function ApplicationsPage() {
  const navigate = useNavigate();
  const applications = useApplicationStore((state) => state.applications);
  const isLoading = useApplicationStore((state) => state.isLoading);
  const error = useApplicationStore((state) => state.error);
  const fetchAll = useApplicationStore((state) => state.fetchAll);
  const generate = useApplicationStore((state) => state.generate);
  const remove = useApplicationStore((state) => state.remove);
  const addToast = useToastStore((state) => state.addToast);
  const [filter, setFilter] = useState<ApplicationStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Application | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const filteredApplications = useMemo(
    () => applications.filter((application) => {
      const statusMatches = filter === "all" || application.status === filter;
      return statusMatches && applicationMatchesSearch(application, search);
    }),
    [applications, filter, search],
  );

  const handleGenerated = async (result: ApplicationGenerateResponse) => {
    navigate({ to: "/applications/$id", params: { id: result.application.id } });
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
    await remove(application.id);
    addToast("Application deleted", "info");
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

      <div className="mb-6 space-y-2">
        <label htmlFor="application-search" className="sr-only">Search applications</label>
        <input
          id="application-search"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search company, role, or try status:interview relevance:>=70 followup:overdue"
          className="w-full rounded-md border border-app-rule-strong bg-app-surface px-3 py-2 text-sm"
        />
        <p className="text-xs text-app-ink-3">Filters: <code>company:</code>, <code>status:</code>, <code>after:</code>, <code>before:</code>, <code>relevance:&gt;=70</code>, <code>followup:overdue</code>.</p>
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="application-status-filter" className="shrink-0 text-sm font-medium text-app-ink-2">Status</label>
        <select id="application-status-filter" value={filter} onChange={(event) => setFilter(event.target.value as ApplicationStatus | "all")} className="w-full min-w-[10rem] rounded-md border border-app-rule-strong px-3 py-2 text-sm sm:w-auto">
          <option value="all">All statuses</option>
          {APPLICATION_STATUSES.map((status) => <option key={status} value={status}>{STATUS_LABELS[status]}</option>)}
        </select>
        </div>
      </div>

      {isLoading && <LoadingSkeleton count={4} />}
      {error && !isLoading && (
        <div className="rounded-lg border border-app-danger/30 bg-app-danger-soft p-5 text-sm text-app-danger" role="alert">
          <p>{error}</p>
          <button type="button" onClick={fetchAll} className="mt-3 rounded-md border border-app-danger/40 px-3 py-1.5 font-medium hover:bg-app-danger/10">
            Try again
          </button>
        </div>
      )}
      {!error && !isLoading && applications.length === 0 && (
        <EmptyState title="No applications yet" description="Save a job description to generate your first tailored CV." action={{ label: "Track application", onClick: () => setFormOpen(true) }} />
      )}
      {!isLoading && applications.length > 0 && filteredApplications.length === 0 && (
        <div className="rounded-lg border border-dashed border-app-rule-strong bg-app-surface p-10 text-center text-sm text-app-ink-2">No applications match these filters.</div>
      )}
      {!isLoading && filteredApplications.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredApplications.map((application) => (
            <ApplicationCard
              key={application.id}
              application={application}
              retrying={retryingId === application.id}
              onRetry={() => handleRetry(application)}
              onDelete={() => setDeleteTarget(application)}
            />
          ))}
        </div>
      )}

      <ConfirmModal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget ? handleDelete(deleteTarget) : undefined}
        onError={() => addToast("Unable to delete this application", "error")}
        title="Delete application?"
        description={deleteTarget ? (
          <>
            Delete the application for <span className="font-medium text-app-ink">{deleteTarget.company}</span>? This action cannot be undone.
          </>
        ) : null}
        confirmLabel="Delete application"
      />
      <ApplicationFormModal open={formOpen} onClose={() => setFormOpen(false)} onGenerated={handleGenerated} />
    </div>
  );
}

export { RELEVANCE_TOOLTIP, STATUS_LABELS, relevanceScore };
