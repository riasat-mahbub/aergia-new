import type { ExperienceEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";

interface Props {
  data: ExperienceEntry[] | undefined;
  onChange: (data: ExperienceEntry[]) => void;
}

export default function ExperienceEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `exp_${Date.now()}`,
    company: "",
    position: "",
    start_date: "",
    end_date: null,
    current: false,
    location: "",
    description: "",
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: any) => e.company || e.position || "New Experience"}
      >
        {(entry: any, i: number) => (
          <div>
            <div className="grid grid-cols-2 gap-2">
              <Input entry={entry} field="company" label="Company" onChange={(v: any) => update(i, "company", v)} />
              <Input entry={entry} field="position" label="Position" onChange={(v: any) => update(i, "position", v)} />
              <Input entry={entry} field="location" label="Location" onChange={(v: any) => update(i, "location", v)} />
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
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={entry.current} onChange={(e: any) => update(i, "current", e.target.checked)} />
                Current
              </label>
            </div>
            <textarea
              value={entry.description}
              onChange={(e: any) => update(i, "description", e.target.value)}
              placeholder="Description"
              rows={2}
              className="mt-2 w-full rounded border px-2 py-1 text-sm"
            />
          </div>
        )}
      </SortableAccordionList>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Experience</button>
    </div>
  );
}

function Input({ entry, field, label, onChange, disabled }: { entry: ExperienceEntry; field: keyof ExperienceEntry; label: string; onChange: (v: any) => void; disabled?: boolean }) {
  return (
    <div>
      <label className="block text-xs text-gray-500">{label}</label>
      <input
        type="text"
        value={(entry[field] as string) || ""}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="mt-0.5 w-full rounded border px-2 py-1 text-sm disabled:opacity-50"
      />
    </div>
  );
}
