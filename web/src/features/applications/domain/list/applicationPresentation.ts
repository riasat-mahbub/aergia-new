import type { Application } from "@/features/applications/types";

export const JOB_FIT_TOOLTIP = "How well the evidence in this CV supports the job's requirements.";

export function scannerJobFitScore(application: Application): number | null {
  const score = application.scanner_result?.semantic.summary?.job_fit;
  return typeof score === "number" && application.scanner_status !== "stale" && application.scanner_status !== "needs_rescan" ? score : null;
}

export function formatApplicationDate(value: string | null): string {
  if (!value) return "Not applied";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}

function parseDateValue(value: string | null | undefined): Date | null {
  if (!value) return null;
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) return new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]));
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function localDayStart(value = new Date()): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

export function formatFollowUpDate(value: string | null | undefined): string {
  const date = parseDateValue(value);
  return date ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date) : "No follow-up set";
}

export function isFollowUpOverdue(value: string | null | undefined, now = new Date()): boolean {
  const date = parseDateValue(value);
  return Boolean(date && date < localDayStart(now));
}

export function isFollowUpToday(value: string | null | undefined, now = new Date()): boolean {
  const date = parseDateValue(value);
  if (!date) return false;
  const today = localDayStart(now);
  return date.getTime() === today.getTime();
}

export function isFollowUpUpcoming(value: string | null | undefined, now = new Date()): boolean {
  const date = parseDateValue(value);
  return Boolean(date && date > localDayStart(now));
}

function applicationDate(application: Application): Date | null {
  return parseDateValue(application.applied_at) ?? parseDateValue(application.created_at);
}

function dateFromQuery(value: string): Date | null {
  if (value === "today") return localDayStart();
  return parseDateValue(value);
}

function matchesJobFit(application: Application, expression: string): boolean {
  const score = scannerJobFitScore(application);
  if (score === null) return false;
  const match = /^(>=|<=|>|<|=)?(\d{1,3})$/.exec(expression);
  if (!match) return false;
  const target = Number(match[2]);
  switch (match[1] ?? "=") {
    case ">": return score > target;
    case ">=": return score >= target;
    case "<": return score < target;
    case "<=": return score <= target;
    default: return score === target;
  }
}

function matchesFollowUp(application: Application, expression: string): boolean {
  const value = application.next_follow_up_at;
  switch (expression.toLowerCase()) {
    case "none": return !value;
    case "overdue": return isFollowUpOverdue(value);
    case "today": return isFollowUpToday(value);
    case "upcoming": return isFollowUpUpcoming(value);
    default: return value === expression;
  }
}

/** Match free text plus documented field operators in the applications search bar. */
export function applicationMatchesSearch(application: Application, query: string): boolean {
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return true;
  const searchable = [application.company, application.role, application.job_description, application.notes ?? ""]
    .join(" ")
    .toLowerCase();
  const date = applicationDate(application);

  return terms.every((term) => {
    const separator = term.indexOf(":");
    if (separator < 1) return searchable.includes(term);
    const field = term.slice(0, separator);
    const value = term.slice(separator + 1);
    if (!value) return false;
    if (field === "company" || field === "role" || field === "status") {
      const fieldValue = field === "company" ? application.company : field === "role" ? application.role : application.status;
      return fieldValue.toLowerCase().includes(value);
    }
    if (field === "jobfit" || field === "job-fit") return matchesJobFit(application, value);
    if (field === "followup" || field === "follow-up") return matchesFollowUp(application, value);
    if (field === "date" || field === "after" || field === "before") {
      const target = dateFromQuery(value);
      if (!date || !target) return false;
      const day = localDayStart(date).getTime();
      const targetDay = target.getTime();
      if (field === "after") return day >= targetDay;
      if (field === "before") return day <= targetDay;
      return day === targetDay;
    }
    return searchable.includes(term);
  });
}
