import { Link } from "@tanstack/react-router";
import { Check, Copy, Download, ExternalLink, Pencil, XCircle } from "lucide-react";
import type { Application, ScanResult } from "@/features/applications/types";
import type { CVDetail } from "@/features/cvs";
import type {
  TailoringDraftReview,
  TailoringFitReview,
  TailoringIssue,
  TailoringSession,
  TailoringSessionResult,
  TailoringSessionStatusResponse,
} from "@/features/tailoring";
import { safeExternalUrl } from "@/shared/security/safeUrl";
import { sessionStatusLabel } from "@/features/tailoring";

type TailoringOwnerAction = "cancel" | "reevaluate" | "accept" | "discard";
type FitReviewApplicability = "current" | "earlier_version" | "not_run";

interface ApplicationCvPanelProps {
  application: Application;
  linkedCV: CVDetail | null;
  sections: string[];
  sourceCount: number | null;
  tailoringSession: TailoringSession | null;
  tailoringStarting: boolean;
  tailoringStatus: TailoringSessionStatusResponse | null;
  tailoringResult: TailoringSessionResult | null;
  promptCopied: boolean;
  tailoringAction: TailoringOwnerAction | null;
  tailoringActionError: string | null;
  onExport: () => void;
  onStartTailoring: () => void;
  onCopyPrompt: () => void;
  onCancelTailoring: () => void;
  onReevaluateDraft: () => void;
  onAcceptDraft: () => void;
  onDiscardDraft: () => void;
}

interface ScannerWarning {
  key: string;
  title: string;
  detail: string;
}

function TextListDetails({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return <p className="mt-2 text-xs text-app-ink-3">No {title.toLowerCase()} were recorded.</p>;
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">
        {title} ({items.length})
      </summary>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-app-ink-2">
        {items.map((item, index) => <li key={`${index}-${item.slice(0, 48)}`} className="break-words">{item}</li>)}
      </ul>
    </details>
  );
}

function IssueListDetails({
  title,
  items,
  tone = "normal",
}: {
  title: string;
  items: TailoringIssue[];
  tone?: "normal" | "risk";
}) {
  if (items.length === 0) return null;
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">
        {title} ({items.length})
      </summary>
      <ul className="mt-2 space-y-2">
        {items.map((item, index) => (
          <li
            key={`${item.id}-${index}`}
            className={`min-w-0 rounded-md px-3 py-2 text-xs leading-5 ${tone === "risk" ? "bg-app-danger-soft text-app-ink-2" : "bg-app-canvas text-app-ink-2"}`}
          >
            <p className="break-words font-medium">{item.message}</p>
            {item.detail && <p className="mt-1 break-words text-app-ink-3">{item.detail}</p>}
            <p className="mt-1 break-words text-app-ink-3">{[item.category, item.priority].filter(Boolean).join(" · ")}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

function collectScannerWarnings(scan: ScanResult | null): ScannerWarning[] {
  if (!scan) return [];
  const warnings: ScannerWarning[] = [];
  scan.requirement_extraction?.warnings?.forEach((warning, index) => {
    warnings.push({ key: `extraction-${index}`, title: "Requirement extraction", detail: warning });
  });
  scan.presentation_quality?.findings?.filter((finding) => finding.severity !== "info").forEach((finding, index) => {
    warnings.push({
      key: `quality-${finding.code}-${index}`,
      title: `CV quality · ${finding.code}`,
      detail: [finding.explanation, finding.location?.excerpt].filter(Boolean).join(" — "),
    });
  });
  scan.pdf_recovery?.checks?.filter((check) => check.status === "warning" || check.status === "fail").forEach((check, index) => {
    warnings.push({
      key: `pdf-${check.code}-${index}`,
      title: `PDF recovery · ${check.code}`,
      detail: [check.explanation, ...(check.missing_items ?? []), ...(check.affected_items ?? [])].filter(Boolean).join(" — "),
    });
  });

  const ats = scan.ats_guidance;
  if (ats) {
    const findings = [
      ...(ats.common_findings ?? []),
      ...(ats.platform_sensitive_findings ?? []),
      ...Object.values(ats.platforms ?? {}).flatMap((platform) => [...(platform.findings ?? []), ...(platform.tips ?? [])]),
    ];
    const seen = new Set<string>();
    findings.forEach((finding, index) => {
      if (finding.severity !== "warning" && finding.severity !== "recommendation") return;
      const dedupeKey = `${finding.rule_id}:${finding.title}`;
      if (seen.has(dedupeKey)) return;
      seen.add(dedupeKey);
      warnings.push({
        key: `ats-${finding.id}-${index}`,
        title: `ATS · ${finding.title}`,
        detail: [finding.explanation, finding.action, ...finding.affected_items, ...finding.missing_items].filter(Boolean).join(" — "),
      });
    });
  }
  return warnings;
}

function ScannerWarningDetails({ scan }: { scan: ScanResult | null }) {
  const warnings = collectScannerWarnings(scan);
  if (warnings.length === 0) return null;
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">
        Parsing, ATS, quality, and PDF warnings ({warnings.length})
      </summary>
      <ul className="mt-2 space-y-2">
        {warnings.map((warning) => (
          <li key={warning.key} className="min-w-0 rounded-md bg-app-canvas px-3 py-2 text-xs leading-5 text-app-ink-2">
            <p className="break-words font-medium">{warning.title}</p>
            <p className="mt-1 break-words">{warning.detail}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

function EvaluationFeedback({
  label,
  evaluation,
  scannerResult,
  warnings,
}: {
  label: string;
  evaluation: TailoringDraftReview["evaluation"];
  scannerResult: ScanResult | null;
  warnings: string[];
}) {
  const jobFitValue = scannerResult?.semantic?.summary?.job_fit;
  const jobFit = typeof jobFitValue === "number" ? `${Math.round(jobFitValue * 100)}%` : "Not available";
  const riskFindings = evaluation?.risk_findings ?? evaluation?.blockers ?? [];
  return (
    <div className="mt-2">
      <p className="text-xs font-semibold text-app-ink">{label}</p>
      <p className="mt-1 text-xs text-app-ink-2">Scanner Job Fit: {jobFit}</p>
      <ScannerWarningDetails scan={scannerResult} />
      {warnings.length > 0 && <TextListDetails title="Render warnings" items={warnings} />}
      {evaluation && (
        <div className="mt-2">
          <IssueListDetails title="Risk findings" items={riskFindings} tone="risk" />
          <IssueListDetails title="Required conflicts and review items" items={evaluation.review_items ?? []} tone="risk" />
          <IssueListDetails title="Improvements" items={evaluation.improvements ?? []} />
          <IssueListDetails title="Regressions and trade-offs" items={evaluation.regressions ?? []} />
          {evaluation.non_actionable_gaps?.length > 0 && (
            <div className="mt-2">
              <p className="text-xs text-app-ink-3">These findings describe what this CV does not currently demonstrate; they do not assess your full Library or all of your experience.</p>
              <IssueListDetails title="Not demonstrated in this CV" items={evaluation.non_actionable_gaps} />
            </div>
          )}
          <IssueListDetails title="Recommendations" items={evaluation.recommendations ?? []} />
        </div>
      )}
      {!evaluation && !scannerResult && warnings.length === 0 && <p className="mt-1 text-xs text-app-ink-3">No scanner report is available for this version.</p>}
    </div>
  );
}

function applicabilityLabel(applicability: FitReviewApplicability): string {
  switch (applicability) {
    case "current": return "Applies to the current draft";
    case "earlier_version": return "Earlier version";
    case "not_run": return "Not run";
  }
}

function FitReviewSection({
  review,
  applicability,
}: {
  review: TailoringFitReview | null;
  applicability: FitReviewApplicability;
}) {
  const statusLabel = review?.status === "completed"
    ? "Completed"
    : review?.status === "unavailable"
      ? "Unavailable"
      : review?.status === "skipped_explicitly"
        ? "Skipped at your request"
        : "Not run";
  return (
    <section className="mt-3 border-t border-app-rule-soft pt-3" aria-labelledby="fit-review-title">
      <h3 id="fit-review-title" className="text-sm font-semibold text-app-ink">Independent fit review</h3>
      <p className="mt-1 text-xs text-app-ink-3">{applicabilityLabel(applicability)} · {statusLabel}</p>
      {!review && <p className="mt-2 text-xs text-app-ink-2">No independent PDF review was recorded for this submission.</p>}
      {review?.status === "completed" && (
        <div className="mt-2 space-y-1 text-xs leading-5 text-app-ink-2">
          <p><span className="font-medium text-app-ink">Verdict:</span> {review.verdict.replace(/_/g, " ")}</p>
          <p><span className="font-medium text-app-ink">Review method:</span> {review.mode === "fresh_agent" ? "Fresh reviewer agent" : "Manual external review"}</p>
          <p className="break-words">{review.rationale}</p>
          <TextListDetails title="Strong connections" items={review.strong_connections} />
          <TextListDetails title="Weak or missing connections" items={review.weak_or_missing_connections} />
          <TextListDetails title="Recommended changes" items={review.recommended_changes} />
        </div>
      )}
      {(review?.status === "unavailable" || review?.status === "skipped_explicitly") && (
        <p className="mt-2 break-words text-xs leading-5 text-app-ink-2">{review.reason}</p>
      )}
      <p className="mt-2 text-xs text-app-ink-3">This report is advisory. A generic verdict or warning does not prevent acceptance.</p>
    </section>
  );
}

function actionAnnouncement(action: TailoringOwnerAction | null): string | null {
  switch (action) {
    case "cancel": return "Cancelling tailoring…";
    case "reevaluate": return "Reevaluating the saved draft…";
    case "accept": return "Accepting the current draft…";
    case "discard": return "Discarding the pending draft…";
    default: return null;
  }
}

export default function ApplicationCvPanel({
  application,
  linkedCV,
  sections,
  sourceCount,
  tailoringSession,
  tailoringStarting,
  tailoringStatus,
  tailoringResult,
  promptCopied,
  tailoringAction,
  tailoringActionError,
  onExport,
  onStartTailoring,
  onCopyPrompt,
  onCancelTailoring,
  onReevaluateDraft,
  onAcceptDraft,
  onDiscardDraft,
}: ApplicationCvPanelProps) {
  const safeTailoringSessionUrl = tailoringSession ? safeExternalUrl(tailoringSession.session_url) : null;
  const safeTailoringSkillUrl = tailoringSession ? safeExternalUrl(tailoringSession.skill_url) : null;
  const result = tailoringStatus?.result ?? tailoringResult;
  const sessionStatus = tailoringStatus?.status ?? tailoringSession?.status;
  const protocolVersion = tailoringStatus?.protocol_version ?? tailoringSession?.protocol_version ?? result?.protocol_version ?? 10;
  const isV10 = protocolVersion >= 10;
  const ownerReview = tailoringStatus?.draft_review ?? null;
  const draftId = tailoringStatus?.draft_cv_id ?? result?.draft_cv_id ?? null;
  const storedDraft = sessionStatus === "draft_ready"
    || sessionStatus === "stale"
    || (sessionStatus === "expired" && Boolean(draftId));
  const showDraftReview = storedDraft;
  const reviewIsCurrent = sessionStatus === "draft_ready" && (isV10 ? ownerReview?.state === "current" : Boolean(result));
  const submittedEvaluation = result?.evaluation ?? result?.tailoring_evaluation ?? null;
  const submittedScanner = result?.scanner_result ?? null;
  const currentEvaluation = isV10 ? (ownerReview?.state === "current" ? ownerReview.evaluation : null) : submittedEvaluation;
  const currentScanner = isV10 ? (ownerReview?.state === "current" ? ownerReview.scanner_result : null) : submittedScanner;
  const currentWarnings = isV10 ? (ownerReview?.state === "current" ? ownerReview.warnings : []) : (result?.render_warnings ?? []);
  const submittedWarnings = result?.render_warnings ?? [];
  const currentEvaluationHash = currentEvaluation?.candidate_hash ?? null;
  const submittedHash = result?.candidate_hash ?? submittedEvaluation?.candidate_hash ?? null;
  const submittedFitReview = result?.protocol_version === 10 ? result.fit_review ?? null : null;
  const fitReview = isV10 ? (ownerReview?.fit_review ?? submittedFitReview) : null;
  const fitApplicability: FitReviewApplicability = !fitReview
    ? "not_run"
    : sessionStatus === "draft_ready" && ownerReview?.fit_review
      ? ownerReview.fit_review_applicability
      : "earlier_version";
  const showSubmittedHistory = Boolean(result) && (
    (isV10 && !reviewIsCurrent)
    || (isV10 && reviewIsCurrent && currentEvaluationHash !== null && submittedHash !== null && currentEvaluationHash !== submittedHash)
    || (!isV10 && sessionStatus === "stale")
  );
  const historyEvaluation = sessionStatus === "stale" && ownerReview?.state === "current"
    ? ownerReview.evaluation
    : submittedEvaluation;
  const historyScanner = sessionStatus === "stale" && ownerReview?.state === "current"
    ? ownerReview.scanner_result
    : submittedScanner;
  const historyWarnings = sessionStatus === "stale" && ownerReview?.state === "current"
    ? ownerReview.warnings
    : submittedWarnings;
  const hasCurrentV10Basis = ownerReview?.state === "current"
    && typeof ownerReview.cv_revision === "number"
    && Number.isInteger(ownerReview.cv_revision)
    && typeof ownerReview.candidate_hash === "string"
    && /^[0-9a-f]{64}$/.test(ownerReview.candidate_hash);
  const hasLegacyDraft = !isV10 && Boolean(draftId);
  const canOpenDraft = Boolean(draftId)
    && (!isV10 || ownerReview?.state === "current" || ownerReview?.state === "needs_reevaluation")
    && (sessionStatus === "draft_ready" || sessionStatus === "stale" || sessionStatus === "expired");
  const canReevaluate = isV10
    && sessionStatus === "draft_ready"
    && ownerReview?.state === "needs_reevaluation"
    && typeof ownerReview.cv_revision === "number"
    && Number.isInteger(ownerReview.cv_revision);
  const canAccept = sessionStatus === "draft_ready" && (isV10 ? hasCurrentV10Basis : hasLegacyDraft);
  const canDiscard = showDraftReview;
  const isActiveSession = sessionStatus === "created" || sessionStatus === "exchanged";
  const tailoringBlocksNewSession = isActiveSession || sessionStatus === "draft_ready" || sessionStatus === "stale" || (sessionStatus === "expired" && Boolean(draftId));
  const canRestart = sessionStatus === "rejected" || sessionStatus === "accepted" || sessionStatus === "failed" || sessionStatus === "expired" || sessionStatus === "cancelled";
  const isCreated = sessionStatus === "created";
  const showOneTimePrompt = Boolean(
    tailoringSession?.code.trim()
      && tailoringSession.prompt.trim()
      && isCreated,
  );
  const announcement = actionAnnouncement(tailoringAction);

  return (
    <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm" aria-labelledby="application-cv-panel-title">
      <h2 id="application-cv-panel-title" className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Linked CV and tailoring</h2>
      {application.cv_id ? (
        <>
          <p className="mt-2 text-sm text-app-ink-2">{linkedCV?.title || `${application.company} — ${application.role}`}</p>
          {sections.length > 0 && <p className="mt-2 text-xs text-app-ink-3">Sections: {sections.join(" → ")}</p>}
          {sourceCount !== null && <p className="mt-2 text-xs text-app-ink-3">Selected Library rows: {sourceCount}</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/builder/$id" params={{ id: application.cv_id }} search={{ application: application.id }} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-sm font-medium text-white hover:bg-app-primary-hover">Open/Edit CV <Pencil className="h-3.5 w-3.5" /></Link>
            <button type="button" onClick={onExport} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"><Download className="h-3.5 w-3.5" /> Export PDF</button>
          </div>
        </>
      ) : (
        <p className="mt-2 text-sm text-app-ink-2">No CV is linked yet. Link one in Scanner analysis or start a tailoring session to create a draft.</p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onStartTailoring}
          disabled={tailoringStarting || tailoringAction !== null || tailoringBlocksNewSession}
          className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"
        >
          {tailoringStarting ? "Preparing tailoring…" : tailoringBlocksNewSession ? "Finish current tailoring first" : canRestart ? "Start new tailoring" : "Tailor with AI"}
        </button>
      </div>
      {tailoringActionError && <p className="mt-3 text-xs leading-5 text-app-danger" role="alert" aria-live="assertive">{tailoringActionError}</p>}
      <p className="mt-3 text-xs text-app-ink-3">Your coding agent receives your full profile and every Library entry, composes a complete CV, and previews the rendered result. Your linked CV stays in place until you accept the draft.</p>

      {tailoringSession && (
        <div className="mt-4 rounded-md bg-app-canvas px-3 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-app-ink">Use your coding agent</p>
              <p className="mt-1 break-words text-xs text-app-ink-3">{sessionStatus ? sessionStatusLabel(sessionStatus) : "Ready to start"}{sessionStatus === "draft_ready" ? " · ready for review" : (isActiveSession ? ` · agent access expires ${new Date(tailoringSession.expires_at).toLocaleTimeString()}` : "")}</p>
            </div>
            {isActiveSession && <button type="button" onClick={onCancelTailoring} disabled={tailoringAction !== null} className="inline-flex items-center gap-1 text-xs font-medium text-app-danger hover:underline disabled:opacity-50"><XCircle className="h-3.5 w-3.5" /> {tailoringAction === "cancel" ? "Cancelling…" : "Cancel"}</button>}
          </div>

          {showOneTimePrompt && (
            <>
              <p className="mt-3 text-xs text-app-ink-2">Copy this one-time prompt and paste it into Codex, Claude Code, or OpenCode.</p>
              <textarea aria-label="Aergia tailoring prompt" readOnly value={tailoringSession.prompt} rows={6} className="mt-2 block w-full resize-y rounded border border-app-rule-strong bg-app-surface px-2 py-2 text-xs leading-5 text-app-ink-2" />
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <button type="button" onClick={onCopyPrompt} disabled={tailoringAction !== null} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover disabled:opacity-50">{promptCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}{promptCopied ? "Copied" : "Copy prompt"}</button>
                {safeTailoringSessionUrl && <a href={safeTailoringSessionUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-medium text-app-primary hover:underline">Open session link <ExternalLink className="h-3.5 w-3.5" /></a>}
                {safeTailoringSkillUrl && <a href={safeTailoringSkillUrl} className="inline-flex items-center gap-1 text-xs font-medium text-app-primary hover:underline" download>Install tailoring skill <Download className="h-3.5 w-3.5" /></a>}
              </div>
            </>
          )}
          {isCreated && !showOneTimePrompt && <p className="mt-3 text-xs leading-5 text-app-ink-2" role="status">This loaded session has no reusable one-time code. Cancel it and start a new session to get a fresh prompt.</p>}
          {sessionStatus === "exchanged" && <p className="mt-3 text-xs leading-5 text-app-ink-2" role="status">Your coding agent has connected. This page will update when it submits a draft.</p>}

          {showDraftReview && (
            <div className="mt-3 border-t border-app-rule-soft pt-3 text-xs text-app-ink-2">
              <p className="font-medium text-app-ink">{sessionStatus === "stale" ? "Draft needs recovery" : "Draft ready for your review"}</p>
              {sessionStatus === "stale" && <p className="mt-1 break-words">The application or source CV changed. Discard this draft and start a new session to review current information.</p>}
              {reviewIsCurrent && ownerReview?.state === "current" && <p className="mt-1">Current review applies to saved draft revision {ownerReview.cv_revision ?? "unknown"}.</p>}
              {sessionStatus === "stale" && ownerReview?.state === "current" && <p className="mt-1">This saved draft has a review for the previous application target.</p>}
              {ownerReview?.state === "needs_reevaluation" && <p className="mt-1">The saved draft changed after its last review. Reevaluate the saved version before accepting it.</p>}
              {isV10 && ownerReview?.state === "unavailable" && <p className="mt-1">This draft is no longer available. Discard the pending session to clear it, then start a new one.</p>}
              {isV10 && !ownerReview && <p className="mt-1">The current owner review is unavailable. Discard this pending session, then start a new one to review a current draft.</p>}
              {isV10 && ownerReview?.state === "needs_reevaluation" && ownerReview.fit_review_applicability === "earlier_version" && <p className="mt-1">The independent fit review below describes an earlier version of this draft.</p>}

              <section className="mt-3 border-t border-app-rule-soft pt-3" aria-labelledby="scanner-feedback-title">
                <h3 id="scanner-feedback-title" className="text-sm font-semibold text-app-ink">Scanner feedback</h3>
                <p className="mt-1 text-xs text-app-ink-3">These findings describe the tailored CV shown here. They do not assess the full Library or all of your experience.</p>
                {reviewIsCurrent && <EvaluationFeedback label={isV10 ? "Current owner review" : "Submitted review · historical protocol"} evaluation={currentEvaluation} scannerResult={currentScanner} warnings={currentWarnings} />}
                {!reviewIsCurrent && isV10 && <p className="mt-2 text-xs text-app-ink-3">There is no current scanner report. Reevaluate the saved draft to refresh these findings.</p>}
                {showSubmittedHistory && result && (
                  <details className="mt-3 border-t border-app-rule-soft pt-3">
                    <summary className="cursor-pointer text-xs font-medium text-app-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-primary">Earlier review feedback</summary>
                    <EvaluationFeedback label={sessionStatus === "stale" ? "Review for the previous application target" : "Original agent preview"} evaluation={historyEvaluation} scannerResult={historyScanner} warnings={historyWarnings} />
                  </details>
                )}
              </section>

              <FitReviewSection review={fitReview} applicability={fitApplicability} />

              <section className="mt-3 border-t border-app-rule-soft pt-3" aria-labelledby="author-notes-title">
                <h3 id="author-notes-title" className="text-sm font-semibold text-app-ink">Author notes</h3>
                {(result?.review_notes ?? []).length > 0
                  ? <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-app-ink-2">{result?.review_notes?.map((note, index) => <li key={`${index}-${note.slice(0, 48)}`} className="break-words">{note}</li>)}</ul>
                  : <p className="mt-2 text-xs text-app-ink-3">No author notes were recorded.</p>}
              </section>

              <div className="mt-3 flex flex-wrap gap-2">
                {canOpenDraft && draftId && <Link aria-disabled={tailoringAction !== null} tabIndex={tailoringAction !== null ? -1 : undefined} to="/builder/$id" params={{ id: draftId }} search={{ application: application.id }} className={`inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover ${tailoringAction !== null ? "pointer-events-none opacity-50" : ""}`}><Pencil className="h-3.5 w-3.5" /> Open/Edit draft</Link>}
                {canReevaluate && <button type="button" onClick={onReevaluateDraft} disabled={tailoringAction !== null} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-xs font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50">{tailoringAction === "reevaluate" ? "Reevaluating…" : "Reevaluate saved draft"}</button>}
                {canAccept && <button type="button" onClick={onAcceptDraft} disabled={tailoringAction !== null} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-xs font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"><Check className="h-3.5 w-3.5" /> {tailoringAction === "accept" ? "Accepting…" : "Accept draft"}</button>}
                {canDiscard && <button type="button" onClick={onDiscardDraft} disabled={tailoringAction !== null} className="inline-flex items-center gap-1 rounded-md border border-app-danger/30 px-3 py-2 text-xs font-medium text-app-danger hover:bg-app-danger-soft disabled:opacity-50"><XCircle className="h-3.5 w-3.5" /> {tailoringAction === "discard" ? "Discarding…" : "Discard draft"}</button>}
                {isV10 && !canAccept && ownerReview?.state === "current" && <p className="self-center text-xs text-app-ink-3">Reload this application to confirm the current review binding before accepting.</p>}
              </div>
            </div>
          )}
          {sessionStatus === "accepted" && <p className="mt-3 text-xs font-medium text-app-primary" role="status">Draft accepted and linked to this application.</p>}
          {sessionStatus === "rejected" && <p className="mt-3 text-xs text-app-ink-3" role="status">Draft discarded. The application CV was not changed. You can start a new tailoring session.</p>}
          {sessionStatus === "expired" && !draftId && <p className="mt-3 text-xs text-app-ink-3" role="status">This tailoring session expired before a draft was submitted. Start a new session to try again.</p>}
          {sessionStatus === "failed" && <p className="mt-3 text-xs text-app-ink-3" role="status">Tailoring failed. No CV changes were saved. Start a new session to try again.</p>}
        </div>
      )}
      {tailoringResult && !tailoringSession && <div className="mt-4 rounded-md bg-app-primary-soft px-3 py-3 text-xs text-app-ink-2"><p className="font-medium text-app-ink">Tailored draft ready</p><p className="mt-1">Scanner Job Fit: {typeof tailoringResult.scanner_result?.semantic.summary?.job_fit === "number" ? `${Math.round(tailoringResult.scanner_result.semantic.summary.job_fit * 100)}%` : "—"}</p></div>}
      {announcement && <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">{announcement}</p>}
    </section>
  );
}
