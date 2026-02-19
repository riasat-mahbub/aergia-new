import { AnimatePresence, motion } from "motion/react";
import type { EducationEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import AccordionPanel from "../../common/AccordionPanel";

interface Props {
  data: EducationEntry[] | undefined;
  onChange: (data: EducationEntry[]) => void;
}

export default function EducationEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `edu_${Date.now()}`,
    institution: "",
    degree: "",
    start_date: "",
    end_date: null,
    current: false,
    gpa: "",
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
              title={entry.degree || entry.institution || "New Education"}
              onRemove={() => remove(i)}
            >
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500">Institution</label>
                  <input type="text" value={entry.institution} onChange={(e) => update(i, "institution", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Degree</label>
                  <input type="text" value={entry.degree} onChange={(e) => update(i, "degree", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Start Date</label>
                  <input type="text" value={entry.start_date} onChange={(e) => update(i, "start_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">End Date</label>
                  <input type="text" value={entry.end_date || ""} onChange={(e) => update(i, "end_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" disabled={entry.current} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">GPA</label>
                  <input type="text" value={entry.gpa} onChange={(e) => update(i, "gpa", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={entry.current} onChange={(e) => update(i, "current", e.target.checked)} />
                  Currently enrolled
                </label>
              </div>
            </AccordionPanel>
          </motion.div>
        ))}
      </AnimatePresence>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Education</button>
    </div>
  );
}
