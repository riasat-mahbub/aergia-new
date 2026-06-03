import type { EducationEntry } from "../../../lib/sections/types";
import { formatDateRange } from "../../../lib/sections/DateField";

interface Props {
  data: EducationEntry[] | undefined;
}

export default function EducationRenderer({ data = [] }: Props) {
  return (
    <div className="space-y-3">
      {data.map((entry) => (
        <div key={entry.id}>
          <h3 className="font-semibold">{entry.degree}</h3>
          <p className="text-sm text-gray-600">{entry.institution}</p>
          <p className="text-xs text-gray-500">
            {formatDateRange(entry.start_date, entry.end_date, entry.current)}
          </p>
          {entry.gpa && <p className="text-xs text-gray-500">GPA: {entry.gpa}</p>}
        </div>
      ))}
    </div>
  );
}
