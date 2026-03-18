import type { EducationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";

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
    current: false,
    gpa: "",
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        getTitle={(e: any) => e.degree || e.institution || "New Education"}
      >
        {(entry: any, i: number) => (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500">Institution</label>
              <input type="text" value={entry.institution} onChange={(e: any) => update(i, "institution", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Degree</label>
              <input type="text" value={entry.degree} onChange={(e: any) => update(i, "degree", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Start Date</label>
              <input type="text" value={entry.start_date} onChange={(e: any) => update(i, "start_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">End Date</label>
              <input type="text" value={entry.end_date || ""} onChange={(e: any) => update(i, "end_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" disabled={entry.current} />
            </div>
            <div>
              <label className="block text-xs text-gray-500">GPA</label>
              <input type="text" value={entry.gpa} onChange={(e: any) => update(i, "gpa", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={entry.current} onChange={(e: any) => update(i, "current", e.target.checked)} />
              Currently enrolled
            </label>
          </div>
        )}
      </SortableAccordionList>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Education</button>
    </div>
  );
}
