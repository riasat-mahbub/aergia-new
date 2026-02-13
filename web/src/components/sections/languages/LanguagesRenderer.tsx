import type { LanguageEntry } from "../../../lib/sections/types";

interface Props {
  data: LanguageEntry[] | undefined;
}

export default function LanguagesRenderer({ data = [] }: Props) {
  return (
    <div className="space-y-1">
      {data.map((entry) => (
        <div key={entry.id} className="flex items-center justify-between text-sm">
          <span>{entry.language}</span>
          <span className="text-xs text-gray-500">{entry.proficiency}</span>
        </div>
      ))}
    </div>
  );
}
