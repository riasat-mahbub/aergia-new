import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Pencil, Trash2 } from "lucide-react";
import ApplicationFormModal from "../components/ApplicationFormModal";
import ApplicationJobPanel from "../components/detail/ApplicationJobPanel";
import ApplicationRelevancePanel from "../components/detail/ApplicationRelevancePanel";
import ApplicationStatusHistory from "../components/detail/ApplicationStatusHistory";
import GeneratedCvPanel from "../components/detail/GeneratedCvPanel";
import LoadingSkeleton from "@/shared/ui/LoadingSkeleton";
import { exportPDF } from "@/features/cvs";
import { downloadBlob } from "@/shared/browser/downloadBlob";
import { APPLICATION_STATUSES } from "@/features/applications/types";
import type {
  ApplicationStatus,
} from "@/features/applications/types";
import { useApplicationStore } from "@/features/applications/state/applicationStore";
import { useToastStore } from "@/shared/state/uiStore";
import {
  formatFollowUpDate,
  isFollowUpOverdue,
} from "../domain/list/applicationPresentation";
import { STATUS_CLASSES, STATUS_LABELS } from "../domain/applicationStatus";
import {
  isRelevanceResult,
  sectionTypes,
  selectedSourceCount,
} from "../domain/detail/applicationDetail";
import { useTailoringSession } from "@/features/tailoring";
import { useLinkedCv } from "../hooks/useLinkedCv";

export interface ApplicationDetailPageProps {
  applicationId: string;
}

export default function ApplicationDetailPage({ applicationId }: ApplicationDetailPageProps) {
  const id = applicationId;
  const navigate = useNavigate();
  const application = useApplicationStore((state) => state.currentApplication);
  const isLoading = useApplicationStore((state) => state.isLoading);
  const error = useApplicationStore((state) => state.error);
  const fetch = useApplicationStore((state) => state.fetch);
  const update = useApplicationStore((state) => state.update);
  const generate = useApplicationStore((state) => state.generate);
  const remove = useApplicationStore((state) => state.remove);
  const addToast = useToastStore((state) => state.addToast);
  const [editOpen, setEditOpen] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [statusSaving, setStatusSaving] = useState(false);
  const {
    tailoringSession,
    tailoringStarting,
    tailoringStatus,
    tailoringResult,
    promptCopied,
    startTailoring,
    copyPrompt,
    cancelTailoring,
  } = useTailoringSession({ applicationId: application?.id ?? id, fetchApplication: fetch, addToast });

  useEffect(() => {
    if (id) fetch(id);
  }, [fetch, id]);

  const linkedCV = useLinkedCv(application?.cv_id);

  const relevance = application && isRelevanceResult(application.relevance) ? application.relevance : null;
  const sections = useMemo(() => sectionTypes(linkedCV), [linkedCV]);
  const sourceCount = selectedSourceCount(linkedCV);

  if (isLoading) {
    return <div className="mx-auto max-w-4xl px-4 py-8"><LoadingSkeleton count={2} /></div>;
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-lg border border-app-danger/30 bg-app-danger-soft p-5 text-sm text-app-danger" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => fetch(id)} className="mt-3 rounded-md border border-app-danger/40 px-3 py-1.5 font-medium hover:bg-app-danger/10">
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!application || application.id !== id) {
    return <div className="mx-auto max-w-4xl px-4 py-8"><p className="text-sm text-app-ink-2">Application not found.</p></div>;
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
        navigate({
          to: "/builder/$id",
          params: { id: result.cv_id },
          search: { application: application.id },
        });
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
      downloadBlob(blob, `${application.company}-${application.role}.pdf`);
    } catch {
      addToast("Unable to export this CV", "error");
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete the application for ${application.company}?`)) return;
    try {
      await remove(application.id);
      addToast("Application deleted", "info");
      navigate({ to: "/applications" });
    } catch {
      addToast("Unable to delete this application", "error");
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <Link to="/applications" className="text-sm text-app-ink-3 hover:text-app-ink-2">&larr; Applications</Link>
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
        <ApplicationJobPanel application={application} />
        <ApplicationRelevancePanel application={application} relevance={relevance} />
      </div>

      <GeneratedCvPanel
        application={application}
        linkedCV={linkedCV}
        sections={sections}
        sourceCount={sourceCount}
        tailoringSession={tailoringSession}
        tailoringStarting={tailoringStarting}
        tailoringStatus={tailoringStatus}
        tailoringResult={tailoringResult}
        promptCopied={promptCopied}
        retrying={retrying}
        onExport={handleExport}
        onRetry={handleRetry}
        onStartTailoring={startTailoring}
        onCopyPrompt={copyPrompt}
        onCancelTailoring={cancelTailoring}
      />

      <ApplicationStatusHistory application={application} />

      <div className="mt-6 flex justify-end gap-2">
        <button type="button" onClick={() => setEditOpen(true)} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"><Pencil className="h-3.5 w-3.5" /> Edit job</button>
        <button type="button" onClick={handleDelete} className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-sm text-app-danger hover:bg-app-danger-soft"><Trash2 className="h-3.5 w-3.5" /> Delete</button>
      </div>

      <ApplicationFormModal open={editOpen} onClose={() => setEditOpen(false)} initialApplication={application} />
    </div>
  );
}
