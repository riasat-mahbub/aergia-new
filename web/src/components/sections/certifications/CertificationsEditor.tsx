import type { CertificationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";

interface Props {
  data: CertificationEntry[] | undefined;
  onChange: (data: CertificationEntry[]) => void;
}

export default function CertificationsEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `cert_${Date.now()}`,
    name: "",
    issuer: "",
    date: "",
    credential_url: "",
  }));

  return (
    <div className="space-y-4">
      {entries.map((entry, i) => (
        <div key={entry.id} className="rounded border p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500">#{i + 1}</span>
            <button onClick={() => remove(i)} className="text-xs text-red-500">Remove</button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500">Name</label>
              <input type="text" value={entry.name} onChange={(e) => update(i, "name", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Issuer</label>
              <input type="text" value={entry.issuer} onChange={(e) => update(i, "issuer", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Date</label>
              <input type="text" value={entry.date} onChange={(e) => update(i, "date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Credential URL</label>
              <input type="text" value={entry.credential_url} onChange={(e) => update(i, "credential_url", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
          </div>
        </div>
      ))}
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Certification</button>
    </div>
  );
}
