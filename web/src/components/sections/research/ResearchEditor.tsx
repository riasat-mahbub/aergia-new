import type { ResearchEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";

interface Props {
  data: ResearchEntry[] | undefined;
  onChange: (data: ResearchEntry[]) => void;
}

export default function ResearchEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `research_${Date.now()}`,
    title: "",
    paper_url: "",
    paper_link_text: "",
    description: "",
    publication_date: "",
    publication_value: "",
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: any) => e.title || "New Research Paper"}
      >
        {(entry: any, i: number) => (
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-gray-500">Paper Title</label>
              <input
                type="text"
                value={entry.title}
                onChange={(e: any) => update(i, "title", e.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500">Publication Venue</label>
              <input
                type="text"
                placeholder="e.g. Nature, 2024 or NeurIPS 2024"
                value={entry.publication_value ?? ""}
                onChange={(e: any) => update(i, "publication_value", e.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-500">Paper Link</label>
                <input
                  type="text"
                  placeholder="https://doi.org/..."
                  value={entry.paper_url}
                  onChange={(e: any) => update(i, "paper_url", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Link Text</label>
                <input
                  type="text"
                  placeholder="Paper"
                  value={entry.paper_link_text}
                  onChange={(e: any) => update(i, "paper_link_text", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
                <p className="mt-0.5 text-[10px] text-gray-400">Defaults to Paper</p>
              </div>
            </div>
            <DateField
              value={entry.publication_date}
              onChange={(v) => update(i, "publication_date", v ?? "")}
              label="Publication Date"
            />
            <div>
              <label className="block text-xs text-gray-500">Description</label>
              <textarea
                value={entry.description}
                onChange={(e: any) => update(i, "description", e.target.value)}
                rows={2}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">
        + Add Research Paper
      </button>
    </div>
  );
}
