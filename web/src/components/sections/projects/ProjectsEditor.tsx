import type { ProjectEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";
import RichTextEditor from "../rich-text/RichTextEditor";
import EntryAddRow from "../_shared/EntryAddRow";
import AddToLibraryButton from "../../library/AddToLibraryButton";

interface Props {
  data: ProjectEntry[] | undefined;
  onChange: (data: ProjectEntry[]) => void;
  context?: { cvId: string; sectionId: string };
}

export default function ProjectsEditor({ data = [], onChange, context }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `proj_${Date.now()}`,
    name: "",
    url: "",
    link_text: "",
    start_date: "",
    end_date: null,
    description: [],
    tech_stack: [],
  }));

  const addTech = (index: number, tech: string) => {
    const entry = entries[index];
    update(index, "tech_stack", [...(entry?.tech_stack ?? []), tech]);
  };

  const removeTech = (entryIndex: number, techIndex: number) => {
    const entry = entries[entryIndex];
    update(entryIndex, "tech_stack", (entry.tech_stack ?? []).filter((_, i) => i !== techIndex));
  };

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: any) => e.name || "New Project"}
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
                    kind="project"
                    entryData={entry as unknown as Record<string, unknown>}
                    entryLabel={entry?.name}
                  />
                );
              }
            : undefined
        }
      >
        {(entry: any, i: number) => (
          <div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-500">Name</label>
                <input
                  type="text"
                  value={entry.name}
                  onChange={(e: any) => update(i, "name", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">URL</label>
                <input
                  type="text"
                  value={entry.url}
                  onChange={(e: any) => update(i, "url", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Link text</label>
                <input
                  type="text"
                  value={entry.link_text}
                  onChange={(e: any) => update(i, "link_text", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <DateField
                value={entry.start_date}
                onChange={(v) => update(i, "start_date", v ?? "")}
                label="Start Date"
              />
              <DateField
                value={entry.end_date}
                onChange={(v) => update(i, "end_date", v)}
                label="End Date"
                disabled={false}
              />
            </div>
            <div className="mt-2">
              <label className="block text-xs text-gray-500">Description</label>
              <RichTextEditor
                value={entry.description}
                onChange={(blocks) => update(i, "description", blocks)}
                placeholder="Description"
              />
            </div>
            <div className="mt-2">
              <label className="block text-xs text-gray-500">Tech stack</label>
              <div className="flex flex-wrap gap-1">
                {(entry.tech_stack ?? []).map((tech: string, j: number) => (
                  <span key={j} className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs">
                    {tech}
                    <button onClick={() => removeTech(i, j)} className="text-gray-400 hover:text-red-500">&times;</button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="Add tech and press Enter"
                className="mt-1 w-full rounded border px-2 py-1 text-sm"
                onKeyDown={(e: any) => {
                  if (e.key === "Enter" && e.target.value.trim()) {
                    addTech(i, e.target.value.trim());
                    e.target.value = "";
                  }
                }}
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      <EntryAddRow
        kind="project"
        addLabel="Project"
        onAddNew={add}
        onPickFromLibrary={(picked) => {
          if (!picked) return;
          const incoming = Array.isArray(picked.data) ? picked.data : [];
          const stamped = incoming.map((row) => ({
            ...(row as Record<string, unknown>),
            id: `proj_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          }));
          onChange([...entries, ...(stamped as ProjectEntry[])]);
        }}
      />
    </div>
  );
}
