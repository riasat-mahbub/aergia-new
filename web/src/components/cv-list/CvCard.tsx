import { motion } from "motion/react";
import { Link } from "react-router-dom";
import type { CVListItem } from "../../lib/api/cvs";

const TEMPLATE_STYLES: Record<string, { strip: string; chip: string }> = {
  "generic-modern": { strip: "bg-app-primary", chip: "bg-app-primary-soft text-app-primary" },
  "generic-classic": { strip: "bg-app-secondary", chip: "bg-app-secondary-soft text-app-secondary" },
  "generic-minimal": { strip: "bg-app-ink-3", chip: "bg-app-surface-muted text-app-ink-2" },
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
  const templateStyle = TEMPLATE_STYLES[cv.template_id] || TEMPLATE_STYLES["generic-modern"];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, boxShadow: "0 8px 25px rgba(0,0,0,0.1)" }}
      className="overflow-hidden rounded-lg border border-app-rule bg-app-surface shadow-sm transition-shadow"
    >
      <div className={`h-1.5 ${templateStyle.strip}`} />
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-app-ink truncate">{cv.title}</h3>
            <div className="mt-1 flex items-center gap-2">
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${templateStyle.chip}`}>
                {templateLabel}
              </span>
              <span className="text-xs text-app-ink-3">Updated {date}</span>
            </div>
            {cv.application && (
              <Link
                to={`/dashboard/applications/${cv.application.id}`}
                className="mt-3 flex min-w-0 flex-wrap items-center gap-1.5 text-xs text-app-primary hover:text-app-primary hover:underline"
              >
                <span className="inline-flex shrink-0 items-center rounded-full bg-app-primary-soft px-2 py-0.5 font-medium">
                  Application CV
                </span>
                <span className="truncate">{cv.application.company} · {cv.application.role}</span>
              </Link>
            )}
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button
            onClick={() => onEdit(cv.id)}
            className="rounded bg-app-primary px-3 py-1.5 text-sm text-white hover:bg-app-primary-hover"
          >
            Edit
          </button>
          <button
            onClick={() => onCopy(cv.id)}
            className="rounded border border-app-rule-strong px-3 py-1.5 text-sm text-app-ink-2 hover:bg-app-surface-muted"
          >
            Copy
          </button>
          <button
            onClick={() => onDelete(cv.id)}
            className="rounded border border-app-danger px-3 py-1.5 text-sm text-app-danger hover:bg-app-danger-soft"
          >
            Delete
          </button>
        </div>
      </div>
    </motion.div>
  );
}
