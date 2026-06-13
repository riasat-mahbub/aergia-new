import type { ProjectEntry } from "../../../lib/sections/types";
import { formatDateRange } from "../../../lib/sections/DateField";

interface Props {
  data: ProjectEntry[] | undefined;
}

export default function ProjectsRenderer({ data = [] }: Props) {
  return (
    <div className="space-y-3">
      {data.map((entry) => (
        <div key={entry.id}>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold">{entry.name}</h3>
              {entry.url && (
                <span className="text-xs text-blue-600 underline">
                  {entry.link_text || entry.url}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              {formatDateRange(entry.start_date, entry.end_date, false)}
            </p>
          </div>
          {entry.description && <p className="mt-1 text-sm text-gray-700">{entry.description}</p>}
          {entry.tech_stack.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {entry.tech_stack.map((tech, i) => (
                <span key={i} className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">{tech}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
