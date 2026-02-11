import type { LanguageEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";

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
      {entries.map((entry, i) => (
        <div key={entry.id} className="flex items-center gap-2 rounded border p-2">
          <input type="text" value={entry.language} onChange={(e) => update(i, "language", e.target.value)} placeholder="Language" className="flex-1 rounded border px-2 py-1 text-sm" />
          <select value={entry.proficiency} onChange={(e) => update(i, "proficiency", e.target.value)} className="rounded border px-2 py-1 text-sm">
            {PROFICIENCIES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <button onClick={() => remove(i)} className="text-xs text-red-500">Remove</button>
        </div>
      ))}
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Language</button>
    </div>
  );
}
