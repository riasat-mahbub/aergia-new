import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ExternalLink, Plus, RefreshCw, Trash2 } from "lucide-react";
import ApplicationFormModal from "../components/applications/ApplicationFormModal";
import EmptyState from "../components/common/EmptyState";
import LoadingSkeleton from "../components/common/LoadingSkeleton";
import {
  APPLICATION_STATUSES,
  type Application,
  type ApplicationGenerateResponse,
  type ApplicationStatus,
} from "../lib/api/applications";
import { useApplicationStore } from "../lib/store/applicationStore";
import { useToastStore } from "../lib/store/uiStore";

const RELEVANCE_TOOLTIP = "Weighted keyword coverage of this CV against the saved job description—not an ATS or hiring probability.";

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  draft: "Draft",
  applied: "Applied",
  responded: "Responded",
  interview: "Interview",
  offer: "Offer",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const STATUS_CLASSES: Record<ApplicationStatus, string> = {
  draft: "bg-app-surface-muted text-app-ink-2",
  applied: "bg-app-primary-soft text-app-primary",
  responded: "bg-app-secondary-soft text-app-secondary",
  interview: "bg-app-secondary-soft text-app-secondary",
  offer: "bg-app-warning-soft text-app-warning",
  hired: "bg-app-primary-soft text-app-primary",
  rejected: "bg-app-danger-soft text-app-danger",
  withdrawn: "bg-app-surface-muted text-app-ink-3",
};

function relevanceScore(relevance: Application["relevance"]): number | null {
  if ("score" in relevance && typeof relevance.score === "number") return relevance.score;
  return null;
}

function formatDate(value: string | null): string {
  if (!value) return "Not applied";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

interface ApplicationCardProps {
  application: Application;
  retrying: boolean;
  onRetry: () => void;
  onDelete: () => void;
}

function ApplicationCard({ application, retrying, onRetry, onDelete }: ApplicationCardProps) {
  const score = relevanceScore(application.relevance);
  const fitLabel = application.fits_one_page === true
    ? "One-page fit"
    : application.fits_one_page === false
      ? "Could not fit one page without rewriting content"
      : null;

  return (
    <article className="rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link to={`/dashboard/applications/${application.id}`} className="block truncate text-lg font-semibold text-app-ink hover:text-app-primary">
            {application.company}
          </Link>
          <p className="mt-1 truncate text-sm text-app-ink-2">{application.role}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[application.status]}`}>
          {STATUS_LABELS[application.status]}
        </span>
      </div>

      <div className="mt-4 grid gap-2 text-sm text-app-ink-2 sm:grid-cols-2">
        <span>Updated {formatDate(application.updated_at)}</span>
        <span>{formatDate(application.applied_at)}</span>
        {score !== null && <span className="font-medium text-app-ink" title={RELEVANCE_TOOLTIP}>Relevance {score}%</span>}
        {fitLabel && <span className={application.fits_one_page ? "text-app-primary" : "text-app-warning"}>{fitLabel}</span>}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-app-rule-soft pt-4">
        {application.generation_status === "ready" && application.cv_id ? (
          <Link
            to={`/dashboard/builder/${application.cv_id}?application=${application.id}`}
          >
            Open linked CV
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        ) : (
          <button
            type="button"
            onClick={onRetry}
            disabled={retrying}
            className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-1.5 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} />
            {retrying ? "Generating…" : application.generation_status === "failed" ? "Retry" : "Generate CV"}
          </button>
        )}
        <Link to={`/dashboard/applications/${application.id}`} className="rounded-md px-3 py-1.5 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted">
          Details
        </Link>
        <button type="button" onClick={onDelete} className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-sm text-app-ink-3 hover:bg-app-danger-soft hover:text-app-danger">
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </button>
      </div>
      {application.generation_error && <p className="mt-3 text-xs text-app-danger">CV generation failed. Please retry.</p>}
    </article>
  );
}

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
    if (result.application.generation_status === "ready" && result.cv_id) {
      navigate(`/dashboard/builder/${result.cv_id}?application=${result.application.id}`);
    } else if (result.application.generation_status === "failed") {
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
            <ApplicationCard key={application.id} application={application} retrying={retryingId === application.id} onRetry={() => handleRetry(application)} onDelete={() => handleDelete(application)} />
          ))}
        </div>
      )}

      <ApplicationFormModal open={formOpen} onClose={() => setFormOpen(false)} onGenerated={handleGenerated} />
    </div>
  );
}

export { STATUS_LABELS, relevanceScore };
