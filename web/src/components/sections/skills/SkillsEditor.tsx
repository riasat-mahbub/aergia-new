import type { SkillGroup } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import EntryAddRow from "../_shared/EntryAddRow";
import AddToLibraryButton from "../../library/AddToLibraryButton";

interface Props {
  data: SkillGroup[] | undefined;
  onChange: (data: SkillGroup[]) => void;
  context?: { cvId: string; sectionId: string };
}

export default function SkillsEditor({ data = [], onChange, context }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
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
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: any) => e.category || "New Skill Group"}
        onAddToLibrary={
          context
              ? (entryId) => {
                const entry = entries.find((e: any) => e.id === entryId);
                if (!entry) return null;
                return (
                  <AddToLibraryButton
                    cvId={context.cvId}
                    sectionId={context.sectionId}
                    entryId={entryId}
                    kind="skill"
                    entryData={entry as unknown as Record<string, unknown>}
                    entryLabel={entry?.category}
                  />
                );
              }
            : undefined
        }
      >
        {(group: any, i: number) => (
          <div>
            <input
              type="text"
              value={group.category}
              onChange={(e: any) => update(i, "category", e.target.value)}
              placeholder="Category (e.g. Frontend)"
              className="mb-2 w-full rounded border px-2 py-1 text-sm"
            />
            <div className="flex flex-wrap gap-1">
              {group.items.map((item: string, j: number) => (
                <span key={j} className="inline-flex items-center gap-1 rounded bg-app-surface-muted px-2 py-0.5 text-xs">
                  {item}
                  <button onClick={() => removeItem(i, j)} className="text-app-ink-3 hover:text-app-danger">&times;</button>
                </span>
              ))}
            </div>
            <input
              type="text"
              placeholder="Add skill and press Enter"
              className="mt-2 w-full rounded border px-2 py-1 text-sm"
              onKeyDown={(e: any) => {
                if (e.key === "Enter" && e.target.value.trim()) {
                  addItem(i, e.target.value.trim());
                  e.target.value = "";
                }
              }}
            />
          </div>
        )}
      </SortableAccordionList>
      <EntryAddRow
        kind="skill"
        addLabel="Skill Group"
        onAddNew={add}
        onPickFromLibrary={(picked) => {
          if (!picked) return;
          const incoming = Array.isArray(picked.data) ? picked.data : [];
          const stamped = incoming.map((row) => ({
            ...(row as Record<string, unknown>),
            id: `sk_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          }));
          onChange([...entries, ...(stamped as SkillGroup[])]);
        }}
      />
    </div>
  );
}
