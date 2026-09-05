import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import type { Application } from "@/features/applications/types";
import { safeExternalUrl } from "@/shared/security/safeUrl";

export default function ApplicationJobPanel({ application }: { application: Application }) {
  const [expanded, setExpanded] = useState(false);
  const safeJobUrl = safeExternalUrl(application.job_url);

  return (
    <section className={`flex flex-col overflow-hidden rounded-lg border border-app-rule bg-app-surface p-5 shadow-sm ${expanded ? "" : "h-60 md:h-64"}`}>
      <div id="application-job-details" className="relative min-h-0 flex-1 overflow-hidden">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-app-ink-3">Job</h2>
        <div className="mt-4 whitespace-pre-wrap text-sm leading-6 text-app-ink-2">{application.job_description}</div>
        {safeJobUrl && <a href={safeJobUrl} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex items-center gap-1 text-sm text-app-primary hover:underline">Open job listing <ExternalLink className="h-3.5 w-3.5" /></a>}
        {application.notes && <p className="mt-4 border-t border-app-rule-soft pt-4 text-sm text-app-ink-2">{application.notes}</p>}
        {!expanded && <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-app-surface to-transparent" />}
      </div>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls="application-job-details"
        onClick={() => setExpanded((current) => !current)}
        className="mt-3 inline-flex shrink-0 items-center gap-1 self-start text-sm font-medium text-app-primary hover:text-app-primary-hover"
      >
        {expanded ? "See less" : "See more"}
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
    </section>
  );
}
