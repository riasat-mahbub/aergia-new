import type { ProjectEntry } from "@/lib/cv/sectionData";
import { useFieldArray } from "@/lib/forms/useFieldArray";
import DateField from "@/components/common/DateField";
import SortableAccordionList from "@/components/common/SortableAccordionList";
import RichTextEditor from "@/components/common/section-editors/rich-text/RichTextEditor";
import EntryAddRow from "@/components/common/section-editors/_shared/EntryAddRow";
import { renderEntryActionFor, type SectionEditorActions } from "../types";

interface Props {
  data: ProjectEntry[] | undefined;
  onChange: (data: ProjectEntry[]) => void;
  actions?: SectionEditorActions;
  mode?: "section" | "library";
}

export default function ProjectsEditor({ data = [], onChange, actions, mode = "section" }: Props) {
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
        compact={mode === "library"}
        getTitle={(e: ProjectEntry) => e.name || "New Project"}
        renderActions={(entry) => renderEntryActionFor(actions, "project", entry, entry.name)}
      >
        {(entry: ProjectEntry, i: number) => (
          <div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-app-ink-3">Name</label>
                <input
                  type="text"
                  value={entry.name}
                  onChange={(e) => update(i, "name", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-app-ink-3">URL</label>
                <input
                  type="text"
                  value={entry.url}
                  onChange={(e) => update(i, "url", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-app-ink-3">Link text</label>
                <input
                  type="text"
                  value={entry.link_text}
                  onChange={(e) => update(i, "link_text", e.target.value)}
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                />
              </div>
              <DateField
                value={entry.start_date ?? ""}
                onChange={(v) => update(i, "start_date", v ?? "")}
                label="Start Date"
              />
              <DateField
                value={entry.end_date ?? null}
                onChange={(v) => update(i, "end_date", v)}
                label="End Date"
                disabled={false}
              />
            </div>
            <div className="mt-2">
              <label className="block text-xs text-app-ink-3">Description</label>
              <RichTextEditor
                value={entry.description ?? []}
                onChange={(blocks) => update(i, "description", blocks)}
                placeholder="Describe the project, impact, and key details…"
              />
            </div>
            <div className="mt-2">
              <label className="block text-xs text-app-ink-3">Tech stack</label>
              <div className="flex flex-wrap gap-1">
                {(entry.tech_stack ?? []).map((tech: string, j: number) => (
                  <span key={j} className="inline-flex items-center gap-1 rounded bg-app-surface-muted px-2 py-0.5 text-xs">
                    {tech}
                    <button onClick={() => removeTech(i, j)} className="text-app-ink-3 hover:text-app-danger">&times;</button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                placeholder="Add tech and press Enter"
                className="mt-1 w-full rounded border px-2 py-1 text-sm"
                onKeyDown={(e) => {
                  const input = e.currentTarget;
                  if (e.key === "Enter" && input.value.trim()) {
                    addTech(i, input.value.trim());
                    input.value = "";
                  }
                }}
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          addLabel="Project"
          onAddNew={add}
          secondaryAction={actions?.renderAddAction?.({
            kind: "project",
            onPick: (picked) => {
              if (!picked) return;
              const incoming = Array.isArray(picked.data) ? picked.data : [];
              const stamped = incoming.map((row) => ({
                ...(row as Record<string, unknown>),
                id: `proj_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              }));
              onChange([...entries, ...(stamped as ProjectEntry[])]);
            },
          })}
        />
      )}
    </div>
  );
}
