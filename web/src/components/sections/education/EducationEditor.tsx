import type { EducationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";
import EntryAddRow from "../_shared/EntryAddRow";

interface Props {
  data: EducationEntry[] | undefined;
  onChange: (data: EducationEntry[]) => void;
}

export default function EducationEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `edu_${Date.now()}`,
    institution: "",
    degree: "",
    start_date: "",
    end_date: null,
    current: false,
    gpa: "",
    summary: "",
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: any) => e.degree || e.institution || "New Education"}
      >
        {(entry: any, i: number) => (
          <div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-500">Institution</label>
                <input
                  type="text"
                  value={entry.institution}
                  onChange={(e: any) => update(i, "institution", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Degree</label>
                <input
                  type="text"
                  value={entry.degree}
                  onChange={(e: any) => update(i, "degree", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <DateField
                value={entry.start_date}
                onChange={(v) => update(i, "start_date", v ?? "")}
                label="Start Date"
              />
              <DateField
                value={entry.end_date}
                onChange={(v) => update(i, "end_date", v)}
                label="End Date"
                disabled={entry.current}
              />
              <div className="col-span-2 flex items-center justify-between gap-2">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500">GPA</label>
                  <input
                    type="text"
                    value={entry.gpa}
                    onChange={(e: any) => update(i, "gpa", e.target.value)}
                    className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                  />
                </div>
                <label className="flex items-center gap-2 pt-4 text-sm">
                  <input
                    type="checkbox"
                    checked={entry.current}
                    onChange={(e: any) => update(i, "current", e.target.checked)}
                  />
                  Currently enrolled
                </label>
              </div>
            </div>
            <textarea
              value={entry.summary || ""}
              onChange={(e: any) => update(i, "summary", e.target.value)}
              placeholder="Summary"
              rows={2}
              className="mt-2 w-full rounded border px-2 py-1 text-sm"
            />
          </div>
        )}
      </SortableAccordionList>
      <EntryAddRow
        kind="education"
        addLabel="Education"
        onAddNew={add}
        onPickFromLibrary={(picked) => {
          if (!picked) return;
          const incoming = Array.isArray(picked.data) ? picked.data : [];
          // Stamp a fresh id so each entry has a stable key.
          const stamped = incoming.map((row) => ({
            ...(row as Record<string, unknown>),
            id: `edu_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          }));
          onChange([...entries, ...(stamped as EducationEntry[])]);
        }}
      />
    </div>
  );
}
