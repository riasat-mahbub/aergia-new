import { useEffect } from "react";
import { X } from "lucide-react";
import type { RequirementRelevanceResult, RelevanceAnalysis, RelevanceResult } from "../../lib/api/applications";

interface RelevanceDrawerProps {
  open: boolean;
  relevance: RelevanceAnalysis | null;
  onClose: () => void;
  refreshing?: boolean;
  refreshError?: boolean;
}

function isRequirementAnalysis(value: RelevanceAnalysis): value is RequirementRelevanceResult {
  return "requirements" in value && Array.isArray(value.requirements);
}

function LegacyRelevance({ relevance }: { relevance: RelevanceResult }) {
  return (
    <div className="space-y-6 py-6">
      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Matched keywords</h3>
        {relevance.matched_keywords.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {relevance.matched_keywords.map((keyword) => <span key={keyword} className="rounded-full bg-app-primary-soft px-2.5 py-1 text-xs text-app-primary">{keyword}</span>)}
          </div>
        ) : <p className="mt-2 text-sm text-app-ink-2">No matched keywords.</p>}
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Missing keywords</h3>
        {relevance.missing_keywords.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {relevance.missing_keywords.map((keyword) => <span key={keyword} className="rounded-full bg-app-surface-muted px-2.5 py-1 text-xs text-app-ink-2">{keyword}</span>)}
          </div>
        ) : <p className="mt-2 text-sm text-app-ink-2">No missing keywords.</p>}
      </section>

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Source evidence</h3>
        {relevance.evidence.length > 0 ? (
          <div className="mt-3 space-y-3">
            {relevance.evidence.map((item, index) => (
              <div key={`${item.keyword}-${item.field_path}-${index}`} className="rounded-md bg-app-canvas px-3 py-3 text-xs text-app-ink-2">
                <p><strong className="text-app-ink">{item.keyword}</strong> · {item.section_type}</p>
                <p className="mt-1 text-app-ink-3">{item.field_path}</p>
                <p className="mt-1 text-app-ink-3">Source: {item.source_row_id ?? item.library_entry_id ?? "CV content"}</p>
                <p className="mt-2 leading-5">{item.snippet}</p>
              </div>
            ))}
          </div>
        ) : <p className="mt-2 text-sm text-app-ink-2">No source evidence is available.</p>}
      </section>
    </div>
  );
}

function RequirementRelevance({ relevance }: { relevance: RequirementRelevanceResult }) {
  if (relevance.status === "not_evaluated") {
    return <p className="py-6 text-sm text-app-ink-2">Generate the CV before relevance is evaluated. Later Builder edits update this analysis without rebuilding the CV.</p>;
  }
  return (
    <div className="space-y-4 py-6">
      <div className="rounded-md bg-app-canvas px-3 py-3 text-sm text-app-ink-2">
        <p><strong className="text-app-ink">{relevance.score ?? "—"}%</strong> weighted relevance · <strong className="text-app-ink">{relevance.coverage_score ?? "—"}%</strong> requirement coverage</p>
        <p><strong className="text-app-ink">{relevance.covered_requirements}</strong> of <strong className="text-app-ink">{relevance.total_requirements}</strong> requirements covered</p>
        <p className="mt-1 text-xs text-app-ink-3">Required: {relevance.required_score ?? "—"}% · Preferred: {relevance.preferred_score ?? "—"}%</p>
      </div>
      {relevance.requirements.map((match) => (
        <article key={match.requirement.id} className="rounded-md border border-app-rule-soft bg-app-surface px-3 py-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <p className="font-medium text-app-ink">{match.requirement.text}</p>
            <span className={match.covered ? "shrink-0 text-xs font-medium text-app-primary" : match.score > 0 ? "shrink-0 text-xs font-medium text-app-ink-2" : "shrink-0 text-xs font-medium text-app-ink-3"}>
              {match.covered ? `${Math.round(match.score * 100)}% covered` : match.score > 0 ? `${Math.round(match.score * 100)}% partial` : "Missing"}
            </span>
          </div>
          <p className="mt-1 text-xs text-app-ink-3">{match.requirement.required ? "Required" : "Preferred"} · {match.requirement.type.replace("_", " ")}</p>
          {match.best_evidence ? (
            <div className="mt-3 rounded bg-app-canvas px-2.5 py-2 text-xs text-app-ink-2">
              <p>{match.best_evidence.section_type} · {match.best_evidence.field_path} · {match.best_evidence.method}</p>
              <p className="mt-1 leading-5">{match.best_evidence.snippet}</p>
            </div>
          ) : <p className="mt-3 text-xs text-app-ink-3">No supporting CV evidence.</p>}
        </article>
      ))}
    </div>
  );
}

export default function RelevanceDrawer({ open, relevance, onClose, refreshing = false, refreshError = false }: RelevanceDrawerProps) {
  useEffect(() => {
    if (!open) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="presentation">
      <button
        type="button"
        aria-label="Dismiss relevance details"
        className="absolute inset-0 h-full w-full cursor-default bg-black/25"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="relevance-drawer-title"
        className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col overflow-y-auto bg-app-surface p-6 shadow-xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-app-rule-soft pb-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-app-primary">Application analysis</p>
            <h2 id="relevance-drawer-title" className="mt-1 text-xl font-semibold text-app-ink">Relevance details</h2>
            <p className="mt-1 text-sm text-app-ink-2">Deterministic requirement coverage and the strongest CV evidence for each requirement.</p>
            {refreshing && <p className="mt-2 text-xs text-app-primary" role="status">Updating relevance…</p>}
            {refreshError && <p className="mt-2 text-xs text-app-danger" role="alert">Could not update relevance. Your saved CV is unchanged.</p>}
          </div>
          <button type="button" aria-label="Close relevance details" onClick={onClose} className="rounded-md p-1.5 text-app-ink-3 hover:bg-app-surface-muted hover:text-app-ink">
            <X className="h-5 w-5" />
          </button>
        </header>

        {!relevance ? (
          <p className="mt-6 text-sm text-app-ink-2">Relevance has not been calculated yet.</p>
        ) : (
          isRequirementAnalysis(relevance) ? <RequirementRelevance relevance={relevance} /> : <LegacyRelevance relevance={relevance} />
        )}
      </aside>
    </div>
  );
}
