import type { ExperienceEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";
import RichTextEditor from "../rich-text/RichTextEditor";
import EntryAddRow from "../_shared/EntryAddRow";
import AddToLibraryButton from "../../library/AddToLibraryButton";

interface Props {
  data: ExperienceEntry[] | undefined;
  onChange: (data: ExperienceEntry[]) => void;
  context?: { cvId: string; sectionId: string };
  mode?: "section" | "library";
}

export default function ExperienceEditor({ data = [], onChange, context, mode = "section" }: Props) {
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
        getTitle={(e: any) => e.company || e.position || "New Experience"}
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
                    kind="experience"
                    entryData={entry as unknown as Record<string, unknown>}
                    entryLabel={entry?.company || entry?.position}
                  />
                );
              }
            : undefined
        }
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
            <div className="mt-2">
              <label className="block text-xs text-app-ink-3">Description</label>
              <RichTextEditor
                value={entry.description}
                onChange={(blocks) => update(i, "description", blocks)}
                placeholder="Add a concise summary or bullet highlights…"
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          kind="experience"
          addLabel="Experience"
          onAddNew={add}
          onPickFromLibrary={(picked) => {
            if (!picked) return;
            const incoming = Array.isArray(picked.data) ? picked.data : [];
            const stamped = incoming.map((row) => ({
              ...(row as Record<string, unknown>),
              id: `exp_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            }));
            onChange([...entries, ...(stamped as ExperienceEntry[])]);
          }}
        />
      )}
    </div>
  );
}

function Input({ entry, field, label, onChange, disabled }: { entry: ExperienceEntry; field: keyof ExperienceEntry; label: string; onChange: (v: any) => void; disabled?: boolean }) {
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
