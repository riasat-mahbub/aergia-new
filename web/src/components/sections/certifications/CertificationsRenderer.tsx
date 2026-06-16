import type { CertificationEntry, SectionStyle } from "../../../lib/sections/types";
import { formatSingleDate } from "../../../lib/sections/DateField";

interface Props {
  data: CertificationEntry[] | undefined;
  style?: SectionStyle;
}

export default function CertificationsRenderer({ data = [], style }: Props) {
  return (
    <div className="space-y-2">
      {data.map((entry) => {
        const formattedDate = formatSingleDate(entry.date, style?.date_style ?? null);
        return (
          <div key={entry.id}>
            <h3 className="text-sm font-semibold">{entry.name}</h3>
            {entry.credential_url && (
              <span className="text-xs text-blue-600 underline">Credential</span>
            )}
            {formattedDate && (
              <p className="mt-1 text-xs text-gray-500">{formattedDate}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
