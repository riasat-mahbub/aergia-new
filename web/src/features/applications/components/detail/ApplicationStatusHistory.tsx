import type { Application } from "@/features/applications/types";
import { formatFollowUpDate } from "../../domain/list/applicationPresentation";
import { STATUS_LABELS } from "../../domain/applicationStatus";

export default function ApplicationStatusHistory({ application }: { application: Application }) {
  const history = application.status_history ?? [];
  return (
    <section className="mt-4 rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Status history</h2>
      {history.length > 0 ? (
        <ol className="mt-4 space-y-3 border-l border-app-rule pl-4">
          {history.map((event) => (
            <li key={event.id} className="relative text-sm text-app-ink-2">
              <span className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-app-primary" />
              <span className="font-medium text-app-ink">{event.from_status ? `${STATUS_LABELS[event.from_status]} → ` : "Started as "}{STATUS_LABELS[event.to_status]}</span>
              <span className="ml-2 text-xs text-app-ink-3">{formatFollowUpDate(event.changed_at.slice(0, 10))}</span>
            </li>
          ))}
        </ol>
      ) : <p className="mt-2 text-sm text-app-ink-2">No status changes recorded yet.</p>}
    </section>
  );
}
