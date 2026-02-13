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
          <p className="text-xs text-gray-600">{entry.issuer}{entry.date ? ` · ${entry.date}` : ""}</p>
          {entry.credential_url && (
            <a href={entry.credential_url} className="text-xs text-blue-600 hover:underline">Credential</a>
          )}
        </div>
      ))}
    </div>
  );
}
