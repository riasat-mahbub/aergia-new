import type { ProjectEntry, SectionStyle } from "../../../lib/sections/types";
import { formatDateRange } from "../../../lib/sections/DateField";
import { ExternalLink } from "lucide-react";

interface Props {
  data: ProjectEntry[] | undefined;
  style?: SectionStyle;
}

export default function ProjectsRenderer({ data = [], style }: Props) {
  return (
    <div className="space-y-3">
      {data.map((entry) => (
        <div key={entry.id}>
          <div className="flex items-start justify-between gap-2.5">
            <div>
              <h3 className="font-semibold">{entry.name}</h3>
              {entry.description && <p className="mt-1 text-sm text-gray-700">{entry.description}</p>}
              {entry.tech_stack.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {entry.tech_stack.map((tech, i) => (
                    <span key={i} className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">{tech}</span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex shrink-0 flex-col items-end gap-0.5">
              {entry.url && (
                <a
                  href={entry.url}
                  target="_blank"
                  rel="noreferrer"
                  className="shrink-0 whitespace-nowrap text-xs font-medium text-blue-700 underline decoration-blue-300 underline-offset-2"
                >
                  {entry.link_text || entry.url}
                  <ExternalLink aria-hidden="true" className="ml-0.5 inline h-3 w-3" />
                </a>
              )}
              <p className="whitespace-nowrap text-xs text-gray-500">
                {formatDateRange(entry.start_date, entry.end_date, false, style?.date_style ?? null)}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
