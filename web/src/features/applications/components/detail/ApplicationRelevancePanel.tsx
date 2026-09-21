import { Link } from "@tanstack/react-router";
import type { Application, RelevanceAnalysis } from "@/features/applications/types";
import { RELEVANCE_TOOLTIP } from "../../domain/list/applicationPresentation";

interface ApplicationRelevancePanelProps {
  application: Application;
  relevance: RelevanceAnalysis | null;
}

export default function ApplicationRelevancePanel({ application, relevance }: ApplicationRelevancePanelProps) {
  return (
    <section className="flex flex-col overflow-hidden rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
      <div className="relative min-h-0 flex-1 overflow-hidden">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Current relevance (legacy)</h2>
            <p className="mt-2 text-3xl font-semibold text-app-ink" title={RELEVANCE_TOOLTIP}>{relevance ? `${relevance.score}%` : "—"}</p>
            {relevance && "ai_relevance" in relevance && relevance.ai_relevance && (
              <p className="mt-1 text-sm text-app-primary">AI fit: {relevance.ai_relevance.score}%</p>
            )}
          </div>
        </div>
        <p className="mt-3 text-xs text-app-ink-3">{RELEVANCE_TOOLTIP}</p>
        {application.cv_id && <Link to="/builder/$id" params={{ id: application.cv_id }} search={{ application: application.id }} className="mt-4 inline-flex text-sm font-medium text-app-primary hover:text-app-primary-hover">Open the linked CV to inspect matched, missing, and source evidence</Link>}
      </div>
    </section>
  );
}
