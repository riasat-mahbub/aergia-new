import type { SkillGroup } from "@/lib/cv/sectionData";
import { useFieldArray } from "@/lib/forms/useFieldArray";
import SortableAccordionList from "@/components/common/SortableAccordionList";
import EntryAddRow from "@/components/common/section-editors/_shared/EntryAddRow";
import { renderEntryActionFor, type SectionEditorActions } from "../types";

interface Props {
  data: SkillGroup[] | undefined;
  onChange: (data: SkillGroup[]) => void;
  actions?: SectionEditorActions;
  mode?: "section" | "library";
}

export default function SkillsEditor({ data = [], onChange, actions, mode = "section" }: Props) {
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
        compact={mode === "library"}
        getTitle={(e: SkillGroup) => e.category || "New Skill Group"}
        renderActions={(entry) => renderEntryActionFor(actions, "skill", entry, entry.category)}
      >
        {(group: SkillGroup, i: number) => (
          <div>
            <input
              type="text"
              value={group.category}
              onChange={(e) => update(i, "category", e.target.value)}
              placeholder="Category (e.g. Frontend)"
              className="mb-2 w-full rounded border px-2 py-1 text-sm"
            />
            <div className="flex flex-wrap gap-1">
              {group.items.map((item: string, j: number) => (
                <span key={j} className="inline-flex items-center gap-1 rounded bg-app-surface-muted px-2 py-0.5 text-xs">
                  {item}
                  <button
                    type="button"
                    onClick={() => removeItem(i, j)}
                    className="text-app-ink-3 hover:text-app-danger"
                    aria-label={`Remove ${item}`}
                    title={`Remove ${item}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            <input
              type="text"
              placeholder="Add skill and press Enter"
              className="mt-2 w-full rounded border px-2 py-1 text-sm"
              onKeyDown={(e) => {
                const input = e.currentTarget;
                if (e.key === "Enter" && input.value.trim()) {
                  addItem(i, input.value.trim());
                  input.value = "";
                }
              }}
            />
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          addLabel="Skill Group"
          onAddNew={add}
          secondaryAction={actions?.renderAddAction?.({
            kind: "skill",
            onPick: (picked) => {
              if (!picked) return;
              const incoming = Array.isArray(picked.data) ? picked.data : [];
              const stamped = incoming.map((row) => ({
                ...(row as Record<string, unknown>),
                id: `sk_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              }));
              onChange([...entries, ...(stamped as SkillGroup[])]);
            },
          })}
        />
      )}
    </div>
  );
}
