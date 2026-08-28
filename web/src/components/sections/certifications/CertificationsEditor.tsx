import type { CertificationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import SortableAccordionList from "../../../lib/sections/SortableAccordionList";
import DateField from "../../../lib/sections/DateField";
import EntryAddRow from "../_shared/EntryAddRow";
import AddToLibraryButton from "../../library/AddToLibraryButton";

interface Props {
  data: CertificationEntry[] | undefined;
  onChange: (data: CertificationEntry[]) => void;
  context?: { cvId: string; sectionId: string };
}

export default function CertificationsEditor({ data = [], onChange, context }: Props) {
  const { entries, add, remove, update, move } = useFieldArray(data, onChange, () => ({
    id: `cert_${Date.now()}`,
    name: "",
    issuer: "",
    date: "",
    credential_url: "",
    link_text: "",
  }));

  return (
    <div className="space-y-4">
      <SortableAccordionList
        entries={entries}
        onRemove={remove}
        onMove={move}
        getTitle={(e: any) => e.name || "New Certification"}
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
                    kind="certification"
                    entryData={entry as unknown as Record<string, unknown>}
                    entryLabel={entry?.name}
                  />
                );
              }
            : undefined
        }
      >
        {(entry: any, i: number) => (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-app-ink-3">Name</label>
              <input type="text" value={entry.name} onChange={(e: any) => update(i, "name", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-app-ink-3">Issuer</label>
              <input type="text" value={entry.issuer} onChange={(e: any) => update(i, "issuer", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <DateField
              value={entry.date}
              onChange={(v) => update(i, "date", v ?? "")}
              label="Date"
            />
            <div>
              <label className="block text-xs text-app-ink-3">Credential URL</label>
              <input type="text" value={entry.credential_url} onChange={(e: any) => update(i, "credential_url", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-app-ink-3">Link Text</label>
              <input type="text" value={entry.link_text ?? ""} placeholder="Certificate" onChange={(e: any) => update(i, "link_text", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
            </div>
          </div>
        )}
      </SortableAccordionList>
      <EntryAddRow
        kind="certification"
        addLabel="Certification"
        onAddNew={add}
        onPickFromLibrary={(picked) => {
          if (!picked) return;
          const incoming = Array.isArray(picked.data) ? picked.data : [];
          const stamped = incoming.map((row) => ({
            ...(row as Record<string, unknown>),
            id: `cert_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          }));
          onChange([...entries, ...(stamped as CertificationEntry[])]);
        }}
      />
    </div>
  );
}
