import type { Application, RelevanceAnalysis } from "@/features/applications";

export const APPLICATION_RELEVANCE_TOOLTIP =
  "Weighted job-requirement coverage of this CV—not an ATS or hiring probability.";

export function applicationMatchesCv(application: Application | null, cvId: string): boolean {
  return Boolean(application && application.cv_id === cvId);
}

function isRelevanceResult(value: Application["relevance"]): value is RelevanceAnalysis {
  return "score" in value && typeof value.score === "number";
}

export function applicationRelevance(application: Application | null): RelevanceAnalysis | null {
  return application && isRelevanceResult(application.relevance) ? application.relevance : null;
}
