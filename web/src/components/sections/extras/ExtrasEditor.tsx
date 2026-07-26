import type { JSX } from "react";
import { Plus, Trash2 } from "lucide-react";

import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";

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
    if (!entry) return;
    const fields = entry.fields.map((f, i) =>
      i === fieldIndex ? { ...f, ...patch } : f
    );
    update(entryIndex, "fields", fields);
  };

  const addField = (entryIndex: number) => {
    const entry = entries[entryIndex];
    if (!entry) return;
    update(entryIndex, "fields", [...entry.fields, { label: "", value: "" }]);
  };

  const removeField = (entryIndex: number, fieldIndex: number) => {
    const entry = entries[entryIndex];
    if (!entry) return;
    update(
      entryIndex,
      "fields",
      entry.fields.filter((_, i) => i !== fieldIndex)
    );
  };

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: ExtrasEntry) => e.title || "New Section"}
      >
        {(entry: ExtrasEntry, i: number) => (
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500">Section title</label>
              <input
                type="text"
                placeholder="e.g. Awards, Publications, Volunteering"
                value={entry.title}
                onChange={(e) => update(i, "title", e.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-xs text-gray-500">Fields</label>
              {entry.fields.length === 0 ? (
                <p className="text-xs text-gray-400 italic">
                  No fields yet. Add one to capture labels and values.
                </p>
              ) : (
                entry.fields.map((field, fi) => (
                  <div
                    key={`${entry.id}_field_${fi}`}
                    className="grid grid-cols-[1fr_2fr_auto] items-start gap-2 rounded border border-gray-100 bg-gray-50 p-2"
                  >
                    <input
                      type="text"
                      placeholder="Label"
                      value={field.label}
                      onChange={(e) => updateField(i, fi, { label: e.target.value })}
                      className="rounded border px-2 py-1 text-xs"
                    />
                    <textarea
                      placeholder="Value"
                      value={field.value}
                      onChange={(e) => updateField(i, fi, { value: e.target.value })}
                      rows={2}
                      className="rounded border px-2 py-1 text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => removeField(i, fi)}
                      className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
                      aria-label="Remove field"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))
              )}
              <button
                type="button"
                onClick={() => addField(i)}
                className="text-xs text-blue-600 hover:underline"
              >
                + Add field
              </button>
            </div>
          </div>
        )}
      </SortableAccordionList>
      <button
        type="button"
        onClick={add}
        className="text-sm text-blue-600 hover:underline"
      >
        <Plus className="mr-1 inline h-3.5 w-3.5" /> Add Section
      </button>
    </div>
  );
}
