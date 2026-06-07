import type { CertificationEntry } from "../../../lib/sections/types";

interface Props {
  data: CertificationEntry[] | undefined;
}

export default function CertificationsRenderer({ data = [] }: Props) {
  return (
    <div className="space-y-2">
      {data.map((entry) => (
        <div key={entry.id}>
          <h3 className="text-sm font-semibold">{entry.name}</h3>
          {entry.credential_url && (
            <span className="text-xs text-blue-600 underline">Credential</span>
          )}
        </div>
      ))}
    </div>
  );
}
