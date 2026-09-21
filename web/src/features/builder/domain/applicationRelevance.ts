import type { Application } from "@/features/applications";

export function applicationMatchesCv(application: Application | null, cvId: string): boolean {
  return Boolean(application && application.cv_id === cvId);
}
