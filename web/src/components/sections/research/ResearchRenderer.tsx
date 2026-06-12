import type { ResearchEntry } from "../../../lib/sections/types";
import { ExternalLink } from "lucide-react";

interface Props {
  data: ResearchEntry[] | undefined;
}

export default function ResearchRenderer({ data = [] }: Props) {
  return (
    <div className="space-y-3">
      {data.map((entry) => {
        const label = entry.paper_link_text.trim() || "Paper";
        return (
          <article
            key={entry.id}
            className="border-l-2 border-blue-200 pl-3"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-semibold">{entry.title}</h3>
              {entry.paper_url && (
                <a
                  href={entry.paper_url}
                  target="_blank"
                  rel="noreferrer"
                  className="shrink-0 text-xs font-medium text-blue-700 underline decoration-blue-300 underline-offset-2"
                >
                  {label}
                  <ExternalLink aria-hidden="true" className="ml-0.5 inline h-3 w-3" />
                </a>
              )}
            </div>
            {entry.publication_date && (
              <p className="mt-0.5 text-xs text-gray-500">
                Published {entry.publication_date}
              </p>
            )}
            {entry.description && (
              <p className="mt-1.5 text-sm text-gray-700">{entry.description}</p>
            )}
          </article>
        );
      })}
    </div>
  );
}
