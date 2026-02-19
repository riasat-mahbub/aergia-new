import { AnimatePresence, motion } from "motion/react";
import type { CertificationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import AccordionPanel from "../../common/AccordionPanel";

interface Props {
  data: CertificationEntry[] | undefined;
  onChange: (data: CertificationEntry[]) => void;
}

export default function CertificationsEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `cert_${Date.now()}`,
    name: "",
    issuer: "",
    date: "",
    credential_url: "",
  }));

  return (
    <div className="space-y-4">
      <AnimatePresence>
        {entries.map((entry, i) => (
          <motion.div
            key={entry.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
          >
            <AccordionPanel
              title={entry.name || "New Certification"}
              onRemove={() => remove(i)}
            >
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500">Name</label>
                  <input type="text" value={entry.name} onChange={(e) => update(i, "name", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Issuer</label>
                  <input type="text" value={entry.issuer} onChange={(e) => update(i, "issuer", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Date</label>
                  <input type="text" value={entry.date} onChange={(e) => update(i, "date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Credential URL</label>
                  <input type="text" value={entry.credential_url} onChange={(e) => update(i, "credential_url", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
              </div>
            </AccordionPanel>
          </motion.div>
        ))}
      </AnimatePresence>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Certification</button>
    </div>
  );
}
