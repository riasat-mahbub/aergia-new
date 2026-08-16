import type { JSX } from "react";
import { Trash2 } from "lucide-react";

import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import EntryAddRow from "../_shared/EntryAddRow";

export interface ExtrasField {
  label: string;
  value: string;
}

export interface ExtrasEntry {
  id: string;
  title: string;
  fields: ExtrasField[];
}

interface Props {
  data: ExtrasEntry[] | undefined;
  onChange: (data: ExtrasEntry[]) => void;
}

function createEmptyEntry(): ExtrasEntry {
  return {
    id: `extras_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    title: "",
    fields: [],
  };
}

export default function ExtrasEditor({ data = [], onChange }: Props): JSX.Element {
  const { entries, add, remove, update, move } = useFieldArray<ExtrasEntry>(
    data,
    onChange,
    createEmptyEntry
  );

  const updateField = (
    entryIndex: number,
    fieldIndex: number,
    patch: Partial<ExtrasField>
  ) => {
    const entry = entries[entryIndex];
    const next = entry.fields.map((f, i) => (i === fieldIndex ? { ...f, ...patch } : f));
    update(entryIndex, "fields", next);
  };

  const addField = (entryIndex: number) => {
    const entry = entries[entryIndex];
    update(entryIndex, "fields", [...entry.fields, { label: "", value: "" }]);
  };

  const removeField = (entryIndex: number, fieldIndex: number) => {
    const entry = entries[entryIndex];
    update(entryIndex, "fields", entry.fields.filter((_, i) => i !== fieldIndex));
  };

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: ExtrasEntry) => e.title || "Untitled section"}
      >
        {(entry: ExtrasEntry, i: number) => (
          <div className="space-y-3">
            <input
              type="text"
              value={entry.title}
              onChange={(e) => update(i, "title", e.target.value)}
              placeholder="Section title"
              className="w-full rounded border px-2 py-1 text-sm"
            />
            <div className="space-y-2">
              {entry.fields.map((field, j) => (
                <div key={j} className="flex items-start gap-2 rounded border bg-app-canvas p-2">
                  <input
                    type="text"
                    value={field.label}
                    onChange={(e) => updateField(i, j, { label: e.target.value })}
                    placeholder="Label (e.g. LinkedIn)"
                    className="w-1/3 rounded border px-2 py-1 text-sm"
                  />
                  <input
                    type="text"
                    value={field.value}
                    onChange={(e) => updateField(i, j, { value: e.target.value })}
                    placeholder="Value or URL"
                    className="flex-1 rounded border px-2 py-1 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => removeField(i, j)}
                    className="text-app-ink-3 hover:text-app-danger"
                    aria-label="Remove field"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => addField(i)}
                className="text-sm text-app-primary hover:underline"
              >
                + Add field
              </button>
            </div>
          </div>
        )}
      </SortableAccordionList>
      <EntryAddRow kind="extras" addLabel="Section" onAddNew={add} />
    </div>
  );
}
