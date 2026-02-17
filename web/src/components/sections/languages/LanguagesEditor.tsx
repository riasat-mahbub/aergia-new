import { AnimatePresence, motion } from "motion/react";
import type { LanguageEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import AccordionPanel from "../../common/AccordionPanel";

interface Props {
  data: LanguageEntry[] | undefined;
  onChange: (data: LanguageEntry[]) => void;
}

const PROFICIENCIES = ["Native", "Fluent", "Advanced", "Intermediate", "Basic"];

export default function LanguagesEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `lang_${Date.now()}`,
    language: "",
    proficiency: "Intermediate",
  }));

  return (
    <div className="space-y-3">
      <AnimatePresence>
        {entries.map((entry, i) => (
          <motion.div
            key={entry.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
          >
            <AccordionPanel
              title={entry.language || "New Language"}
              onRemove={() => remove(i)}
            >
              <div className="flex items-center gap-2">
                <input type="text" value={entry.language} onChange={(e) => update(i, "language", e.target.value)} placeholder="Language" className="flex-1 rounded border px-2 py-1 text-sm" />
                <select value={entry.proficiency} onChange={(e) => update(i, "proficiency", e.target.value)} className="rounded border px-2 py-1 text-sm">
                  {PROFICIENCIES.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </AccordionPanel>
          </motion.div>
        ))}
      </AnimatePresence>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Language</button>
    </div>
  );
}
