import { Link } from "@tanstack/react-router";
import { Check, Copy, Download, ExternalLink, Pencil, RefreshCw, XCircle } from "lucide-react";
import type { Application } from "@/features/applications/types";
import type { CVDetail } from "@/features/cvs";
import { safeExternalUrl } from "@/shared/security/safeUrl";
import type {
  TailoringSession,
  TailoringSessionResult,
  TailoringSessionStatusResponse,
} from "@/features/tailoring";
import {
  isQualityResult,
  relevanceScoreFromSnapshot,
} from "../../domain/detail/applicationDetail";
import { isTerminalTailoringStatus, sessionStatusLabel } from "@/features/tailoring";

interface GeneratedCvPanelProps {
  application: Application;
  linkedCV: CVDetail | null;
  sections: string[];
  sourceCount: number | null;
  tailoringSession: TailoringSession | null;
  tailoringStarting: boolean;
  tailoringStatus: TailoringSessionStatusResponse | null;
  tailoringResult: TailoringSessionResult | null;
  promptCopied: boolean;
  retrying: boolean;
  onExport: () => void;
  onRetry: () => void;
  onStartTailoring: () => void;
  onCopyPrompt: () => void;
  onCancelTailoring: () => void;
}

export default function GeneratedCvPanel({
  application,
  linkedCV,
  sections,
  sourceCount,
  tailoringSession,
  tailoringStarting,
  tailoringStatus,
  tailoringResult,
  promptCopied,
  retrying,
  onExport,
  onRetry,
  onStartTailoring,
  onCopyPrompt,
  onCancelTailoring,
}: GeneratedCvPanelProps) {
  const safeTailoringSessionUrl = tailoringSession ? safeExternalUrl(tailoringSession.session_url) : null;

  return (
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
            <Link to="/builder/$id" params={{ id: application.cv_id }} search={{ application: application.id }} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-sm font-medium text-white hover:bg-app-primary-hover">Open/Edit CV <Pencil className="h-3.5 w-3.5" /></Link>
            <button type="button" onClick={onExport} className="inline-flex items-center gap-1 rounded-md border border-app-rule-strong px-3 py-2 text-sm font-medium text-app-ink-2 hover:bg-app-surface-muted"><Download className="h-3.5 w-3.5" /> Export PDF</button>
            <button type="button" onClick={onStartTailoring} disabled={tailoringStarting} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50">
              {tailoringStarting ? "Preparing LLM tailoring…" : "LLM Tailoring"}
            </button>
          </div>
          <p className="mt-3 text-xs text-app-ink-3">Your installed coding agent composes a fresh CV locally from the full Library and profile. It may reorganize sections when it explains and cites the decision; you remain the final reviewer. The current CV remains unchanged as optional source evidence.</p>
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
                  <button type="button" onClick={onCancelTailoring} className="inline-flex items-center gap-1 text-xs font-medium text-app-danger hover:underline">
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
                <button type="button" onClick={onCopyPrompt} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover">
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
          {tailoringResult && (
            <div className="mt-4 rounded-md bg-app-primary-soft px-3 py-3 text-xs text-app-ink-2" role="status">
              <p className="font-medium text-app-ink">Tailored CV ready</p>
              <p className="mt-1">
                Relevance: {relevanceScoreFromSnapshot(tailoringResult.before_relevance) ?? "—"}% → {relevanceScoreFromSnapshot(tailoringResult.relevance) ?? "—"}%
              </p>
              {tailoringResult.gaps.length > 0 && <p className="mt-1">Remaining gaps: {tailoringResult.gaps.map((gap) => gap.requirement).join(", ")}</p>}
              <p className="mt-1 text-app-ink-3">Requirement feedback is available in the linked CV&apos;s relevance details.</p>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="mt-2 text-sm text-app-ink-2">{application.generation_status === "failed" ? "CV generation failed. Please retry." : "Generation is pending."}</p>
          <button type="button" onClick={onRetry} disabled={retrying} className="mt-4 inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${retrying ? "animate-spin" : ""}`} /> {retrying ? "Generating…" : "Retry generation"}</button>
        </>
      )}
    </section>
  );
}
