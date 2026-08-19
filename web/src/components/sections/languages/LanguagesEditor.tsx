import type { LanguageEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import EntryAddRow from "../_shared/EntryAddRow";
import AddToLibraryButton from "../../library/AddToLibraryButton";

interface Props {
  data: LanguageEntry[] | undefined;
  onChange: (data: LanguageEntry[]) => void;
  context?: { cvId: string; sectionId: string };
  mode?: "section" | "library";
}

const PROFICIENCIES = ["Native", "Fluent", "Advanced", "Intermediate", "Basic"];

export default function LanguagesEditor({ data = [], onChange, context, mode = "section" }: Props) {
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
        getTitle={(e: any) => e.language || "New Language"}
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
                    kind="language"
                    entryData={entry as unknown as Record<string, unknown>}
                    entryLabel={entry?.language}
                  />
                );
              }
            : undefined
        }
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
      {mode !== "library" && (
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
      )}
    </div>
  );
}
