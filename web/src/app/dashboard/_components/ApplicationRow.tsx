import { Link } from "react-router-dom";
import type { Application } from "@/contracts/applications";
import { STATUS_CLASSES, STATUS_LABELS } from "../_constants/applicationStatus";

export default function ApplicationRow({ application }: { application: Application }) {
  return (
    <Link
      to={`/dashboard/applications/${application.id}`}
      className="flex items-center justify-between gap-4 rounded-lg px-3 py-3 transition hover:bg-app-surface-muted"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-app-ink">{application.company}</p>
        <p className="mt-0.5 truncate text-xs text-app-ink-3">{application.role}</p>
      </div>
      <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[application.status]}`}>
        {STATUS_LABELS[application.status]}
      </span>
    </Link>
  );
}
