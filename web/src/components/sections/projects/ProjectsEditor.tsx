import { AnimatePresence, motion } from "motion/react";
import type { ProjectEntry } from "../../../lib/sections/types";
import { useFieldArray } from "../../../lib/sections/useFieldArray";
import AccordionPanel from "../../common/AccordionPanel";

interface Props {
  data: ProjectEntry[] | undefined;
  onChange: (data: ProjectEntry[]) => void;
}

export default function ProjectsEditor({ data = [], onChange }: Props) {
  const { entries, add, remove, update } = useFieldArray(data, onChange, () => ({
    id: `proj_${Date.now()}`,
    name: "",
    url: "",
    start_date: "",
    end_date: null,
    description: "",
    tech_stack: [],
  }));

  const addTech = (index: number, tech: string) => {
    const entry = entries[index];
    update(index, "tech_stack", [...(entry?.tech_stack || []), tech]);
  };

  const removeTech = (entryIndex: number, techIndex: number) => {
    const entry = entries[entryIndex];
    update(entryIndex, "tech_stack", entry.tech_stack.filter((_, i) => i !== techIndex));
  };

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
              title={entry.name || "New Project"}
              onRemove={() => remove(i)}
            >
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-500">Name</label>
                  <input type="text" value={entry.name} onChange={(e) => update(i, "name", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">URL</label>
                  <input type="text" value={entry.url} onChange={(e) => update(i, "url", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">Start Date</label>
                  <input type="text" value={entry.start_date} onChange={(e) => update(i, "start_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500">End Date</label>
                  <input type="text" value={entry.end_date || ""} onChange={(e) => update(i, "end_date", e.target.value)} className="mt-0.5 w-full rounded border px-2 py-1 text-sm" />
                </div>
              </div>
              <textarea value={entry.description} onChange={(e) => update(i, "description", e.target.value)} placeholder="Description" rows={2} className="mt-2 w-full rounded border px-2 py-1 text-sm" />
              <div className="mt-2">
                <label className="block text-xs text-gray-500">Tech Stack</label>
                <div className="flex flex-wrap gap-1">
                  {entry.tech_stack.map((tech, j) => (
                    <span key={j} className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                      {tech}
                      <button onClick={() => removeTech(i, j)} className="text-blue-400 hover:text-red-500">&times;</button>
                    </span>
                  ))}
                </div>
                <input type="text" placeholder="Add tech and press Enter" className="mt-1 w-full rounded border px-2 py-1 text-sm"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.target as HTMLInputElement).value.trim()) {
                      addTech(i, (e.target as HTMLInputElement).value.trim());
                      (e.target as HTMLInputElement).value = "";
                    }
                  }}
                />
              </div>
            </AccordionPanel>
          </motion.div>
        ))}
      </AnimatePresence>
      <button onClick={add} className="text-sm text-blue-600 hover:underline">+ Add Project</button>
    </div>
  );
}
