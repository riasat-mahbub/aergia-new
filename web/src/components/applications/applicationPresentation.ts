import type { Application, ApplicationStatus } from "../../lib/api/applications";

export const RELEVANCE_TOOLTIP = "Weighted keyword coverage of this CV against the saved job description—not an ATS or hiring probability.";

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  draft: "Draft",
  applied: "Applied",
  responded: "Responded",
  interview: "Interview",
  offer: "Offer",
  hired: "Hired",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export const STATUS_CLASSES: Record<ApplicationStatus, string> = {
  draft: "bg-app-surface-muted text-app-ink-2",
  applied: "bg-app-primary-soft text-app-primary",
  responded: "bg-app-secondary-soft text-app-secondary",
  interview: "bg-app-secondary-soft text-app-secondary",
  offer: "bg-app-warning-soft text-app-warning",
  hired: "bg-app-primary-soft text-app-primary",
  rejected: "bg-app-danger-soft text-app-danger",
  withdrawn: "bg-app-surface-muted text-app-ink-3",
};

export const STATUS_STRIP_CLASSES: Record<ApplicationStatus, string> = {
  draft: "bg-app-ink-3",
  applied: "bg-app-primary",
  responded: "bg-app-secondary",
  interview: "bg-app-secondary",
  offer: "bg-app-warning",
  hired: "bg-app-primary",
  rejected: "bg-app-danger",
  withdrawn: "bg-app-ink-muted",
};

export function relevanceScore(relevance: Application["relevance"]): number | null {
  if ("score" in relevance && typeof relevance.score === "number") return relevance.score;
  return null;
}

export function formatApplicationDate(value: string | null): string {
  if (!value) return "Not applied";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
