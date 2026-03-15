import type { LanguageEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";

interface Props {
  data: LanguageEntry[] | undefined;
  onChange: (data: LanguageEntry[]) => void;
}

const PROFICIENCIES = ["Native", "Fluent", "Advanced", "Intermediate", "Basic"];

export default function LanguagesEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `lang_${Date.now()}`,
    language: "",
    proficiency: "Intermediate",
  }));

  return (
    <div className="space-y-3">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        getTitle={(e: any) => e.language || "New Language"}
      >
        {(entry: any, i: number) => (
          <div className="flex items-center gap-2">
            <input type="text" value={entry.language} onChange={(e: any) => update(i, "language", e.target.value)} placeholder="Language" className="flex-1 rounded border px-2 py-1 text-sm" />
            <select value={entry.proficiency} onChange={(e: any) => update(i, "proficiency", e.target.value)} className="rounded border px-2 py-1 text-sm">
              {PROFICIENCIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        )}
      </SortableAccordionList>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Language</button>
    </div>
  );
}
