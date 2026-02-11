import type { EducationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";

interface Props {
  data: EducationEntry[] | undefined;
  onChange: (data: EducationEntry[]) => void;
}

export default function EducationEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `edu_${Date.now()}`,
    institution: "",
    degree: "",
    start_date: "",
    end_date: null,
    gpa: "",
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
              <label className="block text-xs text-gray-500">Institution</label>
              <input type="text" value={entry.institution} onChange={(e) => update(i, "institution", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Degree</label>
              <input type="text" value={entry.degree} onChange={(e) => update(i, "degree", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Start Date</label>
              <input type="text" value={entry.start_date} onChange={(e) => update(i, "start_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">End Date</label>
              <input type="text" value={entry.end_date || ""} onChange={(e) => update(i, "end_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">GPA</label>
              <input type="text" value={entry.gpa} onChange={(e) => update(i, "gpa", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
          </div>
        </div>
      ))}
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Education</button>
    </div>
  );
}
