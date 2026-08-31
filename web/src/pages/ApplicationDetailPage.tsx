import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, ChevronDown, ChevronUp, Copy, Download, ExternalLink, Pencil, RefreshCw, Trash2, XCircle } from "lucide-react";
import ApplicationFormModal from "../components/applications/ApplicationFormModal";
import LoadingSkeleton from "../components/common/LoadingSkeleton";
import { exportPDF, downloadPDF, fetchCV, type CVDetail } from "../lib/api/cvs";
import {
  APPLICATION_STATUSES,
  type Application,
  type ApplicationStatus,
  type CVQualityResult,
  type RelevanceAnalysis,
} from "../lib/api/applications";
import { useApplicationStore } from "../lib/store/applicationStore";
import { useToastStore } from "../lib/store/uiStore";
import {
  cancelTailoringSession,
  createTailoringSession,
  getTailoringSessionStatus,
  type TailoringSession,
  type TailoringSessionStatusResponse,
} from "../lib/api/tailoring";
import { safeExternalUrl } from "../lib/security/safeUrl";
import {
  RELEVANCE_TOOLTIP,
  STATUS_CLASSES,
  STATUS_LABELS,
  formatFollowUpDate,
  isFollowUpOverdue,
} from "../components/applications/applicationPresentation";


function isRelevanceResult(value: Application["relevance"]): value is RelevanceAnalysis {
  return "score" in value && typeof value.score === "number";
}

function isQualityResult(value: Application["quality"]): value is CVQualityResult {
  return Boolean(value && "status" in value && "issues" in value && Array.isArray(value.issues));
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

function relevanceScoreFromSnapshot(value: Record<string, unknown> | null | undefined): number | null {
  const score = value?.score;
  return typeof score === "number" ? score : null;
}

function sessionStatusLabel(status: TailoringSessionStatusResponse["status"]): string {
  switch (status) {
    case "created": return "Ready to start";
    case "exchanged": return "Agent connected";
    case "submitted": return "Validating patch";
    case "applied": return "Tailoring applied";
    case "failed": return "Tailoring failed";
    case "expired": return "Expired";
    case "cancelled": return "Cancelled";
    case "stale": return "CV changed — restart required";
    default: return status;
  }
}

function isTerminalTailoringStatus(status: TailoringSessionStatusResponse["status"] | undefined): boolean {
  return status === "applied" || status === "failed" || status === "expired" || status === "cancelled" || status === "stale";
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
  const [jobExpanded, setJobExpanded] = useState(false);
  const [tailoringSession, setTailoringSession] = useState<TailoringSession | null>(null);
  const [tailoringStarting, setTailoringStarting] = useState(false);
  const [tailoringStatus, setTailoringStatus] = useState<TailoringSessionStatusResponse | null>(null);
  const [promptCopied, setPromptCopied] = useState(false);

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

  useEffect(() => {
    if (!tailoringSession || isTerminalTailoringStatus(tailoringStatus?.status)) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const status = await getTailoringSessionStatus(tailoringSession.session_id);
        if (cancelled) return;
        setTailoringStatus(status);
        if (status.status === "applied") {
          await fetch(tailoringSession.application_id);
        }
      } catch {
        // The shared API client reports actionable errors. Keep the last known
        // session state visible while the user can retry from this page.
      }
    };

    void poll();
    const timer = window.setInterval(() => { void poll(); }, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [fetch, tailoringSession, tailoringStatus?.status]);

  const relevance = application && isRelevanceResult(application.relevance) ? application.relevance : null;
  const sections = useMemo(() => sectionTypes(linkedCV), [linkedCV]);
  const sourceCount = selectedSourceCount(linkedCV);

  if (isLoading || !application || application.id !== id) {
    return <div className="mx-auto max-w-4xl px-4 py-8">{isLoading ? <LoadingSkeleton count={2} /> : <p className="text-sm text-app-ink-2">Application not found.</p>}</div>;
  }

  const safeJobUrl = safeExternalUrl(application.job_url);
  const safeTailoringSessionUrl = tailoringSession ? safeExternalUrl(tailoringSession.session_url) : null;

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

  const handleStartTailoring = async () => {
    setTailoringStarting(true);
    try {
      const session = await createTailoringSession(application.id);
      setTailoringSession(session);
      setTailoringStatus(null);
      setPromptCopied(false);
      addToast("Local tailoring session created", "info");
    } catch {
      addToast("Unable to create a local tailoring session", "error");
    } finally {
      setTailoringStarting(false);
    }
  };

  const handleCopyPrompt = async () => {
    if (!tailoringSession) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(tailoringSession.prompt);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = tailoringSession.prompt;
        textarea.setAttribute("readonly", "true");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setPromptCopied(true);
      addToast("Prompt copied — paste it into your coding agent", "info");
    } catch {
      addToast("Unable to copy the tailoring prompt", "error");
    }
  };

  const handleCancelTailoring = async () => {
    if (!tailoringSession) return;
    try {
      const status = await cancelTailoringSession(tailoringSession.session_id);
      setTailoringStatus(status);
      addToast("Tailoring session cancelled", "info");
    } catch {
      addToast("Unable to cancel the tailoring session", "error");
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
          <p className={`mt-2 text-sm ${isFollowUpOverdue(application.next_follow_up_at) ? "font-medium text-app-danger" : "text-app-ink-3"}`}>
            {application.next_follow_up_at ? `Next follow-up: ${formatFollowUpDate(application.next_follow_up_at)}` : "No follow-up scheduled"}
          </p>
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
        <section className={`flex flex-col overflow-hidden rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm ${jobExpanded ? "" : "h-60 md:h-64"}`}>
          <div id="application-job-details" className="relative min-h-0 flex-1 overflow-hidden">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Job</h2>
            <div className="mt-4 whitespace-pre-wrap text-sm leading-6 text-app-ink-2">{application.job_description}</div>
            {safeJobUrl && <a href={safeJobUrl} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm text-app-primary hover:underline">Open job listing <ExternalLink className="h-3.5 w-3.5" /></a>}
            {application.notes && <p className="mt-4 border-t border-app-rule-soft pt-4 text-sm text-app-ink-2">{application.notes}</p>}
            {!jobExpanded && <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-app-surface to-transparent" />}
          </div>
          <button
            type="button"
            aria-expanded={jobExpanded}
            aria-controls="application-job-details"
            onClick={() => setJobExpanded((expanded) => !expanded)}
            className="mt-3 inline-flex shrink-0 items-center gap-1 self-start text-sm font-medium text-app-primary hover:text-app-primary-hover"
          >
            {jobExpanded ? "See less" : "See more"}
            {jobExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </section>

        <section className="flex flex-col overflow-hidden rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
          <div className="relative min-h-0 flex-1 overflow-hidden">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Relevance</h2>
                <p className="mt-2 text-3xl font-semibold text-app-ink" title={RELEVANCE_TOOLTIP}>{relevance ? `${relevance.score}%` : "—"}</p>
              </div>
              {application.fits_one_page !== null && <span className={application.fits_one_page ? "text-sm text-app-primary" : "text-sm text-app-warning"}>{application.fits_one_page ? "One-page fit" : "Could not fit one page without rewriting content"}</span>}
            </div>
            <p className="mt-3 text-xs text-app-ink-3">{RELEVANCE_TOOLTIP}</p>
            {application.cv_id && <Link to={`/dashboard/builder/${application.cv_id}?application=${application.id}`} className="mt-4 inline-flex text-sm font-medium text-app-primary hover:text-app-primary-hover">Open the linked CV to inspect matched, missing, and source evidence</Link>}
          </div>
        </section>
      </div>

      <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Generated CV</h2>
        {application.cv_id ? (
          <>
            <p className="mt-2 text-sm text-app-ink-2">{linkedCV?.title || `${application.company} — ${application.role}`}</p>
            {sections.length > 0 && <p className="mt-2 text-xs text-app-ink-3">Sections: {sections.join(" → ")}</p>}
            {sourceCount !== null && <p className="mt-2 text-xs text-app-ink-3">Selected Library rows: {sourceCount}</p>}
            {isQualityResult(application.quality) && (
              <div className="mt-4 rounded-md bg-app-canvas px-3 py-3">
                <p className={`text-sm font-medium ${application.quality.status === "error" ? "text-app-danger" : application.quality.status === "warning" ? "text-app-warning" : "text-app-primary"}`}>
                  Quality checks: {application.quality.status === "pass" ? "Passed" : `${application.quality.issues.length} issue${application.quality.issues.length === 1 ? "" : "s"}`}
                </p>
                {application.quality.page_count !== null && <p className="mt-1 text-xs text-app-ink-3">Rendered pages: {application.quality.page_count}</p>}
                {application.quality.issues.length > 0 && <ul className="mt-2 space-y-1 text-xs text-app-ink-2">{application.quality.issues.map((issue, index) => <li key={`${issue.code}-${index}`}>{issue.message}</li>)}</ul>}
              </div>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to={`/dashboard/builder/${application.cv_id}?application=${application.id}`} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-sm font-medium text-white hover:bg-app-primary-hover">Open/Edit CV <Pencil className="h-3.5 w-3.5" /></Link>
              <button type="button" onClick={handleExport} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"><Download className="h-3.5 w-3.5" /> Export PDF</button>
              <button type="button" onClick={handleStartTailoring} disabled={tailoringStarting} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50">
                {tailoringStarting ? "Preparing LLM tailoring…" : "LLM Tailoring"}
              </button>
            </div>
            <p className="mt-3 text-xs text-app-ink-3">Your installed coding agent does the generative work locally. Aergia sends it only this application’s tailoring evidence and validates the returned patch.</p>
            {tailoringSession && (
              <div className="mt-4 rounded-md bg-app-canvas px-3 py-3" role="status">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-app-ink">Use your coding agent</p>
                    <p className="mt-1 text-xs text-app-ink-3">
                      {sessionStatusLabel(tailoringStatus?.status ?? tailoringSession.status)} · expires {new Date(tailoringSession.expires_at).toLocaleTimeString()}
                    </p>
                  </div>
                  {!isTerminalTailoringStatus(tailoringStatus?.status) && (
                    <button type="button" onClick={handleCancelTailoring} className="inline-flex items-center gap-1 text-xs font-medium text-app-danger hover:underline">
                      <XCircle className="h-3.5 w-3.5" /> Cancel
                    </button>
                  )}
                </div>
                <p className="mt-3 text-xs text-app-ink-2">Copy this prompt and paste it into Codex, Claude Code, or OpenCode with the Aergia tailoring skill installed.</p>
                <textarea
                  aria-label="Aergia tailoring prompt"
                  readOnly
                  value={tailoringSession.prompt}
                  rows={6}
                  className="mt-2 block w-full resize-y rounded border border-app-rule-strong bg-app-surface px-2 py-2 text-xs leading-5 text-app-ink-2"
                />
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <button type="button" onClick={handleCopyPrompt} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover">
                    {promptCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    {promptCopied ? "Copied" : "Copy prompt"}
                  </button>
                  {safeTailoringSessionUrl && <a href={safeTailoringSessionUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-medium text-app-primary hover:underline">
                    Open session link <ExternalLink className="h-3.5 w-3.5" />
                  </a>}
                </div>
                {tailoringStatus?.result && (
                  <div className="mt-3 border-t border-app-rule-soft pt-3 text-xs text-app-ink-2">
                    <p className="font-medium text-app-ink">Result</p>
                    <p className="mt-1">
                      Relevance: {relevanceScoreFromSnapshot(tailoringStatus.result.before_relevance) ?? "—"}% → {relevanceScoreFromSnapshot(tailoringStatus.result.relevance) ?? "—"}%
                    </p>
                    {tailoringStatus.result.gaps.length > 0 && <p className="mt-1">Remaining gaps: {tailoringStatus.result.gaps.map((gap) => gap.requirement).join(", ")}</p>}
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <>
            <p className="mt-2 text-sm text-app-ink-2">{application.generation_status === "failed" ? "CV generation failed. Please retry." : "Generation is pending."}</p>
            <button type="button" onClick={handleRetry} disabled={retrying} className="mt-4 inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} /> {retrying ? "Generating…" : "Retry generation"}</button>
          </>
        )}
      </section>

      <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Status history</h2>
        {(application.status_history ?? []).length > 0 ? (
          <ol className="mt-4 space-y-3 border-l border-app-rule pl-4">
            {(application.status_history ?? []).map((event) => (
              <li key={event.id} className="relative text-sm text-app-ink-2">
                <span className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-app-primary" />
                <span className="font-medium text-app-ink">{event.from_status ? `${STATUS_LABELS[event.from_status]} → ` : "Started as "}{STATUS_LABELS[event.to_status]}</span>
                <span className="ml-2 text-xs text-app-ink-3">{formatFollowUpDate(event.changed_at.slice(0, 10))}</span>
              </li>
            ))}
          </ol>
        ) : <p className="mt-2 text-sm text-app-ink-2">No status changes recorded yet.</p>}
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
