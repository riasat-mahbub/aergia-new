import type { CertificationEntry } from "@/shared/cv/sectionData";
import { useFieldArray } from "@/shared/forms/useFieldArray";
import DateField from "@/shared/ui/DateField";
import SortableAccordionList from "@/shared/ui/SortableAccordionList";
import EntryAddRow from "@/shared/cv-editor/section-editors/shared/EntryAddRow";
import RichTextEditor from "@/shared/cv-editor/section-editors/rich-text/RichTextEditor";
import { renderEntryActionFor, type SectionEditorActions } from "../types";

interface Props {
  data: CertificationEntry[] | undefined;
  onChange: (data: CertificationEntry[]) => void;
  actions?: SectionEditorActions;
  mode?: "section" | "library";
}

export default function CertificationsEditor({ data = [], onChange, actions, mode = "section" }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `cert_${Date.now()}`,
    name: "",
    issuer: "",
    date: "",
    credential_url: "",
    link_text: "",
    description: [],
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        compact={mode === "library"}
        getTitle={(e: CertificationEntry) => e.name || "New Certification"}
        renderActions={(entry) => renderEntryActionFor(actions, "certification", entry, entry.name)}
      >
        {(entry: CertificationEntry, i: number) => (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-app-ink-3">Name</label>
              <input type="text" value={entry.name} onChange={(e) => update(i, "name", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-app-ink-3">Issuer</label>
              <input type="text" value={entry.issuer} onChange={(e) => update(i, "issuer", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <DateField
              value={entry.date ?? ""}
              onChange={(v) => update(i, "date", v ?? "")}
              label="Date"
            />
            <div>
              <label className="block text-xs text-app-ink-3">Credential URL</label>
              <input type="text" value={entry.credential_url} onChange={(e) => update(i, "credential_url", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-app-ink-3">Link Text</label>
              <input type="text" value={entry.link_text ?? ""} placeholder="Certificate" onChange={(e) => update(i, "link_text", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-app-ink-3">Description</label>
              <RichTextEditor
                value={entry.description ?? ""}
                onChange={(blocks) => update(i, "description", blocks)}
                placeholder="Add context or what this certification demonstrates…"
              />
            </div>
          </div>
        )}
      </SortableAccordionList>
      {mode !== "library" && (
        <EntryAddRow
          addLabel="Certification"
          onAddNew={add}
          secondaryAction={actions?.renderAddAction?.({
            kind: "certification",
            onPick: (picked) => {
              if (!picked) return;
              const incoming = Array.isArray(picked.data) ? picked.data : [];
              const stamped = incoming.map((row) => ({
                ...(row as Record<string, unknown>),
                id: `cert_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
              }));
              onChange([...entries, ...(stamped as CertificationEntry[])]);
            },
          })}
        />
      )}
    </div>
  );
}
