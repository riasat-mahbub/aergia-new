import type { LanguageEntry } from "@/lib/cv/types";
import { useFieldArray } from "@/lib/forms/useFieldArray";
import SortableAccordionList from "@/components/common/SortableAccordionList";
import EntryAddRow from "@/components/common/section-editors/_shared/EntryAddRow";
import { renderEntryActionFor, type SectionEditorActions } from "../types";

interface Props {
  data: LanguageEntry[] | undefined;
  onChange: (data: LanguageEntry[]) => void;
  actions?: SectionEditorActions;
  mode?: "section" | "library";
}

const PROFICIENCIES = ["Native", "Fluent", "Advanced", "Intermediate", "Basic"];

export default function LanguagesEditor({ data = [], onChange, actions, mode = "section" }: Props) {
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
        compact={mode === "library"}
        getTitle={(e: LanguageEntry) => e.language || "New Language"}
        renderActions={(entry) => renderEntryActionFor(actions, "language", entry, entry.language)}
      >
        {(entry: LanguageEntry, i: number) => (
          <div className="flex items-center gap-2">
            <input type="text" value={entry.language} onChange={(e) => update(i, "language", e.target.value)} placeholder="Language" className="flex-1 rounded border px-2 py-1 text-sm" />
            <select value={entry.proficiency} onChange={(e) => update(i, "proficiency", e.target.value)} className="rounded border px-2 py-1 text-sm">
              {PROFICIENCIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          addLabel="Language"
          onAddNew={add}
          secondaryAction={actions?.renderAddAction?.({
            kind: "language",
            onPick: (picked) => {
              if (!picked) return;
              const incoming = Array.isArray(picked.data) ? picked.data : [];
              const stamped = incoming.map((row) => ({
                ...(row as Record<string, unknown>),
                id: `lang_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              }));
              onChange([...entries, ...(stamped as LanguageEntry[])]);
            },
          })}
        />
      )}
    </div>
  );
}
