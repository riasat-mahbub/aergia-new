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
import { STATUS_LABELS } from "./ApplicationsPage";

const RELEVANCE_TOOLTIP = "Weighted keyword coverage of this CV against the saved job description—not an ATS or hiring probability.";

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
    return <div className="mx-auto max-w-4xl px-4 py-8">{isLoading ? <LoadingSkeleton count={2} /> : <p className="text-sm text-gray-600">Application not found.</p>}</div>;
  }

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
        addToast(result.application.generation_error || "CV generation failed", "error");
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
      <Link to="/dashboard/applications" className="text-sm text-gray-500 hover:text-gray-700">&larr; Applications</Link>
      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{application.company}</h1>
          <p className="mt-1 text-lg text-gray-600">{application.role}</p>
        </div>
        <select
          aria-label="Application status"
          value={application.status}
          disabled={statusSaving}
          onChange={(event) => handleStatusChange(event.target.value as ApplicationStatus)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm"
        >
          {APPLICATION_STATUSES.map((status) => <option key={status} value={status}>{STATUS_LABELS[status]}</option>)}
        </select>
      </header>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Job</h2>
          <div className="mt-4 whitespace-pre-wrap text-sm leading-6 text-gray-700">{application.job_description}</div>
          {application.job_url && <a href={application.job_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm text-blue-700 hover:underline">Open job listing <ExternalLink className="h-3.5 w-3.5" /></a>}
          {application.notes && <p className="mt-4 border-t border-gray-100 pt-4 text-sm text-gray-600">{application.notes}</p>}
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Relevance</h2>
              <p className="mt-2 text-3xl font-semibold text-gray-900" title={RELEVANCE_TOOLTIP}>{relevance ? `${relevance.score}%` : "—"}</p>
            </div>
            {application.fits_one_page !== null && <span className={application.fits_one_page ? "text-sm text-emerald-700" : "text-sm text-amber-700"}>{application.fits_one_page ? "One-page fit" : "Could not fit one page without rewriting content"}</span>}
          </div>
          <p className="mt-3 text-xs text-gray-500">{RELEVANCE_TOOLTIP}</p>
          {relevance && (
            <>
              <div className="mt-4 flex flex-wrap gap-2">
                {relevance.matched_keywords.map((keyword) => <span key={`matched-${keyword}`} className="rounded-full bg-emerald-50 px-2 py-1 text-xs text-emerald-700">{keyword}</span>)}
                {relevance.missing_keywords.map((keyword) => <span key={`missing-${keyword}`} className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">Missing: {keyword}</span>)}
              </div>
              <div className="mt-4 space-y-2">
                {relevance.evidence.map((item, index) => <div key={`${item.keyword}-${item.field_path}-${index}`} className="rounded bg-gray-50 px-3 py-2 text-xs text-gray-600"><strong>{item.keyword}</strong> · {item.section_type} · {item.field_path}<br />{item.snippet}</div>)}
              </div>
            </>
          )}
        </section>
      </div>

      <section className="mt-4 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Generated CV</h2>
        {application.cv_id ? (
          <>
            <p className="mt-2 text-sm text-gray-700">{linkedCV?.title || `${application.company} — ${application.role}`}</p>
            {sections.length > 0 && <p className="mt-2 text-xs text-gray-500">Sections: {sections.join(" → ")}</p>}
            {sourceCount !== null && <p className="mt-2 text-xs text-gray-500">Selected Library rows: {sourceCount}</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to={`/dashboard/builder/${application.cv_id}?application=${application.id}`} className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">Open/Edit CV <Pencil className="h-3.5 w-3.5" /></Link>
              <button type="button" onClick={handleExport} className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"><Download className="h-3.5 w-3.5" /> Export PDF</button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-gray-600">{application.generation_status === "failed" ? application.generation_error || "Generation failed." : "Generation is pending."}</p>
            <button type="button" onClick={handleRetry} disabled={retrying} className="mt-4 inline-flex items-center gap-1 rounded-md border border-blue-200 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} /> {retrying ? "Generating…" : "Retry generation"}</button>
          </>
        )}
      </section>

      <div className="mt-6 flex justify-end gap-2">
        <button type="button" onClick={() => setEditOpen(true)} className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"><Pencil className="h-3.5 w-3.5" /> Edit job</button>
        <button type="button" onClick={handleDelete} className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm text-red-700 hover:bg-red-50"><Trash2 className="h-3.5 w-3.5" /> Delete</button>
      </div>

      <ApplicationFormModal open={editOpen} onClose={() => setEditOpen(false)} initialApplication={application} />
    </div>
  );
}

export { RELEVANCE_TOOLTIP };
