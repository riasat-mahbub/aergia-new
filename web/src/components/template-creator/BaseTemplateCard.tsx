import { motion } from "motion/react";
import type { UserTemplate } from "../../lib/api/templates";

interface Props {
  template: UserTemplate;
  onSelect: (templateId: string) => void;
}

export default function BaseTemplateCard({ template, onSelect }: Props) {
  const isModern = template.id === "generic-modern";
  const isClassic = template.id === "generic-classic";
  const isMinimal = template.id === "generic-minimal";

  return (
    <motion.button
      type="button"
      whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(template.id)}
      className="flex w-full flex-col items-start rounded-xl border-2 border-gray-200 bg-white p-5 text-left transition-all hover:border-blue-400"
    >
      <div className="mb-3 flex h-16 w-full items-center justify-center rounded-lg bg-gray-50">
        {isModern && (
          <div className="flex h-full w-2/3 gap-0.5">
            <div className="h-full w-[30%] rounded bg-blue-400" />
            <div className="h-full w-[70%] rounded bg-gray-200" />
          </div>
        )}
        {isClassic && (
          <div className="flex h-full w-2/3 flex-col gap-1">
            <div className="h-1.5 w-full rounded bg-gray-400" />
            <div className="h-px w-full bg-gray-300" />
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-1 w-full rounded bg-gray-200" />
            ))}
          </div>
        )}
        {isMinimal && (
          <div className="flex h-full w-2/3 flex-col items-start gap-1.5">
            <div className="h-1.5 w-1/2 rounded bg-gray-400" />
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-1 w-full rounded bg-gray-200" />
            ))}
          </div>
        )}
        {!isModern && !isClassic && !isMinimal && (
          <div className="flex h-full w-2/3 flex-col items-center justify-center gap-1">
            <div className="h-px w-8 bg-gray-300" />
            <div className="h-1.5 w-6 rounded bg-gray-200" />
          </div>
        )}
      </div>

      <h3 className="text-sm font-semibold text-gray-900">{template.name}</h3>
      {template.description && (
        <p className="mt-1 line-clamp-2 text-xs text-gray-500">{template.description}</p>
      )}
    </motion.button>
  );
}
