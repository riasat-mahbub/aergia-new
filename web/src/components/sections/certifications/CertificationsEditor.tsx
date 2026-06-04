import type { CertificationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";

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
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        getTitle={(e: any) => e.name || "New Certification"}
      >
        {(entry: any, i: number) => (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500">Name</label>
              <input type="text" value={entry.name} onChange={(e: any) => update(i, "name", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Issuer</label>
              <input type="text" value={entry.issuer} onChange={(e: any) => update(i, "issuer", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <DateField
              value={entry.date}
              onChange={(v) => update(i, "date", v ?? "")}
              label="Date"
            />
            <div>
              <label className="block text-xs text-gray-500">Credential URL</label>
              <input type="text" value={entry.credential_url} onChange={(e: any) => update(i, "credential_url", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
          </div>
        )}
      </SortableAccordionList>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Certification</button>
    </div>
  );
}
