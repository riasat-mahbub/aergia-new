import { motion } from "motion/react";
import type { CVListItem } from "../../lib/api/cvs";

const TEMPLATE_COLORS: Record<string, string> = {
  "generic-modern": "#2563eb",
  "generic-classic": "#1f2937",
  "generic-minimal": "#6b7280",
};

interface CvCardProps {
  cv: CVListItem;
  onEdit: (id: string) => void;
  onCopy: (id: string) => void;
  onDelete: (id: string) => void;
}

export default function CvCard({ cv, onEdit, onCopy, onDelete }: CvCardProps) {
  const templateLabel = cv.template_id.replace("generic-", "").replace("-", " ");
  const date = new Date(cv.updated_at).toLocaleDateString();
  const accentColor = TEMPLATE_COLORS[cv.template_id] || "#2563eb";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, boxShadow: "0 8px 25px rgba(0,0,0,0.1)" }}
      className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition-shadow"
    >
      <div className="h-1.5" style={{ backgroundColor: accentColor }} />
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">{cv.title}</h3>
            <div className="mt-1 flex items-center gap-2">
              <span
                className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize"
                style={{ backgroundColor: `${accentColor}15`, color: accentColor }}
              >
                {templateLabel}
              </span>
              <span className="text-xs text-gray-400">Updated {date}</span>
            </div>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button
            onClick={() => onEdit(cv.id)}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
          >
            Edit
          </button>
          <button
            onClick={() => onCopy(cv.id)}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            Copy
          </button>
          <button
            onClick={() => onDelete(cv.id)}
            className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
          >
            Delete
          </button>
        </div>
      </div>
    </motion.div>
  );
}
