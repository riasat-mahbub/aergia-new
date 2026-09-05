import type { ExperienceEntry } from "@/lib/cv/sectionData";
import { useFieldArray } from "@/lib/forms/useFieldArray";
import DateField from "@/components/common/DateField";
import SortableAccordionList from "@/components/common/SortableAccordionList";
import RichTextEditor from "@/components/common/section-editors/rich-text/RichTextEditor";
import EntryAddRow from "@/components/common/section-editors/_shared/EntryAddRow";
import { renderEntryActionFor, type SectionEditorActions } from "../types";

interface Props {
  data: ExperienceEntry[] | undefined;
  onChange: (data: ExperienceEntry[]) => void;
  actions?: SectionEditorActions;
  mode?: "section" | "library";
}

export default function ExperienceEditor({ data = [], onChange, actions, mode = "section" }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `exp_${Date.now()}`,
    company: "",
    position: "",
    start_date: "",
    end_date: null,
    current: false,
    location: "",
    description: [],
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        compact={mode === "library"}
        getTitle={(e: ExperienceEntry) => e.company || e.position || "New Experience"}
        renderActions={(entry) => renderEntryActionFor(actions, "experience", entry, entry.company || entry.position)}
      >
        {(entry: ExperienceEntry, i: number) => (
          <div>
            <div className="grid grid-cols-2 gap-2">
              <Input entry={entry} field="company" label="Company" onChange={(v) => update(i, "company", v)} />
              <Input entry={entry} field="position" label="Position" onChange={(v) => update(i, "position", v)} />
              <Input entry={entry} field="location" label="Location" onChange={(v) => update(i, "location", v)} />
              <DateField
                value={entry.start_date ?? ""}
                onChange={(v) => update(i, "start_date", v ?? "")}
                label="Start Date"
              />
              <DateField
                value={entry.end_date ?? null}
                onChange={(v) => update(i, "end_date", v)}
                label="End Date"
                disabled={entry.current}
              />
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={entry.current} onChange={(e) => update(i, "current", e.target.checked)} />
                Current
              </label>
            </div>
            <div className="mt-2">
              <label className="block text-xs text-app-ink-3">Description</label>
              <RichTextEditor
                value={entry.description ?? []}
                onChange={(blocks) => update(i, "description", blocks)}
                placeholder="Add a concise summary or bullet highlights…"
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          addLabel="Experience"
          onAddNew={add}
          secondaryAction={actions?.renderAddAction?.({
            kind: "experience",
            onPick: (picked) => {
              if (!picked) return;
              const incoming = Array.isArray(picked.data) ? picked.data : [];
              const stamped = incoming.map((row) => ({
                ...(row as Record<string, unknown>),
                id: `exp_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              }));
              onChange([...entries, ...(stamped as ExperienceEntry[])]);
            },
          })}
        />
      )}
    </div>
  );
}

function Input({ entry, field, label, onChange, disabled }: { entry: ExperienceEntry; field: keyof ExperienceEntry; label: string; onChange: (v: string) => void; disabled?: boolean }) {
  return (
    <div>
      <label className="block text-xs text-app-ink-3">{label}</label>
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
