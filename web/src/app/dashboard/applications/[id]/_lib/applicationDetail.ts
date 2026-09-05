import type {
  Application,
  CVQualityResult,
  RelevanceAnalysis,
} from "@/contracts/applications";
import type { CVDetail } from "@/contracts/cvs";

export function isRelevanceResult(value: Application["relevance"]): value is RelevanceAnalysis {
  return "score" in value && typeof value.score === "number";
}

export function isQualityResult(value: Application["quality"]): value is CVQualityResult {
  return Boolean(value && "status" in value && "issues" in value && Array.isArray(value.issues));
}

export function sectionTypes(cv: CVDetail | null): string[] {
  if (!cv || !Array.isArray(cv.sections)) return [];
  return cv.sections.flatMap((section) => {
    if (typeof section !== "object" || section === null || !("type" in section)) return [];
    return typeof section.type === "string" ? [section.type] : [];
  });
}

export function selectedSourceCount(cv: CVDetail | null): number | null {
  if (!cv || typeof cv.extra_metadata !== "object" || cv.extra_metadata === null) return null;
  if (!("selected_sources" in cv.extra_metadata)) return null;
  const sources = cv.extra_metadata.selected_sources;
  return Array.isArray(sources) ? sources.length : null;
}

export function relevanceScoreFromSnapshot(value: Record<string, unknown> | null | undefined): number | null {
  const score = value?.score;
  return typeof score === "number" ? score : null;
}
