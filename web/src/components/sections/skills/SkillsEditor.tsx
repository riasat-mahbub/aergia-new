import type { SkillGroup } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";

interface Props {
  data: SkillGroup[] | undefined;
  onChange: (data: SkillGroup[]) => void;
}

export default function SkillsEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `sk_${Date.now()}`,
    category: "",
    items: [],
  }));

  const addItem = (index: number, item: string) => {
    const group = entries[index];
    update(index, "items", [...(group?.items || []), item]);
  };

  const removeItem = (groupIndex: number, itemIndex: number) => {
    const group = entries[groupIndex];
    update(groupIndex, "items", group.items.filter((_, i) => i !== itemIndex));
  };

  return (
    <div className="space-y-4">
      {entries.map((group, i) => (
        <div key={group.id} className="rounded border p-3">
          <div className="mb-2 flex items-center justify-between">
            <input
              type="text"
              value={group.category}
              onChange={(e) => update(i, "category", e.target.value)}
              placeholder="Category (e.g. Frontend)"
              className="w-full rounded border px-2 py-1 text-sm"
            />
            <button onClick={() => remove(i)} className="ml-2 text-xs text-red-500">Remove</button>
          </div>
          <div className="flex flex-wrap gap-1">
            {group.items.map((item, j) => (
              <span key={j} className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs">
                {item}
                <button onClick={() => removeItem(i, j)} className="text-gray-400 hover:text-red-500">&times;</button>
              </span>
            ))}
          </div>
          <input
            type="text"
            placeholder="Add skill and press Enter"
            className="mt-2 w-full rounded border px-2 py-1 text-sm"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.target as HTMLInputElement).value.trim()) {
                addItem(i, (e.target as HTMLInputElement).value.trim());
                (e.target as HTMLInputElement).value = "";
              }
            }}
          />
        </div>
      ))}
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Skill Group</button>
    </div>
  );
}
