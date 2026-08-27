import type { LanguageEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import EntryAddRow from "../_shared/EntryAddRow";

interface Props {
  data: LanguageEntry[] | undefined;
  onChange: (data: LanguageEntry[]) => void;
}

const PROFICIENCIES = ["Native", "Fluent", "Advanced", "Intermediate", "Basic"];
export default function LanguagesEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `lang_${Date.now()}`,
    language: "",
    proficiency: "Intermediate",
  }));

  return (
    <div className="space-y-3">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
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
      <EntryAddRow
        kind="language"
        addLabel="Language"
        onAddNew={add}
        onPickFromLibrary={(picked) => {
          if (!picked) return;
          const incoming = Array.isArray(picked.data) ? picked.data : [];
          const stamped = incoming.map((row) => ({
            ...(row as Record<string, unknown>),
            id: `lang_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          }));
          onChange([...entries, ...(stamped as LanguageEntry[])]);
        }}
      />
    </div>
  );
}
