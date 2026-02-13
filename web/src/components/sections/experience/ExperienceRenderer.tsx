import type { ExperienceEntry } from "../../../lib/sections/types";

interface Props {
  data: ExperienceEntry[] | undefined;
}

export default function ExperienceRenderer({ data = [] }: Props) {
  return (
    <div className="space-y-4">
      {data.map((entry) => (
        <div key={entry.id}>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold">{entry.position}</h3>
              <p className="text-sm text-gray-600">{entry.company}{entry.location ? `, ${entry.location}` : ""}</p>
            </div>
            <p className="text-xs text-gray-500">
              {entry.start_date} – {entry.current ? "Present" : entry.end_date}
            </p>
          </div>
          {entry.description && <p className="mt-1 text-sm text-gray-700">{entry.description}</p>}
        </div>
      ))}
    </div>
  );
}
