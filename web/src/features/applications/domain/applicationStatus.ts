import type { ApplicationStatus } from "@/features/applications/types";

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
