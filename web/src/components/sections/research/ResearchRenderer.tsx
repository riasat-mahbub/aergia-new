import type { ResearchEntry, SectionStyle } from "../../../lib/sections/types";
import { formatSingleDate } from "../../../lib/sections/DateField";
import { ExternalLink } from "lucide-react";

interface Props {
  data: ResearchEntry[] | undefined;
  style?: SectionStyle;
}

export default function ResearchRenderer({ data = [], style }: Props) {
  return (
    <div className="space-y-3">
      {data.map((entry) => {
        const label = entry.paper_link_text.trim() || "Paper";
        const formattedDate = formatSingleDate(entry.publication_date, style?.date_style ?? null);
        return (
          <article key={entry.id}>
            <div className="flex items-start justify-between gap-2.5">
              <div>
                <h3 className="font-semibold">{entry.title}</h3>
                {entry.publication_value && (
                  <p className="mt-0.5 text-xs text-gray-500">{entry.publication_value}</p>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-0.5">
                {entry.paper_url && (
                  <a
                    href={entry.paper_url}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 whitespace-nowrap text-xs font-medium text-blue-700 underline decoration-blue-300 underline-offset-2"
                  >
                    {label}
                    <ExternalLink aria-hidden="true" className="ml-0.5 inline h-3 w-3" />
                  </a>
                )}
                {formattedDate && (
                  <p className="whitespace-nowrap text-xs text-gray-500">{formattedDate}</p>
                )}
              </div>
            </div>
            {entry.description && (
              <p className="mt-1.5 text-sm text-gray-700">{entry.description}</p>
            )}
          </article>
        );
      })}
    </div>
  );
}
