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

const TITLE_FIELDS: Record<string, readonly string[]> = {
  experience: ["position", "company"],
  education: ["degree", "institution", "school"],
  skill: ["category", "name"],
  project: ["name"],
  language: ["language", "name"],
  certification: ["name"],
  research: ["title"],
};

function firstText(payload: Record<string, unknown>, fields: readonly string[]): string | null {
  for (const field of fields) {
    const value = payload[field];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function deriveTitle(entry: LibraryEntry): string {
  const first = entry.payload?.[0];
  if (first && typeof first === "object") {
    const payload = first as Record<string, unknown>;
    const title = firstText(payload, ["title", "text", ...(TITLE_FIELDS[entry.kind] ?? [])]);
    if (title) return title.slice(0, 120);
  }
  return entry.kind.charAt(0).toUpperCase() + entry.kind.slice(1);
}

function deriveDateRange(payload: Record<string, unknown>): string | null {
  const start = firstText(payload, ["start_date", "start"]);
  const end = firstText(payload, ["end_date", "end"]) ?? (payload.current === true ? "Present" : null);
  if (start && end) return `${start} – ${end}`;
  return start ?? end;
}

function deriveMeta(entry: LibraryEntry): string {
  const first = entry.payload?.[0];
  if (!first || typeof first !== "object") return "";
  const payload = first as Record<string, unknown>;
  const range = deriveDateRange(payload);
  let details: Array<string | null> = [];
  if (entry.kind === "experience") {
    details = [firstText(payload, ["company"]), range];
  } else if (entry.kind === "education") {
    details = [firstText(payload, ["institution", "school"]), range];
  } else if (entry.kind === "certification") {
    details = [firstText(payload, ["issuer"]), firstText(payload, ["date"])];
  } else if (entry.kind === "language") {
    details = [firstText(payload, ["proficiency"])];
  } else if (entry.kind === "skill") {
    const items = payload.items;
    details = [Array.isArray(items) ? items.filter((item): item is string => typeof item === "string").join(", ") : null];
  } else if (entry.kind === "project") {
    details = [range];
  } else if (entry.kind === "research") {
    details = [firstText(payload, ["publication_value"]), range];
  }
  return details.filter((value): value is string => Boolean(value)).join(" · ");
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
