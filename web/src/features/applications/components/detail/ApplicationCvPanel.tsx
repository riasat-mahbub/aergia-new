import { Link } from "@tanstack/react-router";
import { Check, Copy, Download, ExternalLink, Pencil, XCircle } from "lucide-react";
import type { Application } from "@/features/applications/types";
import type { CVDetail } from "@/features/cvs";
import type { TailoringSession, TailoringSessionResult, TailoringSessionStatusResponse } from "@/features/tailoring";
import { safeExternalUrl } from "@/shared/security/safeUrl";
import { relevanceScoreFromSnapshot } from "../../domain/detail/applicationDetail";
import { isTerminalTailoringStatus, sessionStatusLabel } from "@/features/tailoring";

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
  onExport: () => void;
  onStartTailoring: () => void;
  onCopyPrompt: () => void;
  onCancelTailoring: () => void;
  onAcceptDraft: () => void;
  onRejectDraft: () => void;
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
  onExport,
  onStartTailoring,
  onCopyPrompt,
  onCancelTailoring,
  onAcceptDraft,
  onRejectDraft,
}: ApplicationCvPanelProps) {
  const safeTailoringSessionUrl = tailoringSession ? safeExternalUrl(tailoringSession.session_url) : null;
  const safeTailoringSkillUrl = tailoringSession ? safeExternalUrl(tailoringSession.skill_url) : null;
  const result = tailoringStatus?.result ?? tailoringResult;
  const draftReady = tailoringStatus?.status === "draft_ready" && result?.draft_cv_id;
  const activeSessionStatus = tailoringStatus?.status ?? tailoringSession?.status;
  const tailoringBlocksNewSession = activeSessionStatus === "created" || activeSessionStatus === "exchanged" || activeSessionStatus === "draft_ready";

  return (
    <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Linked CV and tailoring</h2>
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
        <p className="mt-2 text-sm text-app-ink-2">No CV is linked yet. Link an existing CV in Scanner analysis or start LLM tailoring to create a draft.</p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onStartTailoring} disabled={tailoringStarting || tailoringBlocksNewSession} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-sm font-medium text-app-primary hover:bg-app-primary-soft disabled:opacity-50">
          {tailoringStarting ? "Preparing LLM tailoring…" : tailoringBlocksNewSession ? "Finish current tailoring first" : "LLM Tailoring"}
        </button>
      </div>
      <p className="mt-3 text-xs text-app-ink-3">Your coding agent composes a complete CV and may change content, sections, template, layout, and styles. The current CV stays unchanged until you review the draft.</p>

      {tailoringSession && (
        <div className="mt-4 rounded-md bg-app-canvas px-3 py-3" role="status">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-app-ink">Use your coding agent</p>
              <p className="mt-1 text-xs text-app-ink-3">{sessionStatusLabel(tailoringStatus?.status ?? tailoringSession.status)}{tailoringStatus?.status === "draft_ready" ? " · ready for review" : ` · agent access expires ${new Date(tailoringSession.expires_at).toLocaleTimeString()}`}</p>
            </div>
            {!isTerminalTailoringStatus(tailoringStatus?.status) && <button type="button" onClick={onCancelTailoring} className="inline-flex items-center gap-1 text-xs font-medium text-app-danger hover:underline"><XCircle className="h-3.5 w-3.5" /> Cancel</button>}
          </div>
          {tailoringStatus?.status !== "draft_ready" && tailoringStatus?.status !== "accepted" && tailoringStatus?.status !== "rejected" && <>
            <p className="mt-3 text-xs text-app-ink-2">Copy this prompt and paste it into Codex, Claude Code, or OpenCode.</p>
            <textarea aria-label="Aergia tailoring prompt" readOnly value={tailoringSession.prompt} rows={6} className="mt-2 block w-full resize-y rounded border border-app-rule-strong bg-app-surface px-2 py-2 text-xs leading-5 text-app-ink-2" />
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <button type="button" onClick={onCopyPrompt} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover">{promptCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}{promptCopied ? "Copied" : "Copy prompt"}</button>
              {safeTailoringSessionUrl && <a href={safeTailoringSessionUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-medium text-app-primary hover:underline">Open session link <ExternalLink className="h-3.5 w-3.5" /></a>}
              {safeTailoringSkillUrl && <a href={safeTailoringSkillUrl} className="inline-flex items-center gap-1 text-xs font-medium text-app-primary hover:underline" download>Install tailoring skill <Download className="h-3.5 w-3.5" /></a>}
            </div>
          </>}
          {draftReady && result && (
            <div className="mt-3 border-t border-app-rule-soft pt-3 text-xs text-app-ink-2">
              <p className="font-medium text-app-ink">Draft ready for your review</p>
              <p className="mt-1">Legacy relevance snapshot: {relevanceScoreFromSnapshot(result.relevance) ?? "—"}%</p>
              {result.warnings.length > 0 && <p className="mt-1">Document checks: {result.warnings.join(" ")}</p>}
              {(result.review_notes ?? []).length > 0 && <div className="mt-2"><p className="font-medium">Agent notes</p><ul className="mt-1 list-disc pl-4">{result.review_notes?.map((note, index) => <li key={`${index}-${note.slice(0, 32)}`}>{note}</li>)}</ul></div>}
              <div className="mt-3 flex flex-wrap gap-2">
                <Link to="/builder/$id" params={{ id: result.draft_cv_id }} search={{ application: application.id }} className="inline-flex items-center gap-1 rounded-md bg-app-primary px-3 py-2 text-xs font-medium text-white hover:bg-app-primary-hover"><Pencil className="h-3.5 w-3.5" /> Open/Edit draft</Link>
                <button type="button" onClick={onAcceptDraft} className="inline-flex items-center gap-1 rounded-md border border-app-primary-soft px-3 py-2 text-xs font-medium text-app-primary hover:bg-app-primary-soft"><Check className="h-3.5 w-3.5" /> Accept draft</button>
                <button type="button" onClick={onRejectDraft} className="inline-flex items-center gap-1 rounded-md border border-app-danger/30 px-3 py-2 text-xs font-medium text-app-danger hover:bg-app-danger-soft"><XCircle className="h-3.5 w-3.5" /> Reject draft</button>
              </div>
            </div>
          )}
          {tailoringStatus?.status === "accepted" && <p className="mt-3 text-xs font-medium text-app-primary">Draft accepted and linked to this application.</p>}
          {tailoringStatus?.status === "rejected" && <p className="mt-3 text-xs text-app-ink-3">Draft rejected and removed. The application CV was not changed.</p>}
        </div>
      )}
      {tailoringResult && !tailoringSession && <div className="mt-4 rounded-md bg-app-primary-soft px-3 py-3 text-xs text-app-ink-2"><p className="font-medium text-app-ink">Tailored draft ready</p><p className="mt-1">Legacy relevance snapshot: {relevanceScoreFromSnapshot(tailoringResult.relevance) ?? "—"}%</p></div>}
    </section>
  );
}
