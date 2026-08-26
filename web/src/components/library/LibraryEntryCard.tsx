import { motion } from "motion/react";
import { Pencil, Trash2 } from "lucide-react";
import type { LibraryEntry } from "../../lib/api/library";

interface LibraryEntryCardProps {
  entry: LibraryEntry;
  onEdit?: () => void;
  onDelete?: () => void;
  /** When true (default), the card is interactive — used inside the picker. */
  interactive?: boolean;
  /** Render a compact meta line; default true. */
  showMeta?: boolean;
}

function deriveTitle(entry: LibraryEntry): string {
  const first = entry.payload?.[0];
  if (first && typeof first === "object") {
    const t = (first as Record<string, unknown>).title ?? (first as Record<string, unknown>).text;
    if (typeof t === "string" && t.trim()) return t.trim().slice(0, 120);
    const n = (first as Record<string, unknown>).name;
    if (typeof n === "string" && n.trim()) return n.trim().slice(0, 120);
  }
  return entry.kind.charAt(0).toUpperCase() + entry.kind.slice(1);
}

function deriveMeta(entry: LibraryEntry): string {
  const first = entry.payload?.[0];
  if (!first || typeof first !== "object") return "";
  const f = first as Record<string, unknown>;
  const company = typeof f.company === "string" ? f.company : null;
  const school = typeof f.school === "string" ? f.school : null;
  const start = typeof f.start === "string" ? f.start : null;
  const end = typeof f.end === "string" ? f.end : null;
  const range = start && end ? `${start} – ${end}` : start ?? "";
  const bits = [company ?? school, range].filter(Boolean);
  return bits.join(" · ");
}

export default function LibraryEntryCard({
  entry,
  onEdit,
  onDelete,
  interactive = true,
  showMeta = true,
}: LibraryEntryCardProps) {
  const title = deriveTitle(entry);
  const meta = deriveMeta(entry);

  const cardClasses = interactive
    ? "bg-lib-surface border-lib-rule hover:bg-lib-surface-2 cursor-pointer"
    : "bg-lib-surface border-lib-rule";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={`rounded-lg border p-4 transition-colors ${cardClasses}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="truncate text-base font-semibold text-lib-ink">{title}</h3>
          {showMeta && meta && (
            <p className="mt-1 truncate text-sm text-lib-ink-2">{meta}</p>
          )}
        </div>
        {(onEdit || onDelete) && (
          <div className="flex shrink-0 items-center gap-2">
            {onEdit && (
              <button
                type="button"
                onClick={onEdit}
                className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-lib-ink-3 hover:text-lib-ink"
                aria-label="Edit entry"
              >
                <Pencil className="h-3.5 w-3.5" />
                <span>Edit</span>
              </button>
            )}
            {onDelete && (
              <button
                type="button"
                onClick={onDelete}
                className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-lib-ink-3 hover:text-lib-danger"
                aria-label="Delete entry"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete</span>
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
