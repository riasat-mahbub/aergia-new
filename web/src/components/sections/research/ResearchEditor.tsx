import type { ChangeEvent } from "react";
import type { ResearchEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";
import RichTextEditor from "../rich-text/RichTextEditor";
import EntryAddRow from "../_shared/EntryAddRow";
import AddToLibraryButton from "../../library/AddToLibraryButton";

interface Props {
  data: ResearchEntry[] | undefined;
  onChange: (data: ResearchEntry[]) => void;
  context?: { cvId: string; sectionId: string };
  mode?: "section" | "library";
}

export default function ResearchEditor({ data = [], onChange, context, mode = "section" }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `research_${Date.now()}`,
    title: "",
    paper_url: "",
    paper_link_text: "",
    description: [],
    publication_date: "",
    publication_value: "",
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        compact={mode === "library"}
        onAddToLibrary={
          context
            ? (entryId) => {
                const entry = entries.find((candidate) => candidate.id === entryId);
                if (!entry) return null;
                const entryData = { ...entry } satisfies Record<string, unknown>;
                return (
                  <AddToLibraryButton
                    cvId={context.cvId}
                    sectionId={context.sectionId}
                    entryId={entryId}
                    kind="research"
                    entryData={entryData}
                    entryLabel={entry.title}
                  />
                );
              }
            : undefined
        }
        getTitle={(entry: ResearchEntry) => entry.title || "New Research Paper"}
      >
        {(entry: ResearchEntry, i: number) => (
          <div className="space-y-2">
            <div>
              <label className="block text-xs text-app-ink-3">Paper Title</label>
              <input
                type="text"
                value={entry.title}
                onChange={(event: ChangeEvent<HTMLInputElement>) => update(i, "title", event.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-app-ink-3">Publication Venue</label>
              <input
                type="text"
                placeholder="e.g. Nature, 2024 or NeurIPS 2024"
                value={entry.publication_value ?? ""}
                onChange={(event: ChangeEvent<HTMLInputElement>) => update(i, "publication_value", event.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-app-ink-3">Paper Link</label>
                <input
                  type="text"
                  placeholder="https://doi.org/..."
                  value={entry.paper_url}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => update(i, "paper_url", event.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-app-ink-3">Link Text</label>
                <input
                  type="text"
                  placeholder="Paper"
                  value={entry.paper_link_text}
                  onChange={(event: ChangeEvent<HTMLInputElement>) => update(i, "paper_link_text", event.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
                <p className="mt-0.5 text-[10px] text-app-ink-3">Defaults to Paper</p>
              </div>
            </div>
            <DateField
              value={entry.publication_date ?? ""}
              onChange={(v) => update(i, "publication_date", v ?? "")}
              label="Publication Date"
            />
            <div>
              <label className="block text-xs text-app-ink-3">Description</label>
              <RichTextEditor
                value={entry.description ?? ""}
                onChange={(blocks) => update(i, "description", blocks)}
                placeholder="Description"
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          kind="research"
          addLabel="Research Paper"
          onAddNew={add}
          onPickFromLibrary={(picked) => {
            if (!picked) return;
            const incoming = Array.isArray(picked.data) ? picked.data : [];
            const stamped = incoming.map((row) => ({
              ...(row as Record<string, unknown>),
              id: `research_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
            }));
            onChange([...entries, ...(stamped as ResearchEntry[])]);
          }}
        />
      )}
    </div>
  );
}
