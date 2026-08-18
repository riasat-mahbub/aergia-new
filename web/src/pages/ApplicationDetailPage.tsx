import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Download, ExternalLink, Pencil, RefreshCw, Trash2 } from "lucide-react";
import ApplicationFormModal from "../components/applications/ApplicationFormModal";
import LoadingSkeleton from "../components/common/LoadingSkeleton";
import { exportPDF, downloadPDF, fetchCV, type CVDetail } from "../lib/api/cvs";
import {
  APPLICATION_STATUSES,
  type Application,
  type ApplicationStatus,
  type RelevanceResult,
} from "../lib/api/applications";
import { useApplicationStore } from "../lib/store/applicationStore";
import { useToastStore } from "../lib/store/uiStore";
import { safeExternalUrl } from "../lib/security/safeUrl";
import {
  RELEVANCE_TOOLTIP,
  STATUS_CLASSES,
  STATUS_LABELS,
} from "../components/applications/applicationPresentation";


function isRelevanceResult(value: Application["relevance"]): value is RelevanceResult {
  return "score" in value && typeof value.score === "number";
}

function sectionTypes(cv: CVDetail | null): string[] {
  if (!cv || !Array.isArray(cv.sections)) return [];
  return cv.sections.flatMap((section) => {
    if (typeof section !== "object" || section === null || !("type" in section)) return [];
    return typeof section.type === "string" ? [section.type] : [];
  });
}

function selectedSourceCount(cv: CVDetail | null): number | null {
  if (!cv || typeof cv.extra_metadata !== "object" || cv.extra_metadata === null) return null;
  if (!("selected_sources" in cv.extra_metadata)) return null;
  const sources = cv.extra_metadata.selected_sources;
  return Array.isArray(sources) ? sources.length : null;
}

export default function ApplicationDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const application = useApplicationStore((state) => state.currentApplication);
  const isLoading = useApplicationStore((state) => state.isLoading);
  const fetch = useApplicationStore((state) => state.fetch);
  const update = useApplicationStore((state) => state.update);
  const generate = useApplicationStore((state) => state.generate);
  const remove = useApplicationStore((state) => state.remove);
  const addToast = useToastStore((state) => state.addToast);
  const [editOpen, setEditOpen] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [statusSaving, setStatusSaving] = useState(false);
  const [linkedCV, setLinkedCV] = useState<CVDetail | null>(null);

  useEffect(() => {
    if (id) fetch(id);
  }, [fetch, id]);

  useEffect(() => {
    if (!application?.cv_id) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear stale linked CV when application changes
      setLinkedCV(null);
      return;
    }
    let cancelled = false;
    fetchCV(application.cv_id).then((cv) => {
      if (!cancelled) setLinkedCV(cv);
    }).catch(() => {
      if (!cancelled) setLinkedCV(null);
    });
    return () => { cancelled = true; };
  }, [application?.cv_id]);

  const relevance = application && isRelevanceResult(application.relevance) ? application.relevance : null;
  const sections = useMemo(() => sectionTypes(linkedCV), [linkedCV]);
  const sourceCount = selectedSourceCount(linkedCV);

  if (isLoading || !application || application.id !== id) {
    return <div className="mx-auto max-w-4xl px-4 py-8">{isLoading ? <LoadingSkeleton count={2} /> : <p className="text-sm text-app-ink-2">Application not found.</p>}</div>;
  }

  const safeJobUrl = safeExternalUrl(application.job_url);

  const handleStatusChange = async (status: ApplicationStatus) => {
    setStatusSaving(true);
    try {
      await update(application.id, { status });
    } catch {
      addToast("Unable to update application status", "error");
    } finally {
      setStatusSaving(false);
    }
  };

  const handleRetry = async () => {
    setRetrying(true);
    try {
      const result = await generate(application.id);
      if (result.application.generation_status === "ready" && result.cv_id) {
        navigate(`/dashboard/builder/${result.cv_id}?application=${application.id}`);
      } else {
        addToast("CV generation failed. Please retry.", "error");
      }
    } catch {
      addToast("Unable to generate this CV", "error");
    } finally {
      setRetrying(false);
    }
  };

  const handleExport = async () => {
    if (!application.cv_id) return;
    try {
      const blob = await exportPDF(application.cv_id);
      downloadPDF(blob, `${application.company}-${application.role}.pdf`);
    } catch {
      addToast("Unable to export this CV", "error");
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete the application for ${application.company}?`)) return;
    try {
      await remove(application.id);
      addToast("Application deleted", "info");
      navigate("/dashboard/applications");
    } catch {
      addToast("Unable to delete this application", "error");
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Link to="/dashboard/applications" className="text-sm text-app-ink-3 hover:text-app-ink-2">&larr; Applications</Link>
      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-app-primary">Application</p>
          <h1 className="text-2xl font-bold text-app-ink">{application.company}</h1>
          <p className="mt-1 text-lg text-app-ink-2">{application.role}</p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
          <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[application.status]}`}>
            {STATUS_LABELS[application.status]}
          </span>
          <label className="sr-only" htmlFor="application-status">Change status</label>
          <select
            id="application-status"
            aria-label="Application status"
            value={application.status}
            disabled={statusSaving}
            onChange={(event) => handleStatusChange(event.target.value as ApplicationStatus)}
            className="w-full min-w-[10rem] rounded-md border border-app-rule-strong bg-app-surface px-3 py-2 text-sm sm:w-auto"
          >
            {APPLICATION_STATUSES.map((status) => <option key={status} value={status}>{STATUS_LABELS[status]}</option>)}
          </select>
        </div>
      </header>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <section className="rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Job</h2>
          <div className="mt-4 whitespace-pre-wrap text-sm leading-6 text-app-ink-2">{application.job_description}</div>
          {safeJobUrl && <a href={safeJobUrl} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm text-app-primary hover:underline">Open job listing <ExternalLink className="h-3.5 w-3.5" /></a>}
          {application.notes && <p className="mt-4 border-t border-app-rule-soft pt-4 text-sm text-app-ink-2">{application.notes}</p>}
        </section>

        <section className="rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Relevance</h2>
              <p className="mt-2 text-3xl font-semibold text-app-ink" title={RELEVANCE_TOOLTIP}>{relevance ? `${relevance.score}%` : "—"}</p>
            </div>
            {application.fits_one_page !== null && <span className={application.fits_one_page ? "text-sm text-app-primary" : "text-sm text-app-warning"}>{application.fits_one_page ? "One-page fit" : "Could not fit one page without rewriting content"}</span>}
          </div>
          <p className="mt-3 text-xs text-app-ink-3">{RELEVANCE_TOOLTIP}</p>
          {relevance && (
            <>
              <div className="mt-4 flex flex-wrap gap-2">
                {relevance.matched_keywords.map((keyword) => <span key={`matched-${keyword}`} className="rounded-full bg-app-primary-soft px-2 py-1 text-xs text-app-primary">{keyword}</span>)}
                {relevance.missing_keywords.map((keyword) => <span key={`missing-${keyword}`} className="rounded-full bg-app-surface-muted px-2 py-1 text-xs text-app-ink-2">Missing: {keyword}</span>)}
              </div>
              <div className="mt-4 space-y-2">
                {relevance.evidence.map((item, index) => <div key={`${item.keyword}-${item.field_path}-${index}`} className="rounded bg-app-canvas px-3 py-2 text-xs text-app-ink-2"><strong>{item.keyword}</strong> · {item.section_type} · {item.field_path}<br />{item.snippet}</div>)}
              </div>
            </>
          )}
        </section>
      </div>

      <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Generated CV</h2>
        {application.cv_id ? (
          <>
            <p className="mt-2 text-sm text-app-ink-2">{linkedCV?.title || `${application.company} — ${application.role}`}</p>
            {sections.length > 0 && <p className="mt-2 text-xs text-app-ink-3">Sections: {sections.join(" → ")}</p>}
            {sourceCount !== null && <p className="mt-2 text-xs text-app-ink-3">Selected Library rows: {sourceCount}</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to={`/dashboard/builder/${application.cv_id}?application=${application.id}`} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-sm font-medium text-white hover:bg-app-primary-hover">Open/Edit CV <Pencil className="h-3.5 w-3.5" /></Link>
              <button type="button" onClick={handleExport} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"><Download className="h-3.5 w-3.5" /> Export PDF</button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-app-ink-2">{application.generation_status === "failed" ? "CV generation failed. Please retry." : "Generation is pending."}</p>
            <button type="button" onClick={handleRetry} disabled={retrying} className="mt-4 inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} /> {retrying ? "Generating…" : "Retry generation"}</button>
          </>
        )}
      </section>

      <div className="mt-6 flex justify-end gap-2">
        <button type="button" onClick={() => setEditOpen(true)} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"><Pencil className="h-3.5 w-3.5" /> Edit job</button>
        <button type="button" onClick={handleDelete} className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm text-app-danger hover:bg-app-danger-soft"><Trash2 className="h-3.5 w-3.5" /> Delete</button>
      </div>

      <ApplicationFormModal open={editOpen} onClose={() => setEditOpen(false)} initialApplication={application} />
    </div>
  );
}

export { RELEVANCE_TOOLTIP };
