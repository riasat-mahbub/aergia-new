import { motion } from "motion/react";
import { ArrowRight, CalendarDays, FileText, RefreshCw, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import type { Application } from "../../lib/api/applications";
import {
  formatApplicationDate,
  formatFollowUpDate,
  isFollowUpOverdue,
  relevanceScore,
  RELEVANCE_TOOLTIP,
  STATUS_CLASSES,
  STATUS_LABELS,
  STATUS_STRIP_CLASSES,
} from "./applicationPresentation";

interface ApplicationCardProps {
  application: Application;
  retrying: boolean;
  onRetry: () => void;
  onDelete: () => void;
}

export default function ApplicationCard({ application, retrying, onRetry, onDelete }: ApplicationCardProps) {
  const score = relevanceScore(application.relevance);
  const hasGeneratedCv = application.generation_status === "ready" && Boolean(application.cv_id);
  const fitLabel = application.fits_one_page === true
    ? "One-page fit"
    : application.fits_one_page === false
      ? "Needs content trimming"
      : null;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, boxShadow: "0 8px 25px rgba(47,69,80,0.12)" }}
      className="overflow-hidden rounded-lg border border-app-rule bg-app-surface shadow-sm transition-shadow"
    >
      <div className={`h-1.5 ${STATUS_STRIP_CLASSES[application.status]}`} />
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-app-ink-3">Application</p>
            <Link
              to={`/dashboard/applications/${application.id}`}
              className="mt-1 block truncate text-lg font-semibold text-app-ink hover:text-app-primary"
            >
              {application.company}
            </Link>
            <p className="mt-1 truncate text-sm text-app-ink-2">{application.role}</p>
          </div>
          <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[application.status]}`}>
            {STATUS_LABELS[application.status]}
          </span>
        </div>

        <p className="mt-4 line-clamp-2 text-sm leading-6 text-app-ink-2">{application.job_description}</p>

        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-app-ink-3">
          <span className="inline-flex items-center gap-1">
            <CalendarDays className="h-3.5 w-3.5" />
            {application.applied_at ? `Applied ${formatApplicationDate(application.applied_at)}` : "Not applied"}
          </span>
          <span>Updated {formatApplicationDate(application.updated_at)}</span>
          <span className={isFollowUpOverdue(application.next_follow_up_at) ? "font-medium text-app-danger" : ""}>
            {application.next_follow_up_at
              ? `Follow up ${formatFollowUpDate(application.next_follow_up_at)}`
              : "No follow-up set"}
          </span>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md bg-app-canvas px-3 py-2.5 text-xs">
          {score !== null && <span className="font-medium text-app-ink" title={RELEVANCE_TOOLTIP}>Relevance {score}%</span>}
          {fitLabel && <span className={application.fits_one_page ? "text-app-primary" : "text-app-warning"}>{fitLabel}</span>}
          {hasGeneratedCv ? (
            <span className="ml-auto inline-flex items-center gap-1 font-medium text-app-primary">
              <FileText className="h-3.5 w-3.5" />
              CV ready
            </span>
          ) : (
            <span className="text-app-ink-3">
              {application.generation_status === "failed" ? "CV generation failed" : "CV not generated"}
            </span>
          )}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-app-rule-soft pt-4">
          <Link
            to={`/dashboard/applications/${application.id}`}
            className="inline-flex items-center gap-1 rounded bg-app-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-app-primary-hover"
          >
            View application
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          {!hasGeneratedCv && (
            <button
              type="button"
              onClick={onRetry}
              disabled={retrying}
              className="inline-flex items-center gap-1 rounded border border-app-primary-soft px-3 py-1.5 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} />
              {retrying ? "Generating…" : application.generation_status === "failed" ? "Retry CV" : "Generate CV"}
            </button>
          )}
          <button
            type="button"
            onClick={onDelete}
            className="ml-auto inline-flex items-center gap-1 rounded px-2 py-1.5 text-sm text-app-ink-3 hover:bg-app-danger-soft hover:text-app-danger"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
        {application.generation_error && <p className="mt-3 text-xs text-app-danger">{application.generation_error}</p>}
      </div>
    </motion.article>
  );
}
